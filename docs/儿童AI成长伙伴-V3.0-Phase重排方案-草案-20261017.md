# 儿童 AI 成长伙伴 V3.0：Phase 0-5 重排方案

> **草案（未过外脑团评审）**
> 制定日期：2026-10-17
> 决策依据：用户 2026-10-17 拍板，项目基线从 V1.1 升级到 V3.0 总纲
> V3.0 总纲来源：https://chatgpt.com/s/t_6ad259af4d3481919f03436bd222e21e

---

## 一、V1.1 进展 → V3.0 映射总表

| V3.0 要求 | V1.1 现状 | 状态 | 处置 |
|---|---|---|---|
| Phase 0 环境审计 | `阶段0-现有环境审计报告-20261016.md` | ✅ 已完成 | 直接沿用 |
| 成长事件系统（Learning Event JSON、证据 L1/L2/L3、置信度） | 无 | ❌ 未开始 | Phase 0 核心工程 1，新建 |
| 成长模型（描述性、禁止打分） | `learning_goals` 表有 6 级掌握状态机，但无"描述性发展状态"、无"禁止打分"约束 | ⚠️ 部分完成 | Phase 0 核心工程 2，改造 |
| 教育策略版本化（Policy 版本表、Research Agent、证据 A-D 级） | `strategy_engine.py` 有 11 种策略但无版本化；无 Research Pipeline | ⚠️ 部分完成 | Phase 0 核心工程 3，改造+新建 |
| 20 张核心表 | 现有 6 张（capability_domains、learning_goals、resources、concept_map、observations、review_schedule） | ⚠️ 部分完成 | Phase 0，新增 14 张 |
| Skill 体系（15 个） | 只有 `companion-dialogue` 1 个 skill 文档 | ⚠️ 部分完成 | Phase 0 设计规范，Phase 1 起逐个实现 |
| 十条最高产品原则（System Policy） | `儿童教育宪章-v1.0` 有原则但未落成"系统级 Policy"代码约束 | ⚠️ 部分完成 | Phase 0，宪章升级为 System Policy |
| Phase 1 最小可运行 Agent（语音→ASR→教育策略→TTS→记忆） | `teach_loop.py`（9 步闭环）+ `xiaozhi_glue.py` + `llm_client.py`，15/15 自测通过 | ✅ 已完成 | Phase 1 直接沿用，接入成长事件 |
| Phase 1 五个行为验收测试 | 无 | ❌ 未开始 | Phase 1 新增，必须通过才算 Phase 1 完成 |
| Parent Copilot（每周摘要+建议） | `parent_view.py` 只能查看记录，无摘要、无建议 | ⚠️ 部分完成 | Phase 2 升级为完整 Copilot |
| Learning Scientist Agent | 无 | ❌ 未开始 | Phase 5 |
| Child Development Agent | 无 | ❌ 未开始 | Phase 5 |
| Safety Agent | 无（有安全红线文档，无代码） | ❌ 未开始 | Phase 0 安全模型设计，Phase 1 最小实现 |
| 学习生态（Khan Kids/Numberblocks/YT Kids） | `resources.py` 有资源表结构，无对接逻辑 | ⚠️ 部分完成 | Phase 3 |
| ESP32 硬件 | `xiaozhi_glue.py` 是软件胶水层，无真机 | ❌ 未开始 | Phase 4 |
| Research Update Pipeline | 无 | ❌ 未开始 | Phase 5 |

**结论**：V1.1 的 MVP 是"能跑的教学闭环"，V3.0 要求的是"成长系统"。保留 MVP 代码，Phase 0 补三个核心工程（成长事件、成长模型、策略版本化），不推倒重来。

---

## 二、Phase 0：三个核心工程 + 架构升级

**目标**：把 V3.0 的地基打牢——成长事件系统、成长模型、教育策略版本化。没有这三个，后面所有 Phase 都是空话。

