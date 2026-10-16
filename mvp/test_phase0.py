"""Phase 0验收测试"""
import sqlite3, sys
sys.path.insert(0, "/home/ubuntu/child-companion/mvp")
passed, failed = 0, 0
def check(name, fn):
    global passed, failed
    try:
        fn(); print(f"  PASS {name}"); passed += 1
    except Exception as e:
        print(f"  FAIL {name}: {e}"); failed += 1

print("== growth_event ==")
from growth_event import GrowthEventStore, INSUFFICIENT_INFO
conn = sqlite3.connect(":memory:")
store = GrowthEventStore(conn)
def t1():
    eid = store.record_event(actor="kid1", verb="completed", object_id="m1", result="ok", confidence=0.8, evidence_level="L2", domain="d1")
    assert eid == 1
    assert len(store.get_events("kid1")) == 1
check("record+get", t1)
def t2():
    eid = store.record_event(actor="kid1", verb="observed", object_id="x", result="")
    e = [x for x in store.get_events("kid1") if x["id"]==eid][0]
    assert e["result"] == INSUFFICIENT_INFO and e["evidence_level"] == "L1"
check("empty->insufficient", t2)
def t3():
    eid = store.record_event(actor="kid1", verb="observed", object_id="y", result="maybe likes", evidence_level="L3")
    e = [x for x in store.get_events("kid1") if x["id"]==eid][0]
    assert e["result"].startswith("[推测]")
check("L3 mark", t3)
def t4():
    try: store.record_event(actor="kid1", verb="hacked", object_id="x"); raise AssertionError("x")
    except ValueError: pass
check("bad verb reject", t4)
def t5():
    try: store.record_event(actor="kid1", verb="completed", object_id="x", result="95分"); raise AssertionError("x")
    except ValueError: pass
check("score reject", t5)
def t6():
    try: store.record_event(actor="", verb="completed", object_id="x", result="ok"); raise AssertionError("x")
    except ValueError: pass
check("empty actor reject", t6)

print("== growth_model ==")
from growth_model import GrowthModel
conn2 = sqlite3.connect(":memory:")
gm = GrowthModel(conn2)
def t7():
    gm.update_domain("kid1", "数学逻辑", "数量概念表现良好")
    s = gm.get_growth_snapshot("kid1")
    assert "数量概念" in s["数学逻辑"] and s["语言沟通"] == "暂无记录"
check("update+snapshot", t7)
def t8():
    try: gm.update_domain("kid1", "数学逻辑", "英语 85 分"); raise AssertionError("x")
    except ValueError: pass
check("score write reject", t8)

print("== strategy version ==")
import strategy_engine as se
def t9():
    r = se.decide("correct")
    assert r["policy_version"] == "v1.0" and "strategy" in r
check("version in decide", t9)
def t10():
    se.set_policy_version("v1.1"); r = se.decide("wrong")
    assert r["policy_version"] == "v1.1"; se.set_policy_version("v1.0")
check("set version", t10)
def t11():
    assert se.decide("asr_error")["strategy"] == "scaffold"
    assert se.decide("wants_stop")["strategy"] == "wrapup"
    assert se.decide("refuse")["strategy"] == "comfort_pause"
check("orig not regress", t11)

print(f"\nRESULT: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
