"""Phase 3 测试"""
import sys
sys.path.insert(0, "/home/ubuntu/child-companion/mvp")
p = f = 0
def check(n, fn):
    global p, f
    try: fn(); print(f"  PASS {n}"); p += 1
    except Exception as e: print(f"  FAIL {n}: {e}"); f += 1
from ecosystem import SOURCES, numberblocks_chain, source_to_event, ResourceCurator
def t1(): assert len(SOURCES) == 6
check("6类来源", t1)
def t2():
    c = numberblocks_chain(5)
    assert len(c["steps"]) == 6
    assert c["steps"][0]["step"] == "输入" and c["steps"][5]["step"] == "创造"
    c10 = numberblocks_chain(10)
    assert c10["number"] == 10
check("Numberblocks六步链", t2)
def t3():
    e = source_to_event("video", "看了Numberblocks")
    assert e["verb"] == "watched"
    try: source_to_event("unknown", "x"); raise AssertionError("x")
    except ValueError: pass
check("来源→事件映射", t3)
def t4():
    rc = ResourceCurator()
    s = rc.suggest("video", "Numberblocks 第5集")
    assert len(s) == 4 and s[0]["step"] == "对话", s
    s2 = rc.suggest("book", "好饿的毛毛虫")
    assert len(s2) == 4
check("活动建议生成", t4)
print(f"\nRESULT: {p} passed, {f} failed")
sys.exit(1 if f else 0)