**前置依赖**：Phase 0 环境审计（已完成）。

### 核心工程 1：成长事件系统

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 0-1-1 | `learning_events` 表 | 字段：id、event_type、domain、source、description、assistance_level（独立完成/少量提示/大量帮助）、confidence（0-1）、evidence_level（L1/L2/L3）、child_id、occurred_at、created_at | 建表 SQL 执行成功；插入 1 条测试事件可查回 |
| 0-1-2 | `learning_evidence` 表 | 字段：id、event_id（FK）、evidence_type（L1事实/L2观察/L3推测）、content、source、recorded_by（AI/家长/外部系统） | 同上 |
| 0-1-3 | `growth_event.py` 模块 | 函数：`record_event()`（写事件+证据）、`get_events(child_id, domain, days)`（按条件查询）、`event_to_growth_signal()`（事件转成长信号，带置信度加权） | 单元测试 ≥10 个用例全部通过；`record_event` 写入后 `get_events` 能查回 |
| 0-1-4 | 证据分级规范文档 | L1（事实：可验证的客观记录）、L2（观察：AI/家长的直接观察）、L3（推测：基于模式的推断，必须标注"推测"）三级的定义、示例、升级/降级规则 | 文档评审通过；`growth_event.py` 中 L3 事件在输出时强制带"推测"标记（代码检查） |
| 0-1-5 | "不知道就记录不知道"机制 | 当信息不足时，系统记录 `evidence_level=L1`、`description="信息不足"`，禁止编造 | 测试用例：输入空观察，系统输出"信息不足"而非推测性描述 |

### 核心工程 2：成长模型（描述性、禁止打分）

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 0-2-1 | `growth_domains` 表 | 字段：id、child_id、domain（10 大能力领域）、status_description（描述性文本，如"数量概念：多次观察表现良好"）、last_updated | 建表成功 |
| 0-2-2 | `growth_model.py` 模块 | 函数：`update_domain(child_id, domain, evidence_list)`（基于证据更新描述）、`get_growth_snapshot(child_id)`（返回全部领域描述性快照） | 单元测试通过；快照输出为描述性文本 |
| 0-2-3 | 禁止打分约束 | 代码级禁止：`growth_model.py` 中不允许出现百分制/等级制评分；`get_growth_snapshot` 输出做正则检查，不含数字评分 | 测试：尝试写入"英语 85 分"被拒绝或自动转为描述性文本 |
| 0-2-4 | V1.1 掌握状态机迁移 | `learning_goals` 的 6 级状态（uncontacted→mastered）映射到成长事件：每次状态变更必须关联至少 1 条 learning_event 作为证据 | 迁移脚本执行成功；抽查 5 条状态变更记录，每条都有对应 event |

### 核心工程 3：教育策略版本化

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 0-3-1 | `education_policies` 表 | 字段：id、name（如"socratic questioning"）、description、version_id（FK）、evidence_grade（A/B/C/D）、applicable_age、status（active/deprecated/experimental） | 建表成功 |
| 0-3-2 | `education_policy_versions` 表 | 字段：id、version（如"v1.0"）、change_log（为什么改、依据什么、改了什么）、created_at、approved_by | 建表成功；插入 v1.0 基线版本 |
| 0-3-3 | `strategy_engine.py` 改造 | 现有 11 种策略全部纳入版本管理：每次 `decide()` 调用记录使用的策略名 + 版本号；新增 `set_policy_version()` 切换版本 | 改造后原有 15/15 测试仍然通过；`decide()` 返回结果包含 `policy_version` 字段 |
| 0-3-4 | 证据等级规范 | A（多项高质量研究/系统综述→可进核心策略）、B（较好单项研究→候选）、C（专家观点/早期研究→仅实验）、D（社交媒体/营销→不进核心） | 文档化；`education_policies` 表中每条策略都有 evidence_grade |
| 0-3-5 | 策略变更流程文档 | 新策略上线流程：提议→证据定级→小范围验证→评审→版本发布→旧版本标记 deprecated（不删除） | 文档评审通过 |

