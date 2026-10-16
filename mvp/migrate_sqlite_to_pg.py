"""SQLite → PostgreSQL 全量迁移：mvp/data/*.db → child_companion 库。

- 保留原 id（列名逐表对齐，INSERT ... ON CONFLICT (id) DO NOTHING），
  幂等：重复运行不会造出重复行。
- 迁移后把各表 IDENTITY 序列拨到 max(id)，保证后续 add_* 的 RETURNING id
  不撞车。
- 凭据：同 learning_store_pg 的 resolve_dsn（参数/env/600 文件），
  密码绝不打印、不进日志。
- 回滚：PG 迁移不删除 SQLite 源文件；回滚只需把调用方切回
  CHILD_COMPANION_BACKEND=sqlite（默认）即可。

用法：
    python3 migrate_sqlite_to_pg.py [--db data/demo.db] [--dsn ...]
默认把 data/ 下所有含 learning_goals/observations 等表的 *.db 都迁一遍。
"""
from __future__ import annotations
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psycopg
from psycopg.rows import dict_row

from learning_store_pg import resolve_dsn

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")

TABLES = ["capability_domains", "learning_goals", "resources",
          "concept_map", "observations", "review_schedule"]


def table_columns(sdb: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in sdb.execute(f"PRAGMA table_info({table})")]


def migrate_one(sqlite_path: str, dsn: str) -> dict[str, int]:
    sdb = sqlite3.connect(sqlite_path)
    sdb.row_factory = sqlite3.Row
    present = {r[0] for r in sdb.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    pg = psycopg.connect(dsn, row_factory=dict_row)
    moved: dict[str, int] = {}
    for table in TABLES:
        if table not in present:
            continue
        cols = table_columns(sdb, table)
        collist = ", ".join(cols)
        ph = ", ".join(["%s"] * len(cols))
        n = 0
        for row in sdb.execute(f"SELECT {collist} FROM {table} ORDER BY id"):
            vals = [row[c] for c in cols]
            pg.execute(
                f"INSERT INTO {table} ({collist}) VALUES ({ph})"
                " ON CONFLICT (id) DO NOTHING",
                vals)
            n += 1
        pg.commit()
        # 序列拨到 max(id)，后续自增不撞车
        pg.execute(
            "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
            "COALESCE((SELECT max(id) FROM {}), 1))".format(table),
            (table,))
        pg.commit()
        moved[table] = n
    pg.close()
    sdb.close()
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="只迁移这一个 SQLite 文件（默认扫描 data/*.db）")
    ap.add_argument("--dsn", help="PG DSN（默认走 resolve_dsn）")
    args = ap.parse_args()

    dsn = resolve_dsn(args.dsn)
    if args.db:
        db_files = [args.db]
    else:
        db_files = sorted(
            os.path.join(DATA_DIR, f) for f in os.listdir(DATA_DIR)
            if f.endswith(".db"))
    total: dict[str, int] = {}
    for dbf in db_files:
        sdb = sqlite3.connect(dbf)
        present = {r[0] for r in sdb.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        sdb.close()
        if not any(t in present for t in TABLES):
            print("跳过 %s（无业务表）" % dbf)
            continue
        moved = migrate_one(dbf, dsn)
        for t, n in moved.items():
            total[t] = total.get(t, 0) + n
        print("已迁移 %s：%s" % (os.path.basename(dbf),
              " / ".join("%s=%d" % (t, n) for t, n in moved.items())))
    print("合计：", " / ".join("%s=%d" % (t, n) for t, n in sorted(total.items())))
    # 不打印 dsn（可能含密码）


if __name__ == "__main__":
    main()
