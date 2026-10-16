"""学习档案持久化 —— PostgreSQL 后端（与 learning_store.py 的 Store 接口同签名）。

- 表结构见 schema_pg.sql（由 schema.sql 转换：AUTOINCREMENT→IDENTITY，
  datetime('now','localtime')→to_char(now(),...)，INSERT OR IGNORE→ON CONFLICT）。
- DSN 优先级：显式 dsn 参数 > 环境变量 CHILD_COMPANION_PG_DSN
  > /home/ubuntu/.pg_child_companion_dsn（600 权限，密码永不进代码/日志）。
- 构造时立即连接并探一次 SELECT 1，PG 不可用立刻抛错，
  不静默伪造（同 SQLite 版 V1.1 13-9 约定）。
- 后端切换：get_store() 读环境变量 CHILD_COMPANION_BACKEND
  （sqlite 默认 / pg），调用方（teach_loop.Session 等）无需改代码，
  Session(store, goal_id) 照常接收任意后端实例。
"""
from __future__ import annotations
import os

import psycopg
from psycopg.rows import dict_row

BASE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PG = os.path.join(BASE, "schema_pg.sql")

EVIDENCE = {"A": "家长确认", "B": "互动观察", "C": "未验证推测"}
HELP_LEVELS = ("独立", "少量提示", "较多帮助", "全程协助")

DSN_FILE = os.path.join(os.path.expanduser("~"), ".pg_child_companion_dsn")


def resolve_dsn(dsn: str | None = None) -> str:
    """解析 PG 连接串：参数 > 环境变量 > 600 权限凭据文件。"""
    if dsn:
        return dsn
    env_dsn = os.environ.get("CHILD_COMPANION_PG_DSN")
    if env_dsn:
        return env_dsn
    if os.path.exists(DSN_FILE):
        with open(DSN_FILE, encoding="utf-8") as f:
            return f.read().strip()
    raise RuntimeError(
        "未找到 PG DSN：请传 dsn 参数、设环境变量 CHILD_COMPANION_PG_DSN，"
        f"或在 {DSN_FILE}（600 权限）中存放连接串")


class PGStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = resolve_dsn(dsn)
        # 主动探一次，不可用立刻抛错（V1.1 13-9）
        self.conn = psycopg.connect(self.dsn, row_factory=dict_row)
        self.conn.execute("SELECT 1").fetchone()

    def init_db(self):
        with open(SCHEMA_PG, encoding="utf-8") as f:
            self.conn.execute(f.read())
        self.conn.commit()

    # ---------- 学习目标 ----------
    def add_goal(self, domain_id: int, title: str, prerequisites: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO learning_goals (domain_id, title, prerequisites)"
            " VALUES (%s,%s,%s) RETURNING id",
            (domain_id, title, prerequisites))
        self.conn.commit()
        return cur.fetchone()["id"]

    def get_goal(self, goal_id: int):
        return self.conn.execute(
            "SELECT g.*, d.name AS domain FROM learning_goals g "
            "JOIN capability_domains d ON d.id = g.domain_id WHERE g.id = %s",
            (goal_id,)).fetchone()

    def list_goals(self, domain_id=None):
        q = "SELECT * FROM learning_goals ORDER BY id"
        args: tuple = ()
        if domain_id:
            q = "SELECT * FROM learning_goals WHERE domain_id = %s ORDER BY id"
            args = (domain_id,)
        return self.conn.execute(q, args).fetchall()

    def set_mastery(self, goal_id: int, state: str):
        from strategy_engine import MASTERY
        assert state in MASTERY, state
        self.conn.execute("UPDATE learning_goals SET status = %s WHERE id = %s",
                          (state, goal_id))
        self.conn.commit()

    # ---------- 观察记录 ----------
    def add_observation(self, goal_id, evidence_kind, performance,
                        help_level=None, independent=None,
                        transferred=None, note=""):
        assert evidence_kind in EVIDENCE, evidence_kind
        if help_level is not None:
            assert help_level in HELP_LEVELS, help_level
        cur = self.conn.execute(
            """INSERT INTO observations
               (goal_id, evidence_kind, performance, help_level,
                independent, transferred, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (goal_id, evidence_kind, performance, help_level,
             independent, transferred, note))
        self.conn.commit()
        return cur.fetchone()["id"]

    def recent_observations(self, goal_id, limit=5):
        return self.conn.execute(
            "SELECT * FROM observations WHERE goal_id = %s"
            " ORDER BY id DESC LIMIT %s",
            (goal_id, limit)).fetchall()

    def correct_observation(self, obs_id, new_performance, note=""):
        """家长纠正记录（V1.1 2.7 / 第十章-4）：原记录保留，追加纠正说明。"""
        self.conn.execute(
            "UPDATE observations SET performance = %s, note = %s WHERE id = %s",
            (new_performance, "家长纠正：" + note if note else "家长纠正",
             obs_id))
        self.conn.commit()

    def delete_observation(self, obs_id):
        """家长删除记录（V1.1 2.7 / 第十章-4）。"""
        self.conn.execute("DELETE FROM observations WHERE id = %s", (obs_id,))
        self.conn.commit()

    # ---------- 资源登记（V1.1 5.1） ----------
    def add_resource(self, name, type, topic="", domain_ids="", goal_ids="",
                     age_fit="", review_status="pending", link="", notes=""):
        cur = self.conn.execute(
            """INSERT INTO resources
               (name, type, topic, domain_ids, goal_ids, age_fit,
                review_status, link, notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (name, type, topic, domain_ids, goal_ids, age_fit,
             review_status, link, notes))
        self.conn.commit()
        return cur.fetchone()["id"]

    def approve_resource(self, rid: int):
        self.conn.execute(
            "UPDATE resources SET review_status = 'approved' WHERE id = %s",
            (rid,))
        self.conn.commit()

    def usable_resources(self):
        """只有家长审核通过的资源才能进入教学（V1.1 5.4）。"""
        return self.conn.execute(
            "SELECT * FROM resources WHERE review_status = 'approved' ORDER BY id"
        ).fetchall()

    def mark_contacted(self, rid: int, needs_followup: int = 0):
        self.conn.execute(
            "UPDATE resources SET contacted = 1, needs_followup = %s WHERE id = %s",
            (needs_followup, rid))
        self.conn.commit()

    # ---------- 概念映射（V1.1 5.2） ----------
    def map_concept(self, resource_id, topic, concept, goal_id):
        cur = self.conn.execute(
            "INSERT INTO concept_map (resource_id, topic, concept, goal_id)"
            " VALUES (%s,%s,%s,%s) RETURNING id",
            (resource_id, topic, concept, goal_id))
        self.conn.commit()
        return cur.fetchone()["id"]

    def concepts_for_goal(self, goal_id):
        return self.conn.execute(
            """SELECT c.*, r.name AS resource_name, r.type AS resource_type
               FROM concept_map c JOIN resources r ON r.id = c.resource_id
               WHERE c.goal_id = %s""", (goal_id,)).fetchall()

    # ---------- 间隔复习 ----------
    def schedule_review(self, goal_id, days=2):
        self.conn.execute(
            """INSERT INTO review_schedule (goal_id, next_review_at, interval_days)
               VALUES (%s, to_char(now() + make_interval(days => %s),
                      'YYYY-MM-DD HH24:MI:SS'), %s)""",
            (goal_id, days, days))
        self.conn.commit()

    def due_reviews(self):
        return self.conn.execute(
            """SELECT s.*, g.title FROM review_schedule s
               JOIN learning_goals g ON g.id = s.goal_id
               WHERE s.done = 0
                 AND s.next_review_at <= to_char(now(), 'YYYY-MM-DD HH24:MI:SS')
               ORDER BY s.next_review_at""").fetchall()

    def close(self):
        self.conn.close()


def get_store(backend: str | None = None, path: str | None = None,
              dsn: str | None = None):
    """后端工厂：teach_loop 等调用方的统一入口。

    backend 不传则读环境变量 CHILD_COMPANION_BACKEND（默认 "sqlite"，
    不破坏现有行为）。"pg" 返回 PGStore，"sqlite" 返回 learning_store.Store。
    """
    b = (backend or os.environ.get("CHILD_COMPANION_BACKEND", "sqlite")).lower()
    if b == "pg":
        return PGStore(dsn)
    if b == "sqlite":
        from learning_store import Store, DEFAULT_DB
        return Store(path or DEFAULT_DB)
    raise ValueError("未知后端：%s（应为 sqlite 或 pg）" % backend)