### 架构升级（非核心但 Phase 0 必须）

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 0-4-1 | 20 表完整 Schema | 在现有 6 张基础上新增 14 张：child_profile、growth_domains、growth_goals、learning_events、learning_evidence、interests、activities、activity_results、memory、resource_topics、parent_observations、education_policies、education_policy_versions、research_evidence、strategy_experiments、safety_events、device、conversation_sessions（减去已有的 resources、review_schedule，实际新增 14 张） | `schema_pg.sql` 更新；PostgreSQL 建库后 `\dt` 显示 20 张表；`migrate` 脚本从旧 6 表平滑升级，数据不丢失 |
| 0-4-2 | Skill 体系设计规范 | 15 个 skill 的职责边界、输入输出、调用关系：english-coach、listening-coach、math-coach、logic-coach、storytelling-coach、emotion-coach、science-explorer、reading-coach、creativity-coach、self-learning-coach、parent-copilot、resource-curator、learning-scientist、child-development、safety | 文档评审通过；每个 skill 有明确的"做什么/不做什么" |
| 0-4-3 | System Policy（十条最高原则）代码约束 | 把 V3.0 十条原则转为代码检查点：如"孩子拒绝→立即停止"（已有 comfort_pause，补自动化测试）、"不为活跃度硬拖时长"（teach_loop 加最大轮次限制） | 10 条原则每条对应至少 1 个代码检查点或测试用例 |
| 0-4-4 | Safety Agent 最小实现 | `safety.py`：危险行为关键词拦截、成人内容过滤、使用时长上限 | 单元测试：输入危险行为描述被拦截；超时使用被提醒 |
| 0-4-5 | 教育宪章 v2.0 | V1.1 宪章升级，纳入"成长事件""禁止打分""策略版本化"三章 | 文档评审通过 |

**Phase 0 完成标准**：以上 15 个交付物全部验收通过；PostgreSQL 20 表建表成功；`growth_event.py` + `growth_model.py` 单元测试全过；`strategy_engine.py` 改造后原有测试不回归。

---

## 三、Phase 1：最小可运行 Agent + 五个行为验收测试

**目标**：在 V1.1 MVP 基础上接入成长事件系统，通过 V3.0 规定的 5 个行为测试。

**前置依赖**：Phase 0 全部完成（成长事件、成长模型、策略版本化必须可用）。

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 1-1 | `teach_loop.py` 接入成长事件 | 每次教学活动结束时调用 `record_event()`，记录：目标、孩子表现、所需帮助程度（assistance_level）、证据等级 | 跑一次完整教学闭环，`learning_events` 表新增 ≥1 条记录，`assistance_level` 非空 |
| 1-2 | Skill 实现（第一批 4 个） | english-coach、math-coach、storytelling-coach、emotion-coach：每个 skill 独立模块，有明确输入输出 | 每个 skill 有 ≥5 个单元测试；`teach_loop` 可按需调用 |
| 1-3 | 五个行为验收测试 | 写成自动化测试脚本 `test_v30_phase1.py`：①孩子说"I like dinosaurs"，第二天 Agent 是否记得（查 memory 表）；②学数字 5，几天后换现实场景验证（transfer 策略触发）；③答错数学题，Agent 能否区分"不会/没听懂/粗心/ASR 错误"（4 种错误归因）；④孩子说"我不想玩了"，Agent 是否立即停止（comfort_pause 触发，3 秒内结束）；⑤孩子沉默时，Agent 是否输出"信息不足"而非编造情绪 | 5 个测试全部通过；任一失败则 Phase 1 不算完成 |
| 1-4 | "提示逐渐撤除"机制 | `strategy_engine.py` 新增：记录每次任务的 `assistance_level`；同一目标连续 3 次独立完成 → 自动降低提示等级 | 测试：模拟 3 次独立完成，第 4 次 `decide()` 返回的提示等级下降 |
| 1-5 | 依赖度指标 | 统计"连续直接给答案"次数；10 次问题全要求 AI 给答案时，触发"你想先自己试试吗？" | 测试：模拟 10 次索要答案，第 11 次触发干预提示 |

