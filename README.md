# 儿童 AI 成长伙伴

一个为 5-6 岁儿童设计的 AI 成长陪伴系统：软件先行，硬件后置。

## 核心理念

- **描述性成长模型**：记录孩子"能做什么"，拒绝数字评分
- **证据分级**：L1 直接观察 / L2 间接证据 / L3 合理推测（必须标注）
- **教育策略版本化**：策略可回滚、可审计
- **xAPI 形状的学习事件**：Actor-Verb-Object，行业标准

## 快速开始

```bash
cd mvp
python3 test_phase0.py  # Phase 0: 成长事件/成长模型/策略版本化
python3 test_phase1.py  # Phase 1: 技能系统/事件桥接
python3 test_phase2.py  # Phase 2: 长期记忆/间隔复习
python3 test_phase3.py  # Phase 3: 学习来源/Numberblocks
python3 test_phase4.py  # Phase 4: 设备管理/OTA
python3 test_phase5.py  # Phase 5: 研究管线/家长助手
```

## 项目结构

```
mvp/
├── growth_event.py      # xAPI 形状的学习事件系统
├── growth_model.py      # 描述性成长模型（代码级禁打分）
├── strategy_engine.py   # 教育策略引擎（版本化）
├── skills.py            # 4 大技能系统
├── event_bridge.py      # 教学闭环事件桥接
├── fading.py            # 提示撤除机制
├── memory.py            # 长期记忆与间隔复习
├── ecosystem.py         # 学习来源生态
├── device.py            # 设备管理（ESP32 预留）
├── safety.py            # 儿童安全护栏
├── advanced.py          # 研究管线/家长助手
└── test_phase*.py       # 各阶段测试
docs/
├── 儿童教育宪章-v2.0.md
└── Skill体系设计规范-v3.0.md
```

## 技术栈

- Python 3（无重型依赖）
- SQLite（开发）/ PostgreSQL（生产）
- xAPI 形状的学习事件

## License

MIT
