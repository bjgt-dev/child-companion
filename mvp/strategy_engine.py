"""教育策略引擎 —— V1.1 第二章 2.3 / 第四章 4.2

规则引擎，不依赖任何特定大模型：
输入「学习状态 + 本次观察信号」，输出下一步教学策略与理由。
所有决策可追溯、可版本管理（换模型不破坏教育体系）。
"""

# ---- 4.2 教学策略库（11 种） ----
STRATEGIES = {
    "explore":       "自主探索",
    "socratic":      "启发式提问",
    "scaffold":      "逐级提示",
    "explain":       "直接解释",
    "demo":          "实物示范",
    "game":          "游戏化练习",
    "transfer":      "现实情境迁移",
    "review":        "间隔复习",
    "adjust":        "难度调整",
    "comfort_pause": "情绪安抚与活动暂停",
    "wrapup":        "活动总结和结束",
}

STRATEGY_DESC = {
    "explore":       "跟随孩子兴趣开放式探索，不预设标准答案",
    "socratic":      "用简短适龄问题引导孩子自己发现",
    "scaffold":      "从最少提示开始，逐步增加帮助",
    "explain":       "孩子需要时直接讲清楚；不为启发式而拒绝必要的直接解释（4.1-3）",
    "demo":          "用积木/手指/实物把抽象概念变具体",
    "game":          "把练习包进游戏规则里",
    "transfer":      "换场景、换物品，验证是否真会（不能只在原场景答对）",
    "review":        "隔天/几天后换一组材料再测一次",
    "adjust":        "太难就降，太容易就升",
    "comfort_pause": "孩子烦躁或拒绝时先安抚；允许拒绝、暂停、休息（4.1-8）",
    "wrapup":        "总结本次发现；允许结束，不为活跃度硬拖时长",
}

# ---- V3.0 策略版本化 ----
POLICY_VERSION = "v1.0"  # 当前生效版本，对应 education_policy_versions 表
_POLICY_LOG = []  # 每次 decide() 记录 (strategy, policy_version)

# 证据等级（V3.0）：A 可进核心 / B 候选 / C 仅实验 / D 不进核心
EVIDENCE_GRADES = {"A": "核心策略", "B": "候选", "C": "仅实验", "D": "不进核心"}
STRATEGY_GRADES = {s: "A" for s in STRATEGIES}  # v1.0 基线：11 种策略均为 A 级


def set_policy_version(v: str):
    """切换策略版本。"""
    global POLICY_VERSION
    POLICY_VERSION = v


def get_policy_log() -> list:
    """返回本次运行的策略决策日志（含版本号）。"""
    return list(_POLICY_LOG)


# ---- 4.3 掌握状态机 ----
MASTERY = ["uncontacted", "exploring", "learning", "partial", "mastered", "recheck"]
MASTERY_CN = {
    "uncontacted": "未接触",
    "exploring":   "正在探索",
    "learning":    "正在学习",
    "partial":     "初步掌握",
    "mastered":    "多次观察后基本掌握",
    "recheck":     "需要重新检查",
}

# 观察信号（对应 V1.1 第十三章测试场景）
SIGNALS_CN = {
    "correct":           "孩子答对",
    "wrong":             "孩子答错",
    "dont_know":         "孩子不知道答案",
    "refuse":            "孩子不愿意回答",
    "wants_explanation": "孩子要求直接解释",
    "wants_stop":        "孩子想停止活动",
    "asr_error":         "语音识别错误",
    "partial":           "部分答对/需提示才答对",
    "transfer_ok":       "新场景迁移成功",
    "transfer_fail":     "新场景迁移失败",
}


def decide(signal, *, wrong_streak=0):
    """核心决策。返回 {"strategy", "reason"}。

    铁律（V1.1 4.2 / 4.1）：
    - ASR 错误绝不能记为知识错误。
    - 答错先排查：听懂了吗？识别对了吗？要实物辅助吗？再判断重讲。
    - 孩子要直接解释就给，不为启发而拒绝。
    - 孩子拒绝/想停就停，不硬拖。
    """
    if signal == "asr_error":
        return {"strategy": "scaffold",
                "reason": "语音识别不可靠，不能记为知识错误；换一种方式再问一次（放慢/换词/请复述），不扣分、不降状态"}
    if signal == "wants_stop":
        return {"strategy": "wrapup",
                "reason": "孩子想停止：总结本次发现后结束；不为维持活跃度制造新任务"}
    if signal == "refuse":
        return {"strategy": "comfort_pause",
                "reason": "允许拒绝：先安抚，可转轻松陪伴或换活动，不强迫复述/作答"}
    if signal == "wants_explanation":
        return {"strategy": "explain",
                "reason": "孩子明确要求解释：直接讲清楚"}
    if signal == "dont_know":
        return {"strategy": "socratic",
                "reason": "先启发式提问一次；仍不会则转直接解释（不为启发而拒绝解释）"}
    if signal == "wrong":
        if wrong_streak >= 2:
            return {"strategy": "explain",
                    "reason": f"连续答错 {wrong_streak} 次：先直接解释，再降难度（adjust），必要时回实物示范"}
        return {"strategy": "scaffold",
                "reason": "先排查：题目听懂了吗？识别对了吗？需要实物辅助吗？→ 逐级提示，不直接判不会"}
    if signal == "partial":
        return {"strategy": "scaffold",
                "reason": "部分答对：给少量提示看能否独立完成，记录所需帮助程度"}
    if signal == "correct":
        return {"strategy": "transfer",
                "reason": "答对一次不算掌握：换场景/换物品出迁移任务，验证真会"}
    if signal == "transfer_ok":
        return {"strategy": "review",
                "reason": "迁移成功：安排间隔复习（换材料再测），巩固"}
    if signal == "transfer_fail":
        return {"strategy": "demo",
                "reason": "迁移失败：退回实物示范重建直观理解；掌握状态标为需要重新检查"}
    return {"strategy": "explore", "reason": f"未知信号 {signal}：回退到自主探索，不瞎决策"}


def next_mastery(current, signal, transfer_ok_count=0):
    """掌握状态迁移（V1.1 4.3）。

    - 一次答对 / 看完视频永不直接跳 mastered。
    - transfer_ok 需累计 2 次（含本次）才进 mastered，否则停在 partial。
    - 非知识信号（拒绝/想停/ASR 错误/不知道）不降状态。
    """
    order = MASTERY.index(current) if current in MASTERY else 0
    if signal == "transfer_ok":
        return "mastered" if transfer_ok_count >= 2 else "partial"
    if signal == "transfer_fail":
        return "recheck"
    if signal == "correct" and current in ("uncontacted", "exploring"):
        return "learning"
    if signal == "correct" and current == "learning":
        return "partial"
    if signal == "wrong" and current in ("partial", "mastered"):
        return "recheck"
    if signal in ("refuse", "wants_stop", "asr_error", "dont_know"):
        return current  # 不因非知识信号降状态
    return MASTERY[order]


# ---- V3.0：decide() 版本包装 ----
_decide_orig = decide


def decide(signal, *, wrong_streak=0):  # noqa: F811
    """包装原 decide()，附加 policy_version 并记日志。"""
    r = _decide_orig(signal, wrong_streak=wrong_streak)
    r = dict(r)
    r["policy_version"] = POLICY_VERSION
    _POLICY_LOG.append({"signal": signal, "strategy": r["strategy"],
                        "policy_version": POLICY_VERSION})
    return r
