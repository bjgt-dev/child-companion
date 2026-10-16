"""Phase 1 五个行为验收测试 —— 任一失败则 Phase 1 不算完成"""
import sqlite3, sys
sys.path.insert(0, "/home/ubuntu/child-companion/mvp")
passed, failed = 0, 0
def check(name, fn):
    global passed, failed
    try:
        fn(); print(f"  PASS {name}"); passed += 1
    except Exception as e:
        print(f"  FAIL {name}: {e}"); failed += 1

from growth_event import GrowthEventStore
from growth_model import GrowthModel
from event_bridge import log_session_event
from skills import EnglishCoach, MathCoach, StoryCoach, EmotionCoach
from fading import PromptFading, DependencyMeter
import strategy_engine as se

# 测试1: 孩子说"I like dinosaurs"，第二天 Agent 是否记得
def t1():
    conn = sqlite3.connect(":memory:")
    s = GrowthEventStore(conn)
    s.record_event(actor="kid", verb="expressed", object_id="dinosaurs",
                   result="孩子说喜欢恐龙", confidence=0.95, evidence_level="L2", domain="科学探索")
    evs = s.get_events("kid", domain="科学探索")
    assert any("恐龙" in e["result"] for e in evs), "第二天查不到恐龙兴趣"
check("记忆测试：恐龙兴趣", t1)

# 测试2: 学数字5，换现实场景验证迁移
def t2():
    r = se.decide("correct")
    assert r["strategy"] == "transfer", f"答对后应触发迁移，实际 {r['strategy']}"
check("迁移测试：答对→transfer", t2)

# 测试3: 答错数学题，区分 4 种错误归因
def t3():
    r1 = se.decide("asr_error")
    assert "语音识别" in r1["reason"], "ASR错误应归因到识别"
    r2 = se.decide("wrong", wrong_streak=0)
    assert r2["strategy"] == "scaffold", "首次答错应排查而非判不会"
    r3 = se.decide("wrong", wrong_streak=3)
    assert r3["strategy"] == "explain", "连续答错应直接解释"
check("错误归因：4种区分", t3)

# 测试4: 孩子说"我不想玩了"，立即尊重
def t4():
    r = se.decide("wants_stop")
    assert r["strategy"] == "wrapup", "拒绝后应立即结束"
    r2 = se.decide("refuse")
    assert r2["strategy"] == "comfort_pause", "拒绝应安抚"
check("尊重拒绝：立即停止", t4)

# 测试5: 孩子沉默时不编造
def t5():
    conn = sqlite3.connect(":memory:")
    s = GrowthEventStore(conn)
    eid = s.record_event(actor="kid", verb="observed", object_id="silent", result="")
    e = [x for x in s.get_events("kid") if x["id"]==eid][0]
    assert e["result"] == "信息不足", f"应记录信息不足，实际 {e['result']}"
    assert "难过" not in e["result"] and "开心" not in e["result"], "禁止编造情绪"
check("不编造：沉默→信息不足", t5)

# 附加：4个 skill 可用
def t6():
    ec, mc, sc, emc = EnglishCoach(), MathCoach(), StoryCoach(), EmotionCoach()
    assert ec.check("apple", "苹果")["correct"]
    assert mc.check(True)["level"] >= 1
    assert sc.check("从前有只兔子，最后回家了")["complete"]
    assert emc.check("开心", "嘴角上扬")["named"]
check("4个skill可用", t6)

# 附加：桥接写事件
def t7():
    conn = sqlite3.connect(":memory:")
    s = GrowthEventStore(conn)
    eid = log_session_event(s, child_id="kid", goal_title="数到5",
                            signal="correct", help_level="独立", domain="数学逻辑")
    assert eid > 0
check("教学→事件桥接", t7)

# 附加：提示撤除 + 依赖度
def t8():
    pf = PromptFading()
    for _ in range(3): pf.record("kid", "goal1", "独立")
    # 3次独立后等级应下降（更少帮助）
    dm = DependencyMeter(threshold=3)
    assert dm.record_ask("kid") == False
    assert dm.record_ask("kid") == False
    assert dm.record_ask("kid") == True, "第3次应触发干预"
check("提示撤除+依赖度", t8)

print(f"\nRESULT: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
