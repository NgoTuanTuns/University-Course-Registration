import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import {
  ArrowUpRight,
  Maximize2,
  Minimize2,
  RotateCcw,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import * as api from "../../api";
import type {
  PrereqGraphEdge,
  PrereqGraphNode,
  PrereqGraphResponse,
} from "../../types";

const KIT_CODES = new Set([
  "INT101",
  "MAT201",
  "MAT202",
  "INT131",
  "INT221",
  "INT222",
  "INT231",
  "INT321",
  "INT331",
  "INT341",
  "INT451",
  "INT431",
]);

const PREFIX_LABELS: Record<string, string> = {
  INT: "Ngành CNTT (INT)",
  ELE: "Điện - Điện tử (ELE)",
  MAN: "Quản trị KD (MAN)",
  MAT: "Toán học (MAT)",
  PHY: "Vật lý (PHY)",
  ENG: "Ngoại ngữ (ENG)",
  BAS: "Kỹ năng chung (BAS — 0 TC)",
};

const NODE_W = 228;
const NODE_H = 86;
const COL_GAP = 86;
const ROW_GAP = 18;
const PAD_X = 36;
const PAD_Y = 48;

interface PositionedNode {
  node: PrereqGraphNode;
  x: number;
  y: number;
  hasIn: boolean;
  hasOut: boolean;
}

interface PositionedEdge {
  key: string;
  edge: PrereqGraphEdge;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

interface LevelColumn {
  level: number;
  x: number;
  count: number;
}

const STATUS_STYLE: Record<
  PrereqGraphNode["status"],
  { accent: string; badgeBg: string; badgeText: string; label: string }
> = {
  COMPLETED: {
    accent: "#10b981",
    badgeBg: "#ecfdf5",
    badgeText: "#047857",
    label: "Đã đạt",
  },
  ELIGIBLE: {
    accent: "#f59e0b",
    badgeBg: "#fffbeb",
    badgeText: "#b45309",
    label: "Đủ ĐK",
  },
  LOCKED: {
    accent: "#94a3b8",
    badgeBg: "#f1f5f9",
    badgeText: "#475569",
    label: "Chưa đủ",
  },
};

function computeAirflowLayout(
  nodes: PrereqGraphNode[],
  edges: PrereqGraphEdge[],
): {
  positionedNodes: PositionedNode[];
  positionedEdges: PositionedEdge[];
  columns: LevelColumn[];
  width: number;
  height: number;
} {
  if (!nodes.length) {
    return {
      positionedNodes: [],
      positionedEdges: [],
      columns: [],
      width: 400,
      height: 240,
    };
  }

  const byLevel = new Map<number, PrereqGraphNode[]>();
  for (const n of nodes) {
    const arr = byLevel.get(n.level) ?? [];
    arr.push(n);
    byLevel.set(n.level, arr);
  }
  const sortedLevels = Array.from(byLevel.entries()).sort(
    (a, b) => a[0] - b[0],
  );

  // Build adjacency for barycenter ordering (crossing minimization)
  const parentsMap = new Map<number, number[]>();
  const childrenMap = new Map<number, number[]>();
  for (const e of edges) {
    const p = parentsMap.get(e.courseId) ?? [];
    p.push(e.prereqCourseId);
    parentsMap.set(e.courseId, p);

    const c = childrenMap.get(e.prereqCourseId) ?? [];
    c.push(e.courseId);
    childrenMap.set(e.prereqCourseId, c);
  }

  // Initial sort per column: connected hubs first, then by code
  for (const [, list] of sortedLevels) {
    list.sort((a, b) => {
      const degA =
        (parentsMap.get(a.id)?.length ?? 0) +
        (childrenMap.get(a.id)?.length ?? 0);
      const degB =
        (parentsMap.get(b.id)?.length ?? 0) +
        (childrenMap.get(b.id)?.length ?? 0);
      if (degA !== degB) return degB - degA;
      return a.code.localeCompare(b.code);
    });
  }

  const rowOrder = new Map<number, number>();
  const recordOrder = () => {
    for (const [, list] of sortedLevels) {
      list.forEach((n, idx) => rowOrder.set(n.id, idx));
    }
  };
  recordOrder();

  // 2 forward + backward barycenter sweeps to untangle arrows
  for (let pass = 0; pass < 2; pass++) {
    for (let i = 1; i < sortedLevels.length; i++) {
      const list = sortedLevels[i][1];
      list.sort((a, b) => {
        const pa = parentsMap.get(a.id) ?? [];
        const pb = parentsMap.get(b.id) ?? [];
        const avgA = pa.length
          ? pa.reduce((s, id) => s + (rowOrder.get(id) ?? 0), 0) / pa.length
          : 9999;
        const avgB = pb.length
          ? pb.reduce((s, id) => s + (rowOrder.get(id) ?? 0), 0) / pb.length
          : 9999;
        if (avgA !== avgB) return avgA - avgB;
        return a.code.localeCompare(b.code);
      });
      recordOrder();
    }
    for (let i = sortedLevels.length - 2; i >= 0; i--) {
      const list = sortedLevels[i][1];
      list.sort((a, b) => {
        const ca = childrenMap.get(a.id) ?? [];
        const cb = childrenMap.get(b.id) ?? [];
        const avgA = ca.length
          ? ca.reduce((s, id) => s + (rowOrder.get(id) ?? 0), 0) / ca.length
          : 9999;
        const avgB = cb.length
          ? cb.reduce((s, id) => s + (rowOrder.get(id) ?? 0), 0) / cb.length
          : 9999;
        if (avgA !== avgB) return avgA - avgB;
        return a.code.localeCompare(b.code);
      });
      recordOrder();
    }
  }

  const maxRows = Math.max(...sortedLevels.map(([, list]) => list.length));
  const totalGraphH = maxRows * NODE_H + Math.max(0, maxRows - 1) * ROW_GAP;

  const posMap = new Map<number, PositionedNode>();
  const positionedNodes: PositionedNode[] = [];
  const columns: LevelColumn[] = [];

  sortedLevels.forEach(([lv, list], colIdx) => {
    const x = PAD_X + colIdx * (NODE_W + COL_GAP);
    const colH = list.length * NODE_H + Math.max(0, list.length - 1) * ROW_GAP;
    const yOffset = PAD_Y + Math.max(0, (totalGraphH - colH) / 2);

    columns.push({ level: lv, x, count: list.length });

    list.forEach((node, rowIdx) => {
      const y = yOffset + rowIdx * (NODE_H + ROW_GAP);
      const pn: PositionedNode = {
        node,
        x,
        y,
        hasIn: (parentsMap.get(node.id)?.length ?? 0) > 0,
        hasOut: (childrenMap.get(node.id)?.length ?? 0) > 0,
      };
      posMap.set(node.id, pn);
      positionedNodes.push(pn);
    });
  });

  const positionedEdges: PositionedEdge[] = [];
  for (const edge of edges) {
    const from = posMap.get(edge.prereqCourseId);
    const to = posMap.get(edge.courseId);
    if (!from || !to) continue;
    positionedEdges.push({
      key: `${edge.prereqCourseId}-${edge.courseId}-${edge.groupNo}`,
      edge,
      x1: from.x + NODE_W + 4,
      y1: from.y + NODE_H / 2,
      x2: to.x - 5,
      y2: to.y + NODE_H / 2,
    });
  }

  const width =
    PAD_X * 2 +
    sortedLevels.length * NODE_W +
    Math.max(0, sortedLevels.length - 1) * COL_GAP;
  const height = PAD_Y + totalGraphH + PAD_X;

  return { positionedNodes, positionedEdges, columns, width, height };
}

export default function PrerequisiteGraphView({
  notify,
}: {
  notify: (s: string) => void;
}) {
  const [graph, setGraph] = useState<PrereqGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [groupFilter, setGroupFilter] = useState("KIT");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  // Pan & zoom state (shared seamlessly between embedded & pop-up canvas)
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(0.92);
  const [isPanning, setIsPanning] = useState(false);
  const dragRef = useRef<{
    active: boolean;
    moved: boolean;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  }>({
    active: false,
    moved: false,
    startX: 0,
    startY: 0,
    origX: 0,
    origY: 0,
  });

  useEffect(() => {
    let active = true;
    setLoading(true);
    void api
      .getPrerequisiteGraph()
      .then((res) => {
        if (!active) return;
        setGraph(res);
        const hasKit = res.nodes.some((n) => KIT_CODES.has(n.code));
        if (!hasKit) setGroupFilter("ALL");
      })
      .catch((e) => {
        if (active) notify((e as Error).message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // Close node detail pop-up first, then fullscreen DAG pop-up on Escape
  useEffect(() => {
    if (!isPopupOpen && selectedId === null) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (selectedId !== null) setSelectedId(null);
      else if (isPopupOpen) setIsPopupOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isPopupOpen, selectedId]);

  const nodeByCode = useMemo(() => {
    const map = new Map<string, PrereqGraphNode>();
    if (graph) {
      for (const n of graph.nodes) map.set(n.code, n);
    }
    return map;
  }, [graph]);

  const availablePrefixes = useMemo(() => {
    if (!graph) return [];
    const set = new Set<string>();
    for (const n of graph.nodes) {
      const m = /^([A-Z]+)/.exec(n.code);
      if (m) set.add(m[1]);
    }
    return Array.from(set).sort();
  }, [graph]);

  const hasKitCourses = useMemo(
    () => Boolean(graph?.nodes.some((n) => KIT_CODES.has(n.code))),
    [graph],
  );

  const visibleNodes = useMemo(() => {
    if (!graph) return [];
    const q = search.trim().toLowerCase();
    return graph.nodes.filter((n) => {
      if (groupFilter === "KIT" && !KIT_CODES.has(n.code)) return false;
      if (
        groupFilter !== "ALL" &&
        groupFilter !== "KIT" &&
        !n.code.startsWith(groupFilter)
      ) {
        return false;
      }
      if (statusFilter !== "ALL" && n.status !== statusFilter) return false;
      if (
        q &&
        !n.code.toLowerCase().includes(q) &&
        !n.name.toLowerCase().includes(q)
      ) {
        return false;
      }
      return true;
    });
  }, [graph, groupFilter, statusFilter, search]);

  const visibleIdSet = useMemo(
    () => new Set(visibleNodes.map((n) => n.id)),
    [visibleNodes],
  );

  const visibleEdges = useMemo(() => {
    if (!graph) return [];
    return graph.edges.filter(
      (e) => visibleIdSet.has(e.courseId) && visibleIdSet.has(e.prereqCourseId),
    );
  }, [graph, visibleIdSet]);

  const layout = useMemo(
    () => computeAirflowLayout(visibleNodes, visibleEdges),
    [visibleNodes, visibleEdges],
  );

  // Reset pan when filter changes so graph stays centered
  useEffect(() => {
    setPan({ x: 0, y: 0 });
    setZoom(visibleNodes.length > 25 ? 0.8 : 0.94);
  }, [groupFilter, statusFilter, search, visibleNodes.length]);

  const activeFocusId = hoveredId ?? selectedId;

  const { upstreamSet, downstreamSet } = useMemo(() => {
    const up = new Set<number>();
    const down = new Set<number>();
    if (!activeFocusId || !graph) {
      return { upstreamSet: up, downstreamSet: down };
    }
    const upStack = [activeFocusId];
    while (upStack.length) {
      const cur = upStack.pop()!;
      for (const e of visibleEdges) {
        if (e.courseId === cur && !up.has(e.prereqCourseId)) {
          up.add(e.prereqCourseId);
          upStack.push(e.prereqCourseId);
        }
      }
    }
    const downStack = [activeFocusId];
    while (downStack.length) {
      const cur = downStack.pop()!;
      for (const e of visibleEdges) {
        if (e.prereqCourseId === cur && !down.has(e.courseId)) {
          down.add(e.courseId);
          downStack.push(e.courseId);
        }
      }
    }
    return { upstreamSet: up, downstreamSet: down };
  }, [activeFocusId, graph, visibleEdges]);

  const selectedNode = useMemo(
    () => graph?.nodes.find((n) => n.id === selectedId) || null,
    [graph, selectedId],
  );

  const unlockedBySelected = useMemo(() => {
    if (!selectedNode || !graph) return [];
    const nodeMap = new Map(graph.nodes.map((n) => [n.id, n]));
    return graph.edges
      .filter((e) => e.prereqCourseId === selectedNode.id)
      .map((e) => nodeMap.get(e.courseId))
      .filter((n): n is PrereqGraphNode => Boolean(n));
  }, [selectedNode, graph]);

  const counts = useMemo(() => {
    if (!graph) return { completed: 0, eligible: 0, locked: 0 };
    return {
      completed: graph.nodes.filter((n) => n.status === "COMPLETED").length,
      eligible: graph.nodes.filter((n) => n.status === "ELIGIBLE").length,
      locked: graph.nodes.filter((n) => n.status === "LOCKED").length,
    };
  }, [graph]);

  const handlePointerDown = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      if (e.button !== 0) return;
      // Ignore clicks on toolbar controls
      if ((e.target as HTMLElement).closest("[data-dag-control='true']")) {
        return;
      }
      dragRef.current = {
        active: true,
        moved: false,
        startX: e.clientX,
        startY: e.clientY,
        origX: pan.x,
        origY: pan.y,
      };
    },
    [pan.x, pan.y],
  );

  const handlePointerMove = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      if (!dragRef.current.active) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      if (!dragRef.current.moved) {
        if (Math.abs(dx) <= 5 && Math.abs(dy) <= 5) return;
        dragRef.current.moved = true;
        setIsPanning(true);
        e.currentTarget.setPointerCapture(e.pointerId);
      }
      setPan({
        x: dragRef.current.origX + dx,
        y: dragRef.current.origY + dy,
      });
    },
    [],
  );

  const handlePointerUp = useCallback(
    (e: ReactPointerEvent<HTMLDivElement>) => {
      if (!dragRef.current.active) return;
      dragRef.current.active = false;
      setIsPanning(false);
      if (e.currentTarget.hasPointerCapture(e.pointerId)) {
        e.currentTarget.releasePointerCapture(e.pointerId);
      }
    },
    [],
  );

  const handleWheel = useCallback(
    (e: ReactWheelEvent<HTMLDivElement>) => {
      if (!isPopupOpen && !e.ctrlKey) return;
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.08 : -0.08;
      setZoom((z) =>
        Math.min(1.8, Math.max(0.4, Number((z + delta).toFixed(2)))),
      );
    },
    [isPopupOpen],
  );

  const resetView = useCallback(() => {
    setPan({ x: 0, y: 0 });
    setZoom(visibleNodes.length > 25 ? 0.8 : 0.94);
  }, [visibleNodes.length]);

  const renderFilterControls = () => (
    <div
      className="actions"
      style={{ flexWrap: "wrap", gap: 10, alignItems: "center" }}
    >
      <select
        aria-label="Lọc nhóm môn"
        value={groupFilter}
        onChange={(e) => {
          setGroupFilter(e.target.value);
          setSelectedId(null);
        }}
      >
        {hasKitCourses && (
          <option value="KIT">Bộ môn cốt lõi (KIT — 12 môn)</option>
        )}
        {availablePrefixes.map((prefix) => (
          <option key={prefix} value={prefix}>
            {PREFIX_LABELS[prefix] || `Nhóm ${prefix}`}
          </option>
        ))}
        <option value="ALL">
          Tất cả môn trong khoa ({graph?.nodes.length || 0} môn)
        </option>
      </select>

      <select
        aria-label="Lọc trạng thái"
        value={statusFilter}
        onChange={(e) => setStatusFilter(e.target.value)}
      >
        <option value="ALL">Mọi trạng thái</option>
        <option value="COMPLETED">Đã hoàn thành ({counts.completed})</option>
        <option value="ELIGIBLE">
          Đủ điều kiện học ngay ({counts.eligible})
        </option>
        <option value="LOCKED">Chưa đủ điều kiện ({counts.locked})</option>
      </select>

      <input
        aria-label="Tìm mã hoặc tên học phần trên đồ thị"
        placeholder="Tìm mã hoặc tên môn…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div
        className="muted"
        style={{
          marginLeft: "auto",
          fontSize: 12.5,
          display: "flex",
          gap: 14,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <span>━━ AND (bắt buộc)</span>
        <span>┅┅ OR (chọn 1)</span>
        <span style={{ color: "#00529c", fontWeight: 600 }}>● Tiên quyết</span>
        <span style={{ color: "#d71920", fontWeight: 600 }}>● Mở khóa</span>
      </div>
    </div>
  );

  const renderDagCanvas = (fullscreen: boolean) => {
    const normalEdges: PositionedEdge[] = [];
    const hiEdges: Array<PositionedEdge & { direction: "up" | "down" }> = [];

    for (const pe of layout.positionedEdges) {
      if (!activeFocusId) {
        normalEdges.push(pe);
        continue;
      }
      const { courseId, prereqCourseId } = pe.edge;
      const isUp =
        (courseId === activeFocusId || upstreamSet.has(courseId)) &&
        upstreamSet.has(prereqCourseId);
      const isDown =
        (prereqCourseId === activeFocusId ||
          downstreamSet.has(prereqCourseId)) &&
        downstreamSet.has(courseId);
      if (isUp) {
        hiEdges.push({ ...pe, direction: "up" });
      } else if (isDown) {
        hiEdges.push({ ...pe, direction: "down" });
      } else {
        normalEdges.push(pe);
      }
    }

    const buildPath = (pe: PositionedEdge) => {
      const lead = 8;
      const endCurveX = Math.max(pe.x1 + 10, pe.x2 - lead);
      const dx = Math.max(28, Math.min(88, (endCurveX - pe.x1) * 0.48));
      return `M ${pe.x1} ${pe.y1} C ${pe.x1 + dx} ${pe.y1}, ${endCurveX - dx} ${pe.y2}, ${endCurveX} ${pe.y2} L ${pe.x2} ${pe.y2}`;
    };

    const markerPrefix = fullscreen ? "pop" : "emb";

    return (
      <div
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onWheel={handleWheel}
        style={{
          position: "relative",
          width: "100%",
          height: fullscreen ? "100%" : 540,
          overflow: "hidden",
          borderRadius: 0,
          border: "1px solid #cbd5e1",
          backgroundColor: "#f8fafc",
          backgroundImage:
            "radial-gradient(#cbd5e1 1.15px, transparent 1.15px)",
          backgroundSize: "20px 20px",
          backgroundPosition: `${pan.x}px ${pan.y}px`,
          cursor: isPanning ? "grabbing" : "grab",
          userSelect: "none",
          touchAction: "none",
        }}
      >
        {/* Top-left hint badge */}
        <div
          data-dag-control="true"
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            zIndex: 10,
            background: "rgba(255,255,255,0.92)",
            backdropFilter: "blur(6px)",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: "5px 10px",
            fontSize: 12,
            color: "#475569",
            display: "flex",
            alignItems: "center",
            gap: 8,
            boxShadow: "0 1px 3px rgba(15,23,42,0.06)",
          }}
        >
          <span>
            <b>{visibleNodes.length}</b> môn · <b>{visibleEdges.length}</b> liên
            kết
          </span>
          <span style={{ color: "#94a3b8" }}>|</span>
          <span>Kéo để di chuyển · Di chuột/nhấp để tô sáng luồng</span>
        </div>

        {/* Top-right floating toolbar (Zoom + Corner Pop-up Arrow Button) */}
        <div
          data-dag-control="true"
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            zIndex: 10,
            display: "flex",
            alignItems: "center",
            gap: 6,
            background: "rgba(255,255,255,0.95)",
            backdropFilter: "blur(6px)",
            border: "1px solid #e2e8f0",
            borderRadius: 10,
            padding: 4,
            boxShadow: "0 2px 8px rgba(15,23,42,0.08)",
          }}
        >
          <button
            type="button"
            title="Thu nhỏ"
            aria-label="Thu nhỏ đồ thị"
            onClick={() =>
              setZoom((z) => Math.max(0.4, Number((z - 0.12).toFixed(2))))
            }
            style={{
              padding: "5px 7px",
              borderRadius: 6,
              border: "none",
              background: "transparent",
              color: "#334155",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            <ZoomOut size={16} />
          </button>
          <span
            style={{
              fontSize: 12,
              fontWeight: 600,
              color: "#334155",
              minWidth: 42,
              textAlign: "center",
            }}
          >
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            title="Phóng to"
            aria-label="Phóng to đồ thị"
            onClick={() =>
              setZoom((z) => Math.min(1.8, Number((z + 0.12).toFixed(2))))
            }
            style={{
              padding: "5px 7px",
              borderRadius: 6,
              border: "none",
              background: "transparent",
              color: "#334155",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            <ZoomIn size={16} />
          </button>
          <button
            type="button"
            title="Đặt lại góc nhìn"
            aria-label="Đặt lại góc nhìn"
            onClick={resetView}
            style={{
              padding: "5px 7px",
              borderRadius: 6,
              border: "none",
              background: "transparent",
              color: "#334155",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
            }}
          >
            <RotateCcw size={15} />
          </button>
          <div style={{ width: 1, height: 18, background: "#e2e8f0" }} />
          {!fullscreen ? (
            <button
              type="button"
              title="Mở cửa sổ đồ thị toàn màn hình (Pop-up)"
              aria-label="Mở cửa sổ đồ thị toàn màn hình"
              onClick={() => setIsPopupOpen(true)}
              style={{
                padding: "5px 10px",
                borderRadius: 7,
                border: "1px solid #00529c",
                background: "#00529c",
                color: "#ffffff",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Maximize2 size={14} />
              <span>Mở rộng</span>
              <ArrowUpRight size={14} />
            </button>
          ) : (
            <button
              type="button"
              title="Thu nhỏ về trang chính (Esc)"
              aria-label="Đóng cửa sổ đồ thị toàn màn hình"
              onClick={() => setIsPopupOpen(false)}
              style={{
                padding: "5px 10px",
                borderRadius: 7,
                border: "1px solid #cbd5e1",
                background: "#f8fafc",
                color: "#0f172a",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: 600,
                display: "inline-flex",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Minimize2 size={14} />
              <span>Thu gọn</span>
            </button>
          )}
        </div>

        {/* Pannable & Zoomable Airflow DAG World */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: layout.width,
            height: layout.height,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
          }}
        >
          {/* Level Column Headers */}
          {layout.columns.map((col) => (
            <div
              key={col.level}
              style={{
                position: "absolute",
                left: col.x,
                top: 14,
                width: NODE_W,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                fontSize: 11,
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.05em",
                color: "#64748b",
                borderBottom: "1.5px solid #e2e8f0",
                paddingBottom: 4,
              }}
            >
              <span>Tầng {col.level}</span>
              <span style={{ fontWeight: 500 }}>{col.count} môn</span>
            </div>
          ))}

          {/* SVG Layer for smooth Airflow Bézier edges */}
          <svg
            width={layout.width}
            height={layout.height}
            style={{
              position: "absolute",
              inset: 0,
              pointerEvents: "none",
              overflow: "visible",
            }}
          >
            <defs>
              <marker
                id={`${markerPrefix}-and`}
                viewBox="0 0 10 10"
                markerUnits="userSpaceOnUse"
                markerWidth="8"
                markerHeight="8"
                refX="8"
                refY="5"
                orient="auto"
              >
                <path d="M 0 1.5 L 8.5 5 L 0 8.5 Z" fill="#94a3b8" />
              </marker>
              <marker
                id={`${markerPrefix}-or`}
                viewBox="0 0 10 10"
                markerUnits="userSpaceOnUse"
                markerWidth="8"
                markerHeight="8"
                refX="8"
                refY="5"
                orient="auto"
              >
                <path d="M 0 1.5 L 8.5 5 L 0 8.5 Z" fill="#f59e0b" />
              </marker>
              <marker
                id={`${markerPrefix}-up`}
                viewBox="0 0 10 10"
                markerUnits="userSpaceOnUse"
                markerWidth="9"
                markerHeight="9"
                refX="8.5"
                refY="5"
                orient="auto"
              >
                <path d="M 0 1.2 L 9 5 L 0 8.8 Z" fill="#00529c" />
              </marker>
              <marker
                id={`${markerPrefix}-down`}
                viewBox="0 0 10 10"
                markerUnits="userSpaceOnUse"
                markerWidth="9"
                markerHeight="9"
                refX="8.5"
                refY="5"
                orient="auto"
              >
                <path d="M 0 1.2 L 9 5 L 0 8.8 Z" fill="#d71920" />
              </marker>
            </defs>

            {/* Unfocused / default subtle edges */}
            {normalEdges.map((pe) => {
              const isOr = pe.edge.type === "OR";
              return (
                <path
                  key={pe.key}
                  d={buildPath(pe)}
                  fill="none"
                  stroke={isOr ? "#f59e0b" : "#94a3b8"}
                  strokeWidth={1.4}
                  strokeDasharray={isOr ? "5 4" : undefined}
                  opacity={activeFocusId ? 0.12 : isOr ? 0.78 : 0.58}
                  markerEnd={
                    isOr
                      ? `url(#${markerPrefix}-or)`
                      : `url(#${markerPrefix}-and)`
                  }
                />
              );
            })}

            {/* Highlighted upstream & downstream flow edges on top */}
            {hiEdges.map((pe) => {
              const isOr = pe.edge.type === "OR";
              const isUp = pe.direction === "up";
              return (
                <path
                  key={pe.key}
                  d={buildPath(pe)}
                  fill="none"
                  stroke={isUp ? "#00529c" : "#d71920"}
                  strokeWidth={2.4}
                  strokeDasharray={isOr ? "6 4" : undefined}
                  opacity={0.96}
                  markerEnd={
                    isUp
                      ? `url(#${markerPrefix}-up)`
                      : `url(#${markerPrefix}-down)`
                  }
                />
              );
            })}
          </svg>

          {/* Compact Airflow Task Nodes */}
          {layout.positionedNodes.map(({ node, x, y, hasIn, hasOut }) => {
            const st = STATUS_STYLE[node.status];
            const isSelected = selectedId === node.id;
            const isHovered = hoveredId === node.id;
            const isUpstream = upstreamSet.has(node.id);
            const isDownstream = downstreamSet.has(node.id);
            const isRelated =
              !activeFocusId ||
              activeFocusId === node.id ||
              isUpstream ||
              isDownstream;

            let borderColor = "#cbd5e1";
            if (isSelected || isHovered) borderColor = "#00529c";
            else if (isUpstream) borderColor = "#3b82f6";
            else if (isDownstream) borderColor = "#d71920";

            return (
              <button
                key={node.id}
                type="button"
                onMouseEnter={() => setHoveredId(node.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={(e) => {
                  e.stopPropagation();
                  if (dragRef.current.moved) return;
                  setSelectedId(isSelected ? null : node.id);
                }}
                style={{
                  position: "absolute",
                  left: x,
                  top: y,
                  width: NODE_W,
                  height: NODE_H,
                  padding: "8px 10px 8px 14px",
                  borderRadius: 0,
                  background: "#ffffff",
                  color: "#0f172a",
                  border: `1.5px solid ${borderColor}`,
                  boxShadow:
                    isSelected || isHovered
                      ? "0 4px 14px rgba(0,82,156,0.22)"
                      : "0 1px 3px rgba(15,23,42,0.06)",
                  opacity: isRelated ? 1 : 0.24,
                  textAlign: "left",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "stretch",
                  justifyContent: "space-between",
                  gap: 3,
                  lineHeight: 1.25,
                  transition:
                    "opacity 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease",
                  overflow: "visible",
                }}
              >
                {/* Left Airflow status bar */}
                <span
                  aria-hidden="true"
                  style={{
                    position: "absolute",
                    left: 0,
                    top: 0,
                    bottom: 0,
                    width: 5,
                    borderTopLeftRadius: 0,
                    borderBottomLeftRadius: 0,
                    background: st.accent,
                  }}
                />

                {/* Left & Right Connection Ports */}
                {hasIn && (
                  <span
                    aria-hidden="true"
                    style={{
                      position: "absolute",
                      left: -4,
                      top: "50%",
                      transform: "translateY(-50%)",
                      width: 7,
                      height: 7,
                      borderRadius: "50%",
                      background: "#ffffff",
                      border: `1.5px solid ${borderColor}`,
                    }}
                  />
                )}
                {hasOut && (
                  <span
                    aria-hidden="true"
                    style={{
                      position: "absolute",
                      right: -4,
                      top: "50%",
                      transform: "translateY(-50%)",
                      width: 7,
                      height: 7,
                      borderRadius: "50%",
                      background: "#ffffff",
                      border: `1.5px solid ${borderColor}`,
                    }}
                  />
                )}

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 6,
                    width: "100%",
                  }}
                >
                  <b
                    style={{
                      fontSize: 13,
                      letterSpacing: "0.01em",
                      color: "#0f172a",
                    }}
                  >
                    {node.code}
                  </b>
                  <span
                    style={{
                      fontSize: 10.5,
                      fontWeight: 600,
                      padding: "1px 6px",
                      borderRadius: 999,
                      background: st.badgeBg,
                      color: st.badgeText,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {st.label}
                  </span>
                </div>

                <div
                  title={node.name}
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    lineHeight: 1.25,
                    color: "#1e293b",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    width: "100%",
                  }}
                >
                  {node.name}
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 10.5,
                    color: "#64748b",
                    width: "100%",
                  }}
                >
                  <span>{node.credits} TC</span>
                  <span>
                    {node.minAccumulatedCredits === 0
                      ? "0 TC (Năm 1)"
                      : `≥ ${node.minAccumulatedCredits} TC`}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  const renderNodeDetailPopup = () => {
    if (!selectedNode) return null;
    const st = STATUS_STYLE[selectedNode.status];
    const studentTc = graph?.studentAccumulatedCredits ?? 0;
    const tcMet = selectedNode.missingCredits === 0;

    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="node-popup-title"
        onClick={(e) => {
          if (e.target === e.currentTarget) setSelectedId(null);
        }}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 1100,
          background: "rgba(15, 23, 42, 0.56)",
          backdropFilter: "blur(3px)",
          display: "grid",
          placeItems: "center",
          padding: 16,
        }}
      >
        <div
          style={{
            width: "min(600px, 100%)",
            maxHeight: "88vh",
            overflowY: "auto",
            background: "var(--panel)",
            color: "var(--text)",
            border: "1px solid var(--border)",
            borderTop: `4px solid ${st.accent}`,
            borderRadius: 0,
            boxShadow: "0 24px 60px rgba(15, 23, 42, 0.32)",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flexWrap: "wrap",
                  marginBottom: 6,
                }}
              >
                <span className="code-badge">{selectedNode.code}</span>
                <span
                  style={{
                    fontSize: 11.5,
                    fontWeight: 700,
                    padding: "3px 8px",
                    background: st.badgeBg,
                    color: st.badgeText,
                  }}
                >
                  {st.label}
                </span>
                <span className="muted" style={{ fontSize: 12 }}>
                  Tầng {selectedNode.level}
                </span>
              </div>
              <h2
                id="node-popup-title"
                style={{ margin: 0, fontSize: 20, lineHeight: 1.3 }}
              >
                {selectedNode.name}
              </h2>
            </div>
            <button
              type="button"
              aria-label="Đóng thông tin môn học"
              onClick={() => setSelectedId(null)}
              className="btn-outline"
              style={{ padding: "6px 8px" }}
            >
              <X size={17} />
            </button>
          </div>

          {/* Credit Metrics Strip */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              borderBottom: "1px solid var(--border)",
              background: "var(--soft)",
            }}
          >
            <div
              style={{
                padding: "12px 16px",
                borderRight: "1px solid var(--border)",
              }}
            >
              <div className="muted" style={{ fontSize: 11.5 }}>
                Số tín chỉ môn học
              </div>
              <strong style={{ fontSize: 18 }}>
                {selectedNode.credits} TC
              </strong>
            </div>
            <div
              style={{
                padding: "12px 16px",
                borderRight: "1px solid var(--border)",
              }}
            >
              <div className="muted" style={{ fontSize: 11.5 }}>
                Tín chỉ tích lũy tối thiểu
              </div>
              <strong style={{ fontSize: 18 }}>
                {selectedNode.minAccumulatedCredits === 0
                  ? "0 TC"
                  : `≥ ${selectedNode.minAccumulatedCredits} TC`}
              </strong>
            </div>
            <div style={{ padding: "12px 16px" }}>
              <div className="muted" style={{ fontSize: 11.5 }}>
                Tín chỉ hiện tại của bạn
              </div>
              <strong
                style={{
                  fontSize: 18,
                  color: tcMet ? "#047857" : "#d71920",
                }}
              >
                {studentTc} TC
              </strong>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: tcMet ? "#047857" : "#d71920",
                }}
              >
                {tcMet
                  ? selectedNode.minAccumulatedCredits === 0
                    ? "Mở cho năm nhất"
                    : "Đạt yêu cầu tín chỉ"
                  : `Còn thiếu ${selectedNode.missingCredits} TC`}
              </div>
            </div>
          </div>

          {/* Prerequisites & Unlocks Body */}
          <div style={{ padding: "18px 20px", display: "grid", gap: 16 }}>
            {/* Mandatory AND Prerequisites */}
            <div>
              <div
                style={{
                  fontWeight: 700,
                  fontSize: 13.5,
                  marginBottom: 8,
                  color: "var(--text)",
                }}
              >
                Môn bắt buộc học trước (Tiên quyết AND)
              </div>
              {selectedNode.andPrereqs.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>
                  Không yêu cầu môn tiên quyết bắt buộc.
                </p>
              ) : (
                <div style={{ display: "grid", gap: 6 }}>
                  {selectedNode.andPrereqs.map((code) => {
                    const target = nodeByCode.get(code);
                    const done = target?.status === "COMPLETED";
                    return (
                      <button
                        key={code}
                        type="button"
                        onClick={() => target && setSelectedId(target.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 10,
                          width: "100%",
                          padding: "9px 12px",
                          background: "var(--panel)",
                          color: "var(--text)",
                          border: "1px solid var(--border)",
                          borderLeft: `3px solid ${done ? "#10b981" : "#d71920"}`,
                          textAlign: "left",
                          cursor: target ? "pointer" : "default",
                        }}
                      >
                        <div style={{ minWidth: 0 }}>
                          <b className="mono-id" style={{ marginRight: 8 }}>
                            {code}
                          </b>
                          <span style={{ fontSize: 13 }}>
                            {target?.name || code}
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            padding: "2px 8px",
                            whiteSpace: "nowrap",
                            background: done ? "#ecfdf5" : "#fdecee",
                            color: done ? "#047857" : "#d71920",
                          }}
                        >
                          {done ? "Đã hoàn thành" : "Chưa đạt"}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>

            {/* OR Prerequisite Groups */}
            {selectedNode.orGroups.length > 0 && (
              <div>
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: 13.5,
                    marginBottom: 8,
                    color: "var(--text)",
                  }}
                >
                  Môn tiên quyết thay thế (OR — đạt ít nhất 1 môn mỗi nhóm)
                </div>
                <div style={{ display: "grid", gap: 10 }}>
                  {selectedNode.orGroups.map((group) => (
                    <div
                      key={group.groupNo}
                      style={{
                        border: "1px solid var(--border)",
                        padding: "10px 12px",
                        background: "var(--soft)",
                      }}
                    >
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: "#b45309",
                          marginBottom: 6,
                        }}
                      >
                        Nhóm lựa chọn {group.groupNo}
                      </div>
                      <div style={{ display: "grid", gap: 6 }}>
                        {group.options.map((code) => {
                          const target = nodeByCode.get(code);
                          const done = target?.status === "COMPLETED";
                          return (
                            <button
                              key={code}
                              type="button"
                              onClick={() => target && setSelectedId(target.id)}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                gap: 8,
                                width: "100%",
                                padding: "7px 10px",
                                background: "var(--panel)",
                                color: "var(--text)",
                                border: "1px solid var(--border)",
                                textAlign: "left",
                                cursor: target ? "pointer" : "default",
                              }}
                            >
                              <div>
                                <b
                                  className="mono-id"
                                  style={{ marginRight: 8 }}
                                >
                                  {code}
                                </b>
                                <span style={{ fontSize: 12.5 }}>
                                  {target?.name || code}
                                </span>
                              </div>
                              <span
                                style={{
                                  fontSize: 11,
                                  fontWeight: 700,
                                  color: done ? "#047857" : "#64748b",
                                }}
                              >
                                {done ? "Đã hoàn thành" : "Chưa đạt"}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Downstream Unlocked Courses */}
            <div>
              <div
                style={{
                  fontWeight: 700,
                  fontSize: 13.5,
                  marginBottom: 8,
                  color: "var(--text)",
                }}
              >
                Môn mở khóa sau khi hoàn thành học phần này
              </div>
              {unlockedBySelected.length === 0 ? (
                <p className="muted" style={{ margin: 0 }}>
                  Môn cuối nhánh (không có môn phụ thuộc phía sau).
                </p>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {unlockedBySelected.map((n) => (
                    <button
                      key={n.id}
                      type="button"
                      className="btn-outline"
                      onClick={() => setSelectedId(n.id)}
                      style={{
                        padding: "6px 10px",
                        fontSize: 12,
                        fontWeight: 600,
                      }}
                    >
                      <span className="mono-id">{n.code}</span> — {n.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div
            style={{
              padding: "12px 20px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              justifyContent: "flex-end",
            }}
          >
            <button
              type="button"
              className="primary"
              onClick={() => setSelectedId(null)}
            >
              Đóng
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Sơ đồ tiên quyết học phần</h1>
          <p className="muted">
            Kéo thả để di chuyển đồ thị, di chuột hoặc nhấp vào từng môn để xem
            chuỗi môn bắt buộc và các môn mở khóa tiếp theo.
          </p>
        </div>
        {graph && (
          <span className="pill">
            Tích lũy {graph.studentAccumulatedCredits} tín chỉ
          </span>
        )}
      </div>

      <section className="panel" style={{ marginBottom: 16 }}>
        {renderFilterControls()}
      </section>

      {loading ? (
        <div className="skeleton">Đang dựng đồ thị tiên quyết…</div>
      ) : !visibleNodes.length ? (
        <div className="panel empty">Không tìm thấy học phần phù hợp.</div>
      ) : (
        <section className="panel" style={{ padding: 12 }}>
          {renderDagCanvas(false)}
        </section>
      )}

      {/* Full-screen Interactive Pop-up Modal */}
      {isPopupOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Cửa sổ đồ thị tiên quyết toàn màn hình"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 1000,
            background: "rgba(15, 23, 42, 0.58)",
            backdropFilter: "blur(4px)",
            padding: 16,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              background: "#ffffff",
              color: "#0f172a",
              borderRadius: 0,
              flex: 1,
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              boxShadow: "0 24px 64px rgba(15,23,42,0.35)",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: "12px 18px",
                borderBottom: "1px solid #e2e8f0",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                flexWrap: "wrap",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <b style={{ fontSize: 16 }}>
                  Đồ thị tiên quyết (Airflow DAG View)
                </b>
                {graph && (
                  <span className="pill">
                    Tích lũy: {graph.studentAccumulatedCredits} TC
                  </span>
                )}
              </div>
              <button
                type="button"
                aria-label="Đóng cửa sổ"
                onClick={() => setIsPopupOpen(false)}
                style={{
                  border: "1px solid #cbd5e1",
                  background: "#f8fafc",
                  color: "#0f172a",
                  borderRadius: 8,
                  padding: "6px 10px",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                <X size={16} />
                Đóng
              </button>
            </div>

            {/* Modal Filters */}
            <div
              style={{
                padding: "10px 18px",
                borderBottom: "1px solid #f1f5f9",
                background: "#fcfcfd",
              }}
            >
              {renderFilterControls()}
            </div>

            {/* Modal Interactive Canvas */}
            <div style={{ flex: 1, minHeight: 0, padding: 12 }}>
              {visibleNodes.length ? (
                renderDagCanvas(true)
              ) : (
                <div className="empty">Không tìm thấy học phần phù hợp.</div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Course Detail Pop-up Modal (works over both embedded & fullscreen DAG) */}
      {renderNodeDetailPopup()}
    </div>
  );
}
