import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  Sparkles,
  Clock,
  CheckCheck,
} from "lucide-react";
import type { StudentNotification } from "../api/notifications";

export function NotificationBell({
  userId,
  notifications,
}: {
  userId: number;
  notifications: StudentNotification[];
}) {
  const storageKey = `uniflow_read_notifs_${userId}`;
  const [open, setOpen] = useState(false);
  const [readIds, setReadIds] = useState<string[]>(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      return raw ? (JSON.parse(raw) as string[]) : [];
    } catch {
      return [];
    }
  });
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const nav = useNavigate();

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      setReadIds(raw ? (JSON.parse(raw) as string[]) : []);
    } catch {
      setReadIds([]);
    }
  }, [storageKey]);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const readSet = new Set(readIds);
  const unreadCount = notifications.filter((n) => !readSet.has(n.id)).length;

  const markRead = (ids: string[]) => {
    const merged = Array.from(new Set([...readIds, ...ids]));
    setReadIds(merged);
    try {
      localStorage.setItem(storageKey, JSON.stringify(merged));
    } catch {
      /* ignore storage quota */
    }
  };

  return (
    <div ref={wrapRef} className="notif-wrap">
      <button
        type="button"
        className="notif-trigger"
        aria-label="Trung tâm thông báo"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span
            className="notif-dot"
            aria-label={`${unreadCount} thông báo mới`}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="notif-dropdown" role="region" aria-label="Thông báo">
          <div className="notif-head">
            <div>
              <b>Trung tâm thông báo</b>
              <small className="muted">
                {unreadCount > 0 ? `${unreadCount} chưa đọc` : "Đã đọc tất cả"}
              </small>
            </div>
            {unreadCount > 0 && (
              <button
                type="button"
                className="text-button"
                onClick={() => markRead(notifications.map((n) => n.id))}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  fontSize: 12,
                }}
              >
                <CheckCheck size={14} /> Đọc tất cả
              </button>
            )}
          </div>

          <div className="notif-list">
            {!notifications.length ? (
              <div className="notif-empty">
                Hiện chưa có thông báo học vụ mới nào.
              </div>
            ) : (
              notifications.map((n) => {
                const isUnread = !readSet.has(n.id);
                const Icon =
                  n.kind === "WAITLIST_PROMOTED"
                    ? CheckCircle2
                    : n.kind === "COURSE_NOT_OPENED"
                      ? AlertTriangle
                      : n.kind === "NEW_SECTIONS_OPENED"
                        ? Sparkles
                        : Clock;
                const tone =
                  n.kind === "WAITLIST_PROMOTED"
                    ? "is-success"
                    : n.kind === "COURSE_NOT_OPENED"
                      ? "is-danger"
                      : n.kind === "NEW_SECTIONS_OPENED"
                        ? "is-info"
                        : "is-neutral";
                return (
                  <button
                    key={n.id}
                    type="button"
                    className={`notif-item ${tone} ${isUnread ? "is-unread" : ""}`}
                    onClick={() => {
                      markRead([n.id]);
                      setOpen(false);
                      if (n.link) nav(n.link);
                    }}
                  >
                    <span className="notif-icon">
                      <Icon size={16} />
                    </span>
                    <div className="notif-body">
                      <div className="notif-title">
                        <b>{n.title}</b>
                        {isUnread && <i className="notif-unread-pill" />}
                      </div>
                      <p>{n.message}</p>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
