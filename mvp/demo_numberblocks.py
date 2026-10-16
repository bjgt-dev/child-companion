"""演示：一次完整的 Numberblocks 融合教学闭环（V1.1 6.3 六步流程）。

主题：数学「数字与数量对应」（能力领域 2）
流程：接触内容 → 理解概念 → 实物操作 → 迁移应用 → 间隔复习 → 更新学习记录
同时覆盖 V1.1 第十三章部分测试场景：ASR 错误 / 部分答对 / 迁移成功 / 想停止。

运行：python demo_numberblocks.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning_store import Store
from teach_loop import Session
from resources import can_use

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                  "data", "demo.db")
if os.path.exists(DB):
    os.remove(DB)
os.makedirs(os.path.dirname(DB), exist_ok=True)

store = Store(DB)
store.init_db()

# ---- 准备：目标 + 资源（家长已审核） ----
gid = store.add_goal(2, "数字与数量对应", prerequisites="会数 1-5")
rid = store.add_resource(
name="Numberblocks《认识数字 3》", type="视频", topic="数字 3 的数量展示",
domain_ids="2", goal_ids=str(gid), age_fit="4-6 岁",
review_status="approved", link="家长播放列表",
notes="仅限家长预选单集；不自动播放；时长家长定")
ok, why = can_use(dict(store.db.execute(
"SELECT * FROM resources WHERE id =?", (rid,)).fetchone()))
assert ok, why
store.map_concept(rid, "数字 3 的数量展示", "数字与数量对应", gid)
store.set_mastery(gid, "exploring")

s = Session(store, gid)
print("======== 儿童 AI 成长伙伴 · 教学闭环演示 ========")
s.brief()

print("\n── 第一步：接触内容 ──")
store.mark_contacted(rid, needs_followup=1)
print(" 家长播放 Numberblocks《认识数字 3》（单集，已审核）→ 已记录接触")

print("\n── 第二步：理解概念 ──")
print(' AI：「你刚才看到哪些数字？」')
s.child_signal("asr_error", note="孩子说'三个'，识别成'三只'；不记为知识错误")
print(' AI 换一种方式再问：「小方块有几个？你慢慢说。」')
s.child_signal("partial", note="孩子说'有方块……三个？'，语气不确定")
print(" AI 给少量提示：「对，再数一遍，1、2……」")
s.child_signal("correct", note="孩子独立答'3 个方块！'")

print("\n── 第三步：实物操作 ──")
print(" AI：「拿 3 个积木摆出来，再合起来数一遍。」")
s.child_signal("correct", note="用积木摆出 3 个并正确数数，独立完成")

print("\n── 第四步：迁移应用 ──")
print(" AI：「我们去数楼梯，看看有没有 3 级。」")
s.child_signal("transfer_ok", note="在楼梯场景独立数出 3 级")

print("\n── 第五步：间隔复习（安排）+ 第六步：更新学习记录 ──")
print(' 孩子：「我不想玩了。」')
s.child_signal("wants_stop")
s.finish(review_days=2, review_note="换水果重新数 3 个，验证迁移稳定性")

# ---- 六层区分（V1.1 6.3）：看过 / 能描述 / 实物表现 / 独立解决 / 迁移 ----
print("\n")
print(" 看过相关内容：✓（视频已标记接触）")
print(" 能够描述内容：✓（答出'3 个方块'，B 证据）")
print(" 能够通过实物表现概念：✓（积木，B 证据）")
print(" 能够独立解决相关问题：✓（独立完成，B 证据）")
print(" 能够在新场景中迁移：△ 1 次（需第 2 次迁移才算基本掌握）")
print(" 背出台词≠掌握：本记录只认实物与迁移证据 ✓")

store.close()
print("\n演示完成：数据库", DB)
