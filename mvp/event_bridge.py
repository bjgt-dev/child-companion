"""teach_loop ↔ 成长事件桥接 —— Phase 1
每次教学活动结束时写 learning_event。"""
from __future__ import annotations

def log_session_event(event_store, *, child_id, goal_title, signal, help_level, domain=""):
    """把一次教学互动转为 xAPI 事件。"""
    verb_map = {
        "correct": "completed", "transfer_ok": "transferred",
        "wrong": "attempted", "partial": "attempted",
        "refuse": "refused", "wants_stop": "paused",
        "dont_know": "asked", "asr_error": "attempted",
    }
    verb = verb_map.get(signal, "attempted")
    conf_map = {"独立": 0.9, "少量提示": 0.6, "大量帮助": 0.3}
    conf = conf_map.get(help_level, 0.5)
    return event_store.record_event(
        actor=child_id, verb=verb, object_id=goal_title,
        result=f"{goal_title}：{signal}，帮助程度{help_level or '未知'}",
        confidence=conf, evidence_level="L2", domain=domain,
    )
