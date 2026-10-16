"""Phase 5 测试"""
import sqlite3, sys
sys.path.insert(0, "/home/ubuntu/child-companion/mvp")
p = f = 0
def check(n, fn):
    global p, f
    try: fn(); print(f"  PASS {n}"); p += 1
    except Exception as e: print(f"  FAIL {n}: {e}"); f += 1
from advanced import ResearchPipeline, LearningScientist, ChildDevMonitor, ParentCopilotV2
def t1():
    rp = ResearchPipeline(sqlite3.connect(":memory:"))
    rp.add("间隔学习元分析", "Review of Ed Research", "A", "间隔优于集中")
    rp.add("某博主观点", "社交媒体", "D", "x")
    cands = rp.candidates("B")
    assert len(cands) == 1 and cands[0][0] == "间隔学习元分析"
    try: rp.add("x", grade="Z"); raise AssertionError("x")
    except ValueError: pass
check("研究分级过滤", t1)
def t2():
    ls = LearningScientist()
    r = ls.analyze([{"evidence_level": "L3"}] * 4 + [{"evidence_level": "L1"}] * 6)
    assert r["l3_ratio"] == 0.4 and "推测" in r["suggestion"]
    r2 = ls.analyze([{"evidence_level": "L1"}] * 10)
    assert "健康" in r2["suggestion"]
check("教研分析", t2)
def t3():
    mon = ChildDevMonitor()
    alerts = mon.check({"数学逻辑": "暂无记录", "语言沟通": "良好"}, {"数学逻辑": 35, "语言沟通": 2})
    assert len(alerts) == 1 and "数学逻辑" in alerts[0]
check("发展均衡告警", t3)
def t4():
    pc = ParentCopilotV2()
    rep = pc.weekly("kid1", ["恐龙", "积木"], {"数学逻辑": "进步中", "语言沟通": "暂无记录"})
    assert "恐龙" in rep and "建议活动" in rep and "家长可做的事" in rep
check("家长周报", t4)
print(f"\nRESULT: {p} passed, {f} failed")
sys.exit(1 if f else 0)
