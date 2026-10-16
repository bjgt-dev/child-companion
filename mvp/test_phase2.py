"""Phase 2 测试"""
import sqlite3, sys
sys.path.insert(0, "/home/ubuntu/child-companion/mvp")
p = f = 0
def check(n, fn):
    global p, f
    try: fn(); print(f"  PASS {n}"); p += 1
    except Exception as e: print(f"  FAIL {n}: {e}"); f += 1
from memory import Memory, ReviewScheduler, growth_report
from growth_model import GrowthModel
def t1():
    m = Memory(sqlite3.connect(":memory:"))
    for i in range(5): m.store("kid", "兴趣", f"喜欢恐龙{i}", importance=0.5 + i*0.1)
    m.store("kid", "兴趣", "喜欢恐龙化石", importance=0.9)
    r = m.recall("kid", query="化石", top_k=3)
    assert len(r) == 3 and "化石" in r[0]["content"], r
check("记忆检索", t1)
def t2():
    rs = ReviewScheduler()
    dates = rs.next_reviews("2026-10-17 10:00:00")
    assert dates == ["2026-10-18", "2026-10-20", "2026-10-24", "2026-10-31"], dates
check("间隔复习", t2)
def t3():
    gm = GrowthModel(sqlite3.connect(":memory:"))
    gm.update_domain("kid", "数学逻辑", "从需实物辅助到可心算10以内加法")
    rep = growth_report(gm, "kid")
    assert "心算" in rep and "分" not in rep.replace("10以内", "")
check("成长轨迹无评分", t3)
print(f"\nRESULT: {p} passed, {f} failed")
sys.exit(1 if f else 0)
