"""家长查看学习记录的 CLI（V1.1 阶段 1 验收项 + 第十章 家长监督）。

只读工具：打开数据库时全部使用只读/只查操作，绝不写入或修改数据库。

用法：
    python3 parent_view.py            # 列出所有学习目标 + 最近 3 条观察 + 待复习项
    python3 parent_view.py --goal 1   # 只看 id=1 的目标
    python3 parent_view.py --db data/demo.db   # 指定数据库文件（默认 data/learning.db）
"""
from __future__ import annotations

import argparse
import os
import sqlite3

from learning_store import DEFAULT_DB, Store, EVIDENCE
from strategy_engine import MASTERY_CN

BASE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE_TAG = {k: f"[{k}] {v}" for k, v in EVIDENCE.items()}


def _open_readonly(path: str) -> sqlite3.Connection:
    """以只读 URI 方式打开 SQLite（mode=ro），物理上保证本工具不写入数据库。"""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("SELECT 1").fetchone()
    return conn


def _fmt_obs(row) -> str:
    lines = [f"      [{row['id']}] {row['observed_at']}  "
             f"{EVIDENCE_TAG.get(row['evidence_kind'], row['evidence_kind'])}  "
             f"{row['performance']}"]
    extra = []
    if row["help_level"]:
        extra.append(f"帮助：{row['help_level']}")
    if row["independent"] is not None:
        extra.append("独立完成" if row["independent"] else "非独立")
    if row["transferred"]:
        extra.append("已迁移验证")
    if row["note"]:
        extra.append(f"备注：{row['note']}")
    if extra:
        lines.append("        " + " / ".join(extra))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="家长查看学习记录（只读）")
    ap.add_argument("--goal", type=int, metavar="ID",
                    help="只查看指定 id 的学习目标")
    ap.add_argument("--db", default=DEFAULT_DB,
                    help=f"数据库路径（默认 {DEFAULT_DB}）")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"数据库不存在：{args.db}", flush=True)
        return 1

    conn = _open_readonly(args.db)
    store = Store.__new__(Store)          # 绕过 __init__，复用只读连接
    store.db = conn

    goals = [g for g in store.list_goals()]
    if args.goal is not None:
        goals = [g for g in goals if g["id"] == args.goal]

    print("=" * 60)
    print("家长监督视图 · 学习记录（只读）")
    print("=" * 60)

    if not goals:
        print("(没有学习记录"
              + (f"：未找到 id={args.goal} 的目标" if args.goal is not None else "）"))
    else:
        for g in goals:
            domain = store.get_goal(g["id"])["domain"]
            mastery = MASTERY_CN.get(g["status"], g["status"])
            print(f"\n#{g['id']} [{domain}] {g['title']}   掌握状态：{mastery}")
            obs = store.recent_observations(g["id"], limit=3)
            if obs:
                print("  最近观察记录：")
                for o in obs:
                    print(_fmt_obs(o))
            else:
                print("  最近观察记录：（暂无）")

    print("\n" + "-" * 60)
    print("待复习项（due_reviews）：")
    due = [r for r in store.due_reviews()]
    if args.goal is not None:
        due = [r for r in due if r["goal_id"] == args.goal]
    if due:
        for r in due:
            print(f"  {r['title']}（目标 {r['goal_id']}，"
                  f"计划 {r['next_review_at']}，间隔 {r['interval_days']} 天）")
    else:
        print("  （暂无）")
    print("-" * 60)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
