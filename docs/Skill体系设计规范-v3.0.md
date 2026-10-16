# Skill 体系设计规范 V3.0

15 个 skill 的职责边界。每个 skill 是独立模块，有明确输入输出。

| Skill | 做什么 | 不做什么 |
|---|---|---|
| english-coach | 英语陪练：单词、跟读、简单对话 | 不做语法考试 |
| listening-coach | 听力训练：听辨、复述 | 不做速成 |
| math-coach | 数学引导：数感、实物操作 | 不直接给答案 |
| logic-coach | 逻辑思维：分类、排序、推理游戏 | 不做超龄题目 |
| storytelling-coach | 故事表达：讲故事、复述、创作 | 不代替孩子讲 |
| emotion-coach | 情绪认知：识别、命名、表达情绪 | 不做心理诊断 |
| science-explorer | 科学探索：观察、提问、简单实验 | 不给危险实验 |
| reading-coach | 自主阅读：跟读→独立阅读引导 | 不强迫阅读量 |
| creativity-coach | 创造力：绘画、手工、想象游戏 | 不评判好坏 |
| self-learning-coach | 自主学习：教孩子怎么学 | 不替孩子学 |
| parent-copilot | 家长助手：周报、建议、观察入口 | 不给孩子排名 |
| resource-curator | 资源管理：Khan Kids/绘本/视频索引 | 不做盗版资源 |
| learning-scientist | 教研分析：策略效果、证据评估 | 不直接改策略 |
| child-development | 发展监测：10 领域均衡性 | 不打分排名 |
| safety | 安全守卫：内容过滤、时长控制 | 不监控隐私 |

调用关系：teach_loop → 按需调用各 coach → 写 learning_event。
新增教育理念只改对应 skill，不碰主流程。