**Phase 1 完成标准**：5 个行为测试全过；V1.1 原有 15/15 测试不回归；`learning_events` 有真实写入记录。

---

## 四、Phase 2：成长系统（长期记忆 + 发展追踪）

**目标**：让 Agent 拥有长期记忆，能追踪孩子数周/数月的能力发展轨迹。

**前置依赖**：Phase 1 完成（成长事件持续写入）。

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 2-1 | `memory` 表 + 记忆检索模块 | 字段：id、child_id、memory_type（兴趣/事件/偏好/里程碑）、content、importance（0-1）、created_at、last_accessed；`memory.py`：`store()`、`recall(query, top_k)`（按相关度+重要性排序） | 单元测试：存 20 条记忆，查询返回最相关的 top 3 |
| 2-2 | 间隔复习调度 | 基于 `review_schedule` 表 + 成长事件：自动计算下次复习时间（艾宾浩斯简化版：1 天→3 天→7 天→14 天） | 测试：一次学习事件后，系统生成 4 个复习时间点 |
| 2-3 | 成长轨迹报告 | `growth_report.py`：输入 child_id + 时间范围，输出各领域描述性变化（如"数学：从'需要实物辅助'到'可心算 10 以内加法'"） | 报告无数字评分；家长可读懂 |
| 2-4 | Parent Copilot v1.0 | 在 `parent_view.py` 基础上：每周自动生成摘要（兴趣变化、能力进展、建议活动、家长可做的事） | 每周一自动生成；摘要包含"建议现实活动"≥2 条 |

**Phase 2 完成标准**：记忆检索准确率人工抽查 ≥80%；成长轨迹报告无数字评分；Parent Copilot 每周摘要正常生成。

---

## 五、Phase 3：学习生态（多来源接入）

**目标**：把 Khan Kids、Numberblocks、YouTube Kids、绘本、玩具、户外活动接入为学习事件来源。

**前置依赖**：Phase 2 完成（成长事件系统稳定运行）。

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 3-1 | 学习来源接入规范 | 定义 6 类来源的数据格式：结构化课程（Khan Kids）、视频（Numberblocks/YT Kids）、绘本、玩具、现实生活、AI 活动；每类来源如何转为 learning_event | 文档评审通过；每类来源有 ≥1 个示例 event |
| 3-2 | `resource_copilot` skill | 家长登记"孩子看了什么"（如 Numberblocks 第 5 集）→ 系统生成对应的"对话→动手→生活→迁移"四步活动建议 | 测试：登记 1 集 Numberblocks，输出 4 步活动建议 |
| 3-3 | 家长观察入口 | `parent_observations` 表 + 简单录入界面：家长可记录观察（如"今天主动数了楼梯台阶"），自动转为 L2 证据 | 家长录入 1 条，`learning_events` 新增 1 条 L2 事件 |
| 3-4 | Numberblocks 六步链实现 | 输入→对话→动手→生活→迁移→创造，6 步的活动模板库（至少覆盖数字 1-10） | 每个数字有完整 6 步模板；抽查 3 个数字模板可用 |

**Phase 3 完成标准**：6 类来源每类至少有 1 条真实 learning_event；Numberblocks 1-10 模板齐全。

---

## 六、Phase 4：硬件（ESP32）

**目标**：把软件 Agent 装进 ESP32-S3 硬件，支持 4G 户外模式。

