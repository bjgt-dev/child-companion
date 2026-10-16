"""Safety Agent 最小版 —— V3.0 Phase 0
危险行为拦截、成人内容过滤、使用时长上限。"""
from __future__ import annotations
import re
from datetime import datetime, timedelta

# 危险行为关键词（最小集合，可扩展）
DANGER_PATTERNS = [
    r"自杀", r"自残", r"跳楼", r"吃药.*死",
    r"suicide", r"kill myself", r"hurt myself",
    r"离家出走",
]
# 成人内容关键词（最小集合）
ADULT_PATTERNS = [
    r"性交", r"色情", r"裸体",
    r"porn", r"sex video",
]
# 每日使用上限（分钟）
DAILY_LIMIT_MIN = 60

_usage = {}  # child_id -> [datetime, ...]


def check_text(text: str) -> dict:
    """检查文本。返回 {"safe": bool, "reason": str}。"""
    for p in DANGER_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return {"safe": False, "reason": "危险行为内容，已拦截并建议求助可信成年人"}
    for p in ADULT_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return {"safe": False, "reason": "成人内容，已过滤"}
    return {"safe": True, "reason": ""}


def check_usage(child_id: str, minutes: int = 1) -> dict:
    """记录并检查使用时长。返回 {"allowed": bool, "used_min": int}。"""
    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    key = f"{child_id}:{day}"
    lst = _usage.setdefault(key, [])
    # 清理过期（只保留今天）
    lst[:] = [t for t in lst if t.strftime("%Y-%m-%d") == day]
    used = len(lst) * 1  # 每次调用记 1 分钟（简化）
    if used + minutes > DAILY_LIMIT_MIN:
        return {"allowed": False, "used_min": used}
    for _ in range(minutes):
        lst.append(now)
    return {"allowed": True, "used_min": used + minutes}


def reset_usage():
    _usage.clear()
