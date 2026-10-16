# 儿童 AI 成长伙伴 — 项目资产清单

> 更新：2026-10-16 | 版本管理：本目录为 git 仓库（`git log` 查历史）
> 需求基线：docs/儿童AI成长伙伴-总体建设方案与自主执行任务书-V1.1-定稿-20261016.md（项目负责人：董事长）

## 一、文档（docs/）
| 文件 | 版本 | 说明 |
|---|---|---|
| 总体建设方案与自主执行任务书-V1.1-定稿-20261016.md | V1.1 定稿 | 需求基线，不再扩充理论 |
| 儿童教育宪章-v1.0-20261016.md | v1.0 | 核心文档 |
| 教学策略库-v1.0-20261016.md | v1.0 | 核心文档 |
| 儿童全面发展能力地图-v1.0-20261016.md | v1.0 | 核心文档 |
| 课程与学习状态规范-v1.0-20261016.md | v1.0 | 核心文档 |
| 阶段0-现有环境审计报告-20261016.md | — | 环境审计结论 |

## 二、代码（mvp/）
| 文件 | 说明 | 验证状态 |
|---|---|---|
| strategy_engine.py | 11 种教学策略、掌握状态机 | 15/15 测试通过 |
| learning_store.py | 学习档案（SQLite）、A/B/C 证据分级 | 通过 |
| learning_store_pg.py | 学习档案（PostgreSQL，同签名） | 18/18 测试通过 |
| schema.sql / schema_pg.sql | 表结构 | — |
| migrate_sqlite_to_pg.py | SQLite→PG 迁移 | 数据一致已验 |
| test_scenarios.py / test_pg_store.py | 测试 | 通过 |
| resources.py | 8 种资源类型+审核门禁 | 通过 |
| teach_loop.py | V1.1 第七章教学闭环 | 完整闭环已跑通 |
| demo_numberblocks.py | Numberblocks 六步演示 | 跑通 |
| parent_view.py | 家长视图（pi-agent 真实交付） | 亲验通过 |
| llm_client.py | 可插拔 LLM（sub2api/OpenAI 兼容） | 真实回复通过 |
| xiaozhi_glue.py | 设备端到端胶水（语音→ASR→闭环→TTS） | 模拟验证通过 |
| ASR-接口文档.md | sherpa-onnx 接口 | 中文 19/19 字通过 |
| backup.sh | 备份/恢复 | 备份+恢复亲测通过 |
| 英文水果活动方案-20261016.md | 首个英文活动方案 | 已生成 |

## 三、版本管理规则
1. 代码改动先 `git commit`，再部署运行；`git log --oneline` 查历史
2. 文档大版本用文件名版本号（v1.0→v2.0），小改直接 commit
3. `data/*.db` 不进 git（运行时数据，走 backup.sh）
4. 需求基线（V1.1 定稿）锁定：只按真实运行问题迭代
