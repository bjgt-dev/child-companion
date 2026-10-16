"""统一教学闭环 —— V1.1 第七章。

9 步：1 定目标 → 2 查课程与学习记录 → 3 识别已接触资源 → 4 选下一步活动
→ 5 观察反应 → 6 调整教学 → 7 验证理解和迁移 → 8 更新学习记录
→ 9 安排复习/结束

结束时必须回答 5 个问题（第七章末）。
"""
from strategy_engine import decide, next_mastery, MASTERY_CN, SIGNALS_CN, STRATEGIES


class Session:
    """一次教学活动会话。"""

    def __init__(self, store, goal_id):
        g = store.get_goal(goal_id)
        if g is None:
            raise ValueError("goal %s 不存在" % goal_id)
        self.store = store
        self.goal = dict(g)
        self.wrong_streak = 0
        self.trace = []

    def brief(self):
        """第 1-4 步：定目标 / 查记录 / 识别资源 / 选活动。"""
        g = self.goal
        print("[目标] %s（%s）" % (g["title"], g["domain"]))
        print("[当前状态] %s" % MASTERY_CN[g["status"]])
        obs = self.store.recent_observations(g["id"], 3)
        if obs:
            print("[近期记录]")
            for o in obs:
                print("  - [%s] %s" % (o["evidence_kind"], o["performance"]))
        else:
            print("[近期记录] 无（新目标）")
        concepts = self.store.concepts_for_goal(g["id"])
        if concepts:
            print("[已映射资源]")
            for c in concepts:
                print("  - %s（%s）：%s → %s" % (
                    c["resource_name"], c["resource_type"],
                    c["topic"], c["concept"]))

    def child_signal(self, signal, note=""):
        """第 5-6 步：观察反应 → 调整教学；第 8 步：更新学习记录。"""
        d = decide(signal, wrong_streak=self.wrong_streak)
        if signal == "wrong":
            self.wrong_streak += 1
        elif signal in ("correct", "transfer_ok"):
            self.wrong_streak = 0

        perf = SIGNALS_CN.get(signal, signal)
        help_level, independent, transferred = None, None, 0
        if signal in ("correct", "transfer_ok"):
            help_level, independent = "独立", 1
        elif signal == "partial":
            help_level, independent = "少量提示", 0
        elif signal == "wrong":
            independent = 0
        if signal == "transfer_ok":
            transferred = 1

        self.store.add_observation(
            self.goal["id"], "B", perf, help_level=help_level,
            independent=independent, transferred=transferred, note=note)

        tcount = self._transfer_ok_count()
        new_state = next_mastery(
            self.goal["status"], signal, transfer_ok_count=tcount)
        if new_state != self.goal["status"]:
            self.store.set_mastery(self.goal["id"], new_state)
            print("  状态：%s → %s" % (
                MASTERY_CN[self.goal["status"]], MASTERY_CN[new_state]))
            self.goal["status"] = new_state

        self.trace.append((signal, d["strategy"]))
        extra = "（%s）" % note if note else ""
        print("  孩子：%s%s" % (perf, extra))
        print("  策略：%s —— %s" % (STRATEGIES[d["strategy"]], d["reason"]))
        return d

    def _transfer_ok_count(self):
        rows = self.store.recent_observations(self.goal["id"], limit=50)
        return sum(1 for r in rows if r["transferred"])

    def finish(self, review_days=2, review_note=""):
        """第 9 步：安排复习/结束 + 回答 5 个问题。"""
        s = self.store
        if self.trace and self.trace[-1][0] != "wants_stop":
            s.schedule_review(self.goal["id"], days=review_days)
            tail = "：%s" % review_note if review_note else ""
            print("\n[已安排间隔复习] %d 天后%s" % (review_days, tail))
        print("\n===== 本次活动复盘（V1.1 第七章 5 问）=====")
        print("1. 希望发展什么能力？%s（%s）"
              % (self.goal["title"], self.goal["domain"]))
        contacted = [dict(r) for r in s.usable_resources() if r["contacted"]]
        names = "；".join(r["name"] for r in contacted) or "无"
        print("2. 孩子接触了哪些内容？%s" % names)
        print("3. 实际观察到了什么？")
        for o in s.recent_observations(self.goal["id"], 10):
            tail = "（%s）" % o["note"] if o["note"] else ""
            print("   - [%s] %s%s" % (o["evidence_kind"], o["performance"], tail))
        print("4. 证据与不确定：以上均为 [B] 互动观察实证；"
              "未做 [C] 推测；掌握状态以多次观察为准。")
        last = self.trace[-1] if self.trace else ("-", "-")
        print("5. 下一步：%s；当前掌握状态：%s"
              % (STRATEGIES[last[1]], MASTERY_CN[self.goal["status"]]))
        print("==========================================")
