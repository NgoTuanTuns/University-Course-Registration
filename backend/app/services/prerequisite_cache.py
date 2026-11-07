"""Cache Redis cho engine tiên quyết (M2).

Khóa (quy ước Mục 7 + D16; mọi khóa phụ KHÔNG bắt đầu bằng `prereq:` để không bị
xóa nhầm khi xóa theo tiền tố):
  prereq:{student_id}:{course_id}  kết quả check (JSON), TTL = PREREQ_CACHE_TTL_SEC
  prereqgraph:v1                   toàn bộ DAG + danh mục môn, TTL = PREREQ_GRAPH_CACHE_TTL_SEC
  prereqgraph:v1:gen               "thế hệ" dữ liệu, tăng 1 mỗi lần invalidation
  prereqgraph:v1:lock              khóa ngắn (SET NX) để chỉ 1 request dựng lại đồ thị
  metrics:prereq:hit|miss          bộ đếm cache trúng/trượt

Dữ liệu nào đổi -> khóa nào xóa:
  admin thêm/sửa/xóa tiên quyết, xóa môn, seed lại -> invalidate_graph()
      (tăng gen, xóa prereqgraph:v1 và toàn bộ prereq:*)
  completed_courses của một sinh viên đổi            -> invalidate_student(id)
      (tăng gen, xóa prereq:{id}:*)

Vì sao cần `gen`: request A đọc DB cũ, admin sửa + xóa cache, rồi A mới ghi kết quả
cũ vào cache -> trả sai tới hết TTL. Mọi lệnh ghi cache chỉ thành công khi gen
KHÔNG đổi kể từ lúc đọc (kiểm tra và ghi trong cùng một script Lua, nguyên tử).

Cache là tối ưu, không phải điều kiện đúng đắn: Redis lỗi thì ghi cảnh báo và
trả "không có cache", engine tự tính trực tiếp từ DB.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.redis import get_redis
from app.services.prerequisite_core import EligibilityResult, OrGroupResult
from app.services.prerequisite_repository import CourseLabel, GraphSnapshot

logger = logging.getLogger(__name__)

RESULT_PREFIX = "prereq"
GRAPH_KEY = "prereqgraph:v1"
GEN_KEY = "prereqgraph:v1:gen"
GRAPH_LOCK_KEY = "prereqgraph:v1:lock"
METRIC_HIT_KEY = "metrics:prereq:hit"
METRIC_MISS_KEY = "metrics:prereq:miss"
SCAN_BATCH = 500

# Đọc kết quả + gen hiện tại + đếm hit/miss trong MỘT lần gọi Redis.
# Lua: GET khóa không tồn tại trả false; `x or ''` để mảng trả về không bị cắt.
_READ_MANY_LUA = """
local gen = redis.call('GET', KEYS[1]) or '0'
local out = {gen}
local hits, misses = 0, 0
for i = 4, #KEYS do
  local v = redis.call('GET', KEYS[i])
  if v then hits = hits + 1 else misses = misses + 1 end
  out[#out + 1] = v or ''
end
if hits > 0 then redis.call('INCRBY', KEYS[2], hits) end
if misses > 0 then redis.call('INCRBY', KEYS[3], misses) end
return out
"""

# Ghi nhiều khóa CHỈ KHI gen chưa đổi. KEYS[1] = gen; KEYS[2..n] = khóa đích;
# ARGV[1] = gen đã đọc; ARGV[2..n] = giá trị tương ứng; ARGV[n+1] = TTL giây.
_SET_IF_GEN_LUA = """
local gen = redis.call('GET', KEYS[1]) or '0'
if gen ~= ARGV[1] then return 0 end
local ttl = ARGV[#KEYS + 1]
for i = 2, #KEYS do
  redis.call('SET', KEYS[i], ARGV[i], 'EX', ttl)
end
return 1
"""

# Chỉ xóa khóa dựng đồ thị nếu vẫn là của mình (tránh xóa khóa của request khác
# khi khóa của mình đã tự hết hạn).
_RELEASE_LOCK_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


@dataclass
class CachedLookup:
    """Kết quả tra cache. generation=None nghĩa là Redis không dùng được: bỏ qua ghi."""

    results: dict[int, EligibilityResult]
    generation: str | None


def result_key(student_id: int, course_id: int) -> str:
    return f"{RESULT_PREFIX}:{student_id}:{course_id}"


def _result_ttl() -> int:
    return get_settings().prereq_cache_ttl_sec


def _graph_ttl() -> int:
    return get_settings().prereq_graph_cache_ttl_sec


# --------------------------------------------------------------------- tuần tự hóa
def dump_result(result: EligibilityResult) -> str:
    return json.dumps(
        {
            "course_id": result.course_id,
            "course_code": result.course_code,
            "eligible": result.eligible,
            "missing_courses": result.missing_courses,
            "unmet_or_groups": [
                {"group_no": g.group_no, "options": g.options}
                for g in result.unmet_or_groups
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def load_result(raw: str) -> EligibilityResult:
    data = json.loads(raw)
    return EligibilityResult(
        course_id=data["course_id"],
        course_code=data["course_code"],
        eligible=data["eligible"],
        missing_courses=list(data["missing_courses"]),
        unmet_or_groups=[
            OrGroupResult(g["group_no"], list(g["options"]))
            for g in data["unmet_or_groups"]
        ],
    )


def dump_snapshot(snapshot: GraphSnapshot) -> str:
    return json.dumps(
        {
            "edges": [list(e) for e in snapshot.edges],
            "courses": {
                str(cid): [label.code, label.name]
                for cid, label in snapshot.courses.items()
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def load_snapshot(raw: str) -> GraphSnapshot:
    data = json.loads(raw)
    return GraphSnapshot(
        edges=[(int(c), int(p), str(t), int(g)) for c, p, t, g in data["edges"]],
        courses={
            int(cid): CourseLabel(code, name)
            for cid, (code, name) in data["courses"].items()
        },
    )


# --------------------------------------------------------------------- kết quả check
async def read_results(student_id: int, course_ids: Iterable[int]) -> CachedLookup:
    """Tra nhiều kết quả trong một lần gọi; khóa nào trượt thì không có trong `results`."""
    ids = list(dict.fromkeys(course_ids))
    keys = [GEN_KEY, METRIC_HIT_KEY, METRIC_MISS_KEY]
    keys += [result_key(student_id, cid) for cid in ids]
    try:
        script = get_redis().register_script(_READ_MANY_LUA)
        raw = await script(keys=keys)
    except Exception as exc:
        logger.warning("Redis lỗi khi đọc cache tiên quyết, tính trực tiếp: %s", exc)
        return CachedLookup(results={}, generation=None)

    found: dict[int, EligibilityResult] = {}
    for cid, value in zip(ids, raw[1:], strict=True):
        if value:
            try:
                found[cid] = load_result(value)
            except (ValueError, KeyError, TypeError):
                logger.warning("Bỏ qua cache hỏng %s", result_key(student_id, cid))
    logger.debug(
        "prereq cache student=%s hit=%d miss=%d",
        student_id,
        len(found),
        len(ids) - len(found),
    )
    return CachedLookup(results=found, generation=str(raw[0]))


async def store_results(
    student_id: int, results: Iterable[EligibilityResult], generation: str | None
) -> bool:
    """Ghi kết quả (đã dịch sang mã môn) nếu dữ liệu chưa bị invalidation kể từ lúc đọc."""
    items = list(results)
    if generation is None or not items:
        return False
    keys = [GEN_KEY] + [result_key(student_id, int(r.course_id)) for r in items]
    args = [generation] + [dump_result(r) for r in items] + [_result_ttl()]
    try:
        script = get_redis().register_script(_SET_IF_GEN_LUA)
        return bool(await script(keys=keys, args=args))
    except Exception as exc:
        logger.warning("Redis lỗi khi ghi cache tiên quyết: %s", exc)
        return False


# --------------------------------------------------------------------- đồ thị
async def read_graph() -> GraphSnapshot | None:
    try:
        raw = await get_redis().get(GRAPH_KEY)
    except Exception as exc:
        logger.warning("Redis lỗi khi đọc đồ thị tiên quyết: %s", exc)
        return None
    if not raw:
        return None
    try:
        return load_snapshot(raw)
    except (ValueError, KeyError, TypeError):
        logger.warning("Bỏ qua đồ thị cache hỏng %s", GRAPH_KEY)
        return None


async def store_graph(snapshot: GraphSnapshot, generation: str | None) -> bool:
    if generation is None:
        return False
    args = [generation, dump_snapshot(snapshot), _graph_ttl()]
    try:
        script = get_redis().register_script(_SET_IF_GEN_LUA)
        return bool(await script(keys=[GEN_KEY, GRAPH_KEY], args=args))
    except Exception as exc:
        logger.warning("Redis lỗi khi ghi đồ thị tiên quyết: %s", exc)
        return False


async def read_generation() -> str | None:
    try:
        return str(await get_redis().get(GEN_KEY) or "0")
    except Exception as exc:
        logger.warning("Redis lỗi khi đọc thế hệ cache tiên quyết: %s", exc)
        return None


async def try_acquire_graph_lock() -> str | None:
    """SET NX có hạn: trả token nếu giành được quyền dựng lại đồ thị, ngược lại None."""
    token = uuid.uuid4().hex
    try:
        ok = await get_redis().set(
            GRAPH_LOCK_KEY, token, nx=True, ex=get_settings().prereq_graph_lock_ttl_sec
        )
    except Exception as exc:
        logger.warning("Redis lỗi khi lấy khóa dựng đồ thị: %s", exc)
        return None
    return token if ok else None


async def release_graph_lock(token: str) -> None:
    try:
        script = get_redis().register_script(_RELEASE_LOCK_LUA)
        await script(keys=[GRAPH_LOCK_KEY], args=[token])
    except Exception as exc:
        logger.warning("Redis lỗi khi nhả khóa dựng đồ thị: %s", exc)


async def wait_for_graph(
    attempts: int = 10, delay_sec: float = 0.05
) -> GraphSnapshot | None:
    """Request khác đang dựng đồ thị: chờ ngắn rồi đọc lại thay vì cùng truy vấn DB."""
    for _ in range(attempts):
        await asyncio.sleep(delay_sec)
        snapshot = await read_graph()
        if snapshot is not None:
            return snapshot
    return None


# --------------------------------------------------------------------- invalidation
async def _unlink_matching(pattern: str) -> int:
    """SCAN theo mẫu + UNLINK theo lô. Không dùng KEYS (chặn Redis khi nhiều khóa)."""
    client = get_redis()
    deleted = 0
    batch: list[str] = []
    async for key in client.scan_iter(match=pattern, count=SCAN_BATCH):
        batch.append(key)
        if len(batch) >= SCAN_BATCH:
            deleted += await client.unlink(*batch)
            batch.clear()
    if batch:
        deleted += await client.unlink(*batch)
    return deleted


async def invalidate_graph() -> int:
    """DAG/danh mục môn đổi: xóa đồ thị và MỌI kết quả `prereq:*`. Gọi SAU commit."""
    try:
        client = get_redis()
        await client.incr(GEN_KEY)  # tăng gen TRƯỚC để chặn các lệnh ghi đang dở
        deleted = await client.unlink(GRAPH_KEY)
        deleted += await _unlink_matching(f"{RESULT_PREFIX}:*")
    except Exception as exc:
        logger.error("Không xóa được cache tiên quyết (đồ thị): %s", exc)
        return 0
    logger.info("Đã xóa cache tiên quyết: đồ thị + %d khóa", deleted)
    return deleted


async def invalidate_student(student_id: int) -> int:
    """completed_courses của MỘT sinh viên đổi: xóa `prereq:{student_id}:*`. Gọi SAU commit."""
    try:
        await get_redis().incr(GEN_KEY)
        deleted = await _unlink_matching(f"{RESULT_PREFIX}:{student_id}:*")
    except Exception as exc:
        logger.error(
            "Không xóa được cache tiên quyết của sinh viên %s: %s", student_id, exc
        )
        return 0
    logger.info("Đã xóa %d khóa cache tiên quyết của sinh viên %s", deleted, student_id)
    return deleted


# --------------------------------------------------------------------- số liệu
async def get_metrics() -> dict[str, float]:
    try:
        hit, miss = await get_redis().mget(METRIC_HIT_KEY, METRIC_MISS_KEY)
    except Exception as exc:
        logger.warning("Redis lỗi khi đọc số liệu cache: %s", exc)
        return {"hit": 0, "miss": 0, "hit_ratio": 0.0}
    hits, misses = int(hit or 0), int(miss or 0)
    total = hits + misses
    return {"hit": hits, "miss": misses, "hit_ratio": hits / total if total else 0.0}


async def reset_metrics() -> None:
    try:
        await get_redis().delete(METRIC_HIT_KEY, METRIC_MISS_KEY)
    except Exception as exc:
        logger.warning("Redis lỗi khi đặt lại số liệu cache: %s", exc)
