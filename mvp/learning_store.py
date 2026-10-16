"""学习档案持久化 —— V1.1 2.6 长期记忆层 / 4.3 / 第八章。

- SQLite 本地文件；表结构见 schema.sql（字段命名兼容 PostgreSQL 迁移）。
- 证据分级强制标注：A 家长确认 / B 互动观察 / C 未验证推测。
- 不做能力排名、不存原始录音，只存结构化观察。
"""
from __future__ import annotations
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(BASE, "schema.sql")
DEFAULT_DB = os.path.join(BASE, "data", "learning.db")

EVIDENCE = {"A": "家长确认", "B": "互动观察", "C": "未验证推测"}
HELP_LEVELS = ("独立", "少量提示", "较多帮助", "全程协助")


class Store:
    def __init__(self, path: str = DEFAULT_DB):
        # 不自动建目录；构造时主动探一次，路径不可用立刻抛错，
        # 绝不静默伪造一个能写的库（V1.1 13-9）。
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("SELECT 1").fetchone()

    def init_db(self):
        with open(SCHEMA, encoding="utf-8") as f:
            self.db.executescript(f.read())
        self.db.commit()

    # ---------- 学习目标 ----------
    def add_goal(self, domain_id: int, title: str, prerequisites: str = "") -> int:
        cur = self.db.execute(
            "INSERT INTO learning_goals (domain_id, title, prerequisites) VALUES (?,?,?)",
            (domain_id, title, prerequisites))
        self.db.commit()
        return cur.lastrowid

    def get_goal(self, goal_id: int):
        return self.db.execute(
            "SELECT g.*, d.name AS domain FROM learning_goals g "
            "JOIN capability_domains d ON d.id = g.domain_id WHERE g.id = ?",
            (goal_id,)).fetchone()

    def list_goals(self, domain_id=None):
        q = "SELECT * FROM learning_goals ORDER BY id"
        args: tuple = ()
        if domain_id:
            q = "SELECT * FROM learning_goals WHERE domain_id = ? ORDER BY id"
            args = (domain_id,)
        return self.db.execute(q, args).fetchall()

    def set_mastery(self, goal_id: int, state: str):
        from strategy_engine import MASTERY
        assert state in MASTERY, state
        self.db.execute("UPDATE learning_goals SET status = ? WHERE id = ?",
                        (state, goal_id))
        self.db.commit()

    # ---------- 观察记录 ----------
    def add_observation(self, goal_id, evidence_kind, performance,
                        help_level=None, independent=None,
                        transferred=None, note=""):
        assert evidence_kind in EVIDENCE, evidence_kind
        if help_level is not None:
            assert help_level in HELP_LEVELS, help_level
        cur = self.db.execute(
            """INSERT INTO observations
               (goal_id, evidence_kind, performance, help_level,
                independent, transferred, note)
               VALUES (?,?,?,?,?,?,?)""",
            (goal_id, evidence_kind, performance, help_level,
             independent, transferred, note))
        self.db.commit()
        return cur.lastrowid

    def recent_observations(self, goal_id, limit=5):
        return self.db.execute(
            "SELECT * FROM observations WHERE goal_id = ? ORDER BY id DESC LIMIT ?",
            (goal_id, limit)).fetchall()

    def correct_observation(self, obs_id, new_performance, note=""):
        """家长纠正记录（V1.1 2.7 / 第十章-4）：原记录保留，追加纠正说明。"""
        self.db.execute(
            "UPDATE observations SET performance = ?, note = ? WHERE id = ?",
            (new_performance, "家长纠正：" + note if note else "家长纠正",
             obs_id))
        self.db.commit()

    def delete_observation(self, obs_id):
        """家长删除记录（V1.1 2.7 / 第十章-4）。"""
        self.db.execute("DELETE FROM observations WHERE id = ?", (obs_id,))
        self.db.commit()

    # ---------- 资源登记（V1.1 5.1） ----------
    def add_resource(self, name, type, topic="", domain_ids="", goal_ids="",
                     age_fit="", review_status="pending", link="", notes=""):
        cur = self.db.execute(
            """INSERT INTO resources
               (name, type, topic, domain_ids, goal_ids, age_fit,
                review_status, link, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (name, type, topic, domain_ids, goal_ids, age_fit,
             review_status, link, notes))
        self.db.commit()
        return cur.lastrowid

    def approve_resource(self, rid: int):
        self.db.execute("UPDATE resources SET review_status = 'approved' WHERE id = ?",
                        (rid,))
        self.db.commit()

    def usable_resources(self):
        """只有家长审核通过的资源才能进入教学（V1.1 5.4）。"""
        return self.db.execute(
            "SELECT * FROM resources WHERE review_status = 'approved' ORDER BY id"
        ).fetchall()

    def mark_contacted(self, rid: int, needs_followup: int = 0):
        self.db.execute(
            "UPDATE resources SET contacted = 1, needs_followup = ? WHERE id = ?",
            (needs_followup, rid))
        self.db.commit()

    # ---------- 概念映射（V1.1 5.2） ----------
    def map_concept(self, resource_id, topic, concept, goal_id):
        cur = self.db.execute(
            "INSERT INTO concept_map (resource_id, topic, concept, goal_id)"
            " VALUES (?,?,?,?)",
            (resource_id, topic, concept, goal_id))
        self.db.commit()
        return cur.lastrowid

    def concepts_for_goal(self, goal_id):
        return self.db.execute(
            """SELECT c.*, r.name AS resource_name, r.type AS resource_type
               FROM concept_map c JOIN resources r ON r.id = c.resource_id
               WHERE c.goal_id = ?""", (goal_id,)).fetchall()

    # ---------- 间隔复习 ----------
    def schedule_review(self, goal_id, days=2):
        self.db.execute(
            """INSERT INTO review_schedule (goal_id, next_review_at, interval_days)
               VALUES (?, datetime('now', ?), ?)""",
            (goal_id, f"+{days} days", days))
        self.db.commit()

    def due_reviews(self):
        return self.db.execute(
            """SELECT s.*, g.title FROM review_schedule s
               JOIN learning_goals g ON g.id = s.goal_id
               WHERE s.done = 0 AND s.next_review_at <= datetime('now','localtime')
               ORDER BY s.next_review_at""").fetchall()

    def close(self):
        self.db.close()
