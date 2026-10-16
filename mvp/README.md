# 儿童 AI 成长伙伴 · MVP（阶段 1 软件闭环）

依据《儿童 AI 成长伙伴：总体建设方案与自主执行任务书 V1.1》第二章（总体架构）与第七章（统一教学闭环）。

## 跑起来

```bash
cd mvp
python3 demo_numberblocks.py   # 一次完整 Numberblocks 融合教学闭环演示
python3 test_scenarios.py      # V1.1 ch13 测试场景自测（15 项）
```

## 文件

| 文件 | 对应 V1.1 | 说明 |
|---|---|---|
| `schema.sql` | 2.6 / 4.3 / 5.1 / ch8 | SQLite 表结构（字段命名兼容 PG 迁移），含十领域种子数据 |
| `strategy_engine.py` | 2.3 / 4.2 / 4.3 | 规则引擎：11 种教学策略 + 掌握状态机，不依赖特定大模型 |
| `learning_store.py` | 2.6 / 4.3 / ch8 | 学习档案 CRUD；证据分级 A/B/C 强制标注；家长纠正/删除 |
| `resources.py` | ch5 | 8 种资源类型 + 审核门禁（未审核不得进入教学） |
| `teach_loop.py` | ch7 | 统一教学闭环 CLI：9 步流程 + 结束 5 问复盘 |
| `demo_numberblocks.py` | 6.3 | Numberblocks 六步融合流程演示 |
| `test_scenarios.py` | ch13 | 15 项自测 |
| `TEST-REPORT.md` | ch13 | 测试报告 |

## 设计要点（V1.1 铁律落地）

- ASR 错误永不记为知识错误；状态机不因非知识信号升降。
- 一次答对 / 看完视频永不直接判"基本掌握"；迁移成功需累计 2 次。
- 未审核资源进不了教学；多资源映射到同一目标，不建多份记录。
- 孩子拒绝/想停 → 安抚或总结结束，不为活跃度硬拖。
- DB 不可用时构造即抛错，不伪造记录。

## 待办（按 V1.1 阶段）

- [ ] 四份核心文档进 `files/`：教育宪章 / 教学策略库 / 能力地图 / 课程与学习状态规范
- [ ] LLM 对话接线（pluggable 接口；MVP 先跑通规则闭环）
- [ ] 部署到 arm-agent：复用容器化 PostgreSQL（schema 字段已兼容）
- [ ] ch13 中 △ 项部署联调实测（断网降级 / 访问控制 / 备份回滚）