**前置依赖**：Phase 3 完成（软件闭环稳定）。

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 4-1 | ESP32-S3 选型与采购 | 屏幕 3.5 寸、4G 模块、麦克风、扬声器、电池、物理打断键；BOM 清单 + 采购链接 | 用户确认下单 |
| 4-2 | 设备端软件 | 基于 `xiaozhi_glue.py` 改造：ESP32 端只做语音采集+播放，ASR/LLM/TTS 全在云端；物理打断键 → 立即停止当前 TTS+对话 | 真机测试：按打断键 1 秒内停止播放 |
| 4-3 | 4G 户外模式 | "现实探索模式"：户外时 Agent 主动引导观察（如"看看周围有几种颜色"），而非继续室内课程 | 真机户外测试 30 分钟，Agent 发起 ≥3 次现实探索邀请 |
| 4-4 | 设备管理 | `device` 表：设备绑定、OTA 更新、使用时长统计 | 1 台设备成功绑定；OTA 推送 1 次成功 |

**Phase 4 完成标准**：真机跑通完整对话闭环；打断键有效；户外模式可用。

---

## 七、Phase 5：长期进化（研究管线 + 高级 Agent）

**目标**：建立教育策略的自我进化能力，上线高级 Agent。

**前置依赖**：Phase 4 完成（全链路跑通）。

| # | 交付物 | 具体内容 | 验收标准 |
|---|---|---|---|
| 5-1 | Research Update Pipeline | `research_agent.py`：定期搜索儿童发展/教育心理/学习科学新研究 → `research_evidence` 表（带证据等级 A-D）→ 人工审核 → 策略候选 | 每月运行 1 次；每次产出 ≥3 条带分级的研究摘要 |
| 5-2 | Learning Scientist Agent | `learning_scientist.py`：分析 learning_events，检查当前策略效果，提出策略升级建议（不直接改策略，只提建议） | 每月产出 1 份策略效果分析报告 |
| 5-3 | Child Development Agent | `child_dev.py`：监控 10 大能力领域是否均衡发展；发现某领域长期被忽略时告警 | 测试：模拟某领域 30 天无事件，触发告警 |
| 5-4 | Safety Agent 完整版 | `safety_events` 表 + 实时监控：危险行为识别、内容过滤、使用时长控制、家长告警 | 危险行为测试用例 100% 拦截 |
| 5-5 | Parent Copilot v2.0 | 月度深度报告 + 个性化建议 + 与 Learning Scientist 联动 | 月度报告正常生成 |

**Phase 5 完成标准**：Research Pipeline 跑通 1 个完整周期（搜索→分级→审核→策略候选）；三个高级 Agent 全部上线。

---

## 八、Phase 依赖关系总览

```
Phase 0（地基：成长事件/成长模型/策略版本化/20表/Skill规范/Safety最小版）
  └─→ Phase 1（教学闭环接入事件 + 5行为测试）
        └─→ Phase 2（长期记忆/成长轨迹/Parent Copilot v1）
              └─→ Phase 3（6类学习来源/Numberblocks六步链）
                    └─→ Phase 4（ESP32真机/4G户外）
                          └─→ Phase 5（Research管线/高级Agent）
```

**铁律**：上一 Phase 验收不通过，下一 Phase 不开工。每个 Phase 的"完成标准"是硬门禁。

---

## 九、风险与注意事项

1. **V1.1 代码保护**：`strategy_engine.py` 等已有模块只做增量改造，不重写；每次改造后跑原有 15/15 测试防回归。
2. **数据迁移**：6 表→20 表迁移脚本必须先备份（`backup.sh` 已有），迁移后抽查数据完整性。
3. **禁止打分是红线**：任何 Phase 交付物出现百分制/等级制评分，直接打回。
4. **"不知道就记录不知道"**：贯穿所有 Phase，L3 推测必须标注，违者打回。
5. **本方案为草案**：未过外脑团评审，不得作为最终执行依据；评审通过后升级为"定稿"。

---

*文档结束*
