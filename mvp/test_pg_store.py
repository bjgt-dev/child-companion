"""PG 后端自测：与 test_scenarios.py 的 15 个场景一一对应，跑在 PGStore 上。

- 测的是 child_companion_test 库（测试库，与迁移后的生产库 child_companion 隔离），
  建表/种子/测试数据都在测试库里，不污染生产数据。
- 场景编号与 test_scenarios.py 一致（T2a/T2b/T3/T4/T5/T13/T13b/T14/T15/
  T16/T16b/T10/T11a/T11b/T9）。
- T9：传一个连不上的 DSN，构造时必须立刻抛异常（不伪造记录）。

运行：python3 test_pg_store.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg

from learning_store_pg import PGStore, resolve_dsn
from strategy_engine import decide, next_mastery, STRATEGIES
from resources import can_use
from teach_loop import Session


def make_test_dsn() -> str:
    """由生产 DSN 派生测试库 DSN，并确保测试库存在。"""
    dsn = resolve_dsn()
    test_dsn = re.sub(r"/([^/?#]+)(\?|#|$)", r"/child_companion_test\2", dsn, count=1)
    if test_dsn == dsn:
        raise RuntimeError("无法从 DSN 派生测试库名：%s" % dsn.split("@")[-1])
    admin_dsn = re.sub(r"/([^/?#]+)(\?|#|$)", r"/postgres\2", dsn, count=1)
    admin = psycopg.connect(admin_dsn, autocommit=True)
    exists = admin.execute(
        "SELECT 1 FROM pg_database WHERE datname='child_companion_test'"
    ).fetchone()
    if not exists:
        admin.execute("CREATE DATABASE child_companion_test")
    admin.close()
    return test_dsn


passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail else ""))


store = PGStore(make_test_dsn())
store.init_db()
gid = store.add_goal(2, "数字与数量对应")

# 场景 2：答错 → 逐级提示；连续答错 2 次 → 直接解释+降难度
d1 = decide("wrong", wrong_streak=0)
check("T2a 答错→逐级提示", d1["strategy"] == "scaffold")
d2 = decide("wrong", wrong_streak=2)
check("T2b 连续答错→直接解释", d2["strategy"] == "explain"
      and "降难度" in d2["reason"])

# 场景 3：不知道 → 启发式提问（不是直接判不会）
d = decide("dont_know")
check("T3 不知道→启发式提问", d["strategy"] == "socratic")

# 场景 4：不愿意回答 → 情绪安抚，可暂停（不强迫）
d = decide("refuse")
check("T4 不愿回答→安抚暂停", d["strategy"] == "comfort_pause")

# 场景 5：要求直接解释 → 直接给（不为启发而拒绝）
d = decide("wants_explanation")
check("T5 要解释→直接解释", d["strategy"] == "explain")

# 场景 13：未审核资源不得进入教学
rid = store.add_resource(name="某未知动画", type="视频",
                         review_status="pending")
row = dict(store.conn.execute(
    "SELECT * FROM resources WHERE id = %s", (rid,)).fetchone())
ok, _ = can_use(row)
check("T13 未审核资源被拦截", ok is False)
store.approve_resource(rid)
row = dict(store.conn.execute(
    "SELECT * FROM resources WHERE id = %s", (rid,)).fetchone())
ok, _ = can_use(row)
check("T13b 审核通过后可用", ok is True)

# 场景 14：同一主题来自多个资源 → 映射到同一目标，不建多份记录
r2 = store.add_resource(name="Khan Kids 数数活动", type="结构化课程",
                        review_status="approved")
store.map_concept(rid, "数字 3", "数字与数量对应", gid)
store.map_concept(r2, "数字 3", "数字与数量对应", gid)
maps = store.concepts_for_goal(gid)
check("T14 多资源→同一目标",
      len(maps) == 2 and len({m["goal_id"] for m in maps}) == 1,
      "2 条映射，目标唯一")

# 场景 15：看过视频但无理解表现 → 状态停在 exploring，不判掌握
s = Session(store, gid)
store.set_mastery(gid, "exploring")
st = next_mastery("exploring", "dont_know")
check("T15 无理解证据不升级", st == "exploring")

# 场景 16：原场景会、新场景迁移失败 → recheck，不判掌握
st = next_mastery("partial", "transfer_fail")
check("T16 迁移失败→需重新检查", st == "recheck")
d = decide("transfer_fail")
check("T16b 迁移失败→回实物示范", d["strategy"] == "demo")

# 场景 10：不确定结论必须标注为推测（C），与实证区分
oid = store.add_observation(gid, "C", "可能对 3 敏感",
                            note="仅一次随口回答，未验证")
row = dict(store.conn.execute(
    "SELECT * FROM observations WHERE id = %s", (oid,)).fetchone())
check("T10 推测单独标注", row["evidence_kind"] == "C")

# 场景 11：家长纠正 / 删除记录
store.correct_observation(oid, "对 3 敏感（已确认）", "家长复核两次均答对")
row = dict(store.conn.execute(
    "SELECT * FROM observations WHERE id = %s", (oid,)).fetchone())
check("T11a 家长可纠正",
      "家长纠正" in row["note"] and "已确认" in row["performance"])
store.delete_observation(oid)
row = store.conn.execute(
    "SELECT * FROM observations WHERE id = %s", (oid,)).fetchone()
check("T11b 家长可删除", row is None)

# 场景 9：数据库不可用 → 构造时立刻抛异常，不伪造记录
try:
    bad = PGStore("postgresql://bad:bad@127.0.0.1:1/nope")
    bad.init_db()
    check("T9 DB不可用抛异常", False, "竟未抛异常")
except Exception as e:
    check("T9 DB不可用抛异常（不伪造记录）", True, type(e).__name__)

# PG 特有：中文往返 + get_store 工厂
store2_gid = store.add_goal(1, "中文往返测试目标")
cn_oid = store.add_observation(
    store2_gid, "B", "孩子能指认「苹果」并说出 píngguǒ 🍎",
    help_level="独立", independent=1, transferred=0,
    note="中文备注：观察到迁移能力")
cn_row = dict(store.conn.execute(
    "SELECT * FROM observations WHERE id = %s", (cn_oid,)).fetchone())
check("PG 中文读写无乱码",
      "苹果" in cn_row["performance"] and "píngguǒ" in cn_row["performance"]
      and "中文备注" in cn_row["note"])

from learning_store_pg import get_store  # noqa: E402
default_store = get_store()
check("get_store 默认=SQLite",
      type(default_store).__name__ == "Store")
default_store.close()
pg_store = get_store(backend="pg", dsn=make_test_dsn())
check("get_store(backend='pg')=PGStore",
      type(pg_store).__name__ == "PGStore")
pg_store.close()

store.close()
print("\n通过 %d / 失败 %d" % (len(passed), len(failed)))
if failed:
    print("失败项：", failed)
    sys.exit(1)
print("全部通过")
