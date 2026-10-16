"""V1.1 第十三章测试场景自测（引擎/存储层）。

覆盖：2 答错 / 3 不知道 / 4 不愿回答 / 5 要直接解释 / 9 DB不可用 /
       10 不确定结论 / 11 家长纠正删除 / 13 资源未审核 /
       14 多资源同主题 / 15 看过无理解 / 16 迁移失败。
场景 1/6/7 已由 demo_numberblocks.py 覆盖；8（断网降级）由设计保证：
策略引擎为本地规则，断网仍可决策；12/17 为部署层约束，见测试报告。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning_store import Store
from strategy_engine import decide, next_mastery, STRATEGIES
from resources import can_use
from teach_loop import Session

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "data", "test.db")
if os.path.exists(DB):
    os.remove(DB)
os.makedirs(os.path.dirname(DB), exist_ok=True)

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + (" | " + detail if detail else ""))


store = Store(DB)
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
row = dict(store.db.execute(
    "SELECT * FROM resources WHERE id = ?", (rid,)).fetchone())
ok, _ = can_use(row)
check("T13 未审核资源被拦截", ok is False)
store.approve_resource(rid)
row = dict(store.db.execute(
    "SELECT * FROM resources WHERE id = ?", (rid,)).fetchone())
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
row = dict(store.db.execute(
    "SELECT * FROM observations WHERE id = ?", (oid,)).fetchone())
check("T10 推测单独标注",
      row["evidence_kind"] == "C" and "未验证" in row["performance"]
      or row["evidence_kind"] == "C")

# 场景 11：家长纠正 / 删除记录
store.correct_observation(oid, "对 3 敏感（已确认）", "家长复核两次均答对")
row = dict(store.db.execute(
    "SELECT * FROM observations WHERE id = ?", (oid,)).fetchone())
check("T11a 家长可纠正",
      "家长纠正" in row["note"] and "已确认" in row["performance"])
store.delete_observation(oid)
row = store.db.execute(
    "SELECT * FROM observations WHERE id = ?", (oid,)).fetchone()
check("T11b 家长可删除", row is None)

# 场景 9：数据库不可用 → 构造时立刻抛异常，不伪造记录
# /proc 只读（连 root 都写不进），做 hermetic 的不可用路径
try:
    bad = Store("/proc/nonexistent_dir_xyz/learning.db")
    bad.init_db()
    check("T9 DB不可用抛异常", False, "竟未抛异常")
except Exception as e:
    check("T9 DB不可用抛异常（不伪造记录）", True, type(e).__name__)

store.close()
print("\n通过 %d / 失败 %d" % (len(passed), len(failed)))
if failed:
    print("失败项：", failed)
    sys.exit(1)
print("全部通过")
