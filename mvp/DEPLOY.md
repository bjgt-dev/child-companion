# 部署说明

## 本地运行（已验证 2026-10-16）

```bash
cd mvp
python3 demo_numberblocks.py   # 教学闭环演示
python3 test_scenarios.py      # 15 项自测
```

- 纯标准库，无第三方依赖（python3 即可）。
- 数据落 `mvp/data/*.db`（SQLite）；备份 = 直接拷贝 data/ 目录。

## 部署到 arm-agent（已验证 2026-10-16）

```bash
scp -r mvp arm-agent:/home/ubuntu/child-companion/mvp/
ssh arm-agent 'cd /home/ubuntu/child-companion/mvp && python3 demo_numberblocks.py && python3 test_scenarios.py'
```

## PostgreSQL 迁移（阶段 1 后续）

- `schema.sql` 字段命名已按 PG 习惯设计；迁移时调整：
  - `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`
  - `datetime('now','localtime')` → `now()`
  - `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING`
- 目标库：复用宿主机现有容器化 PG（compose-postgres / ops-pg 二选一），不新建实例。
- 迁移前 `pg_dump` 备份；回滚 = 恢复 dump（V1.1 13-17）。

## 安全约束（V1.1 第十章）

- `data/` 目录权限 700；DB 文件 600。
- 不存原始录音；学习档案仅结构化观察。
- 家长纠正/删除接口已实现（`Store.correct_observation` / `delete_observation`）。
