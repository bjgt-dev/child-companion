# 儿童 AI 成长伙伴 — 版本记录

## [Unreleased]
### 新增
- omemo 对话记忆接入主流程（systemd 自启，记忆存取实测通过）
- Pipecat 语音 pipeline 试点（`pipecat_pilot.py`，STT→策略引擎→TTS 跑通）
- Kokoro-82M 中文 TTS 部署验证（Docker，8 音色，推荐 zf_xiaobei）
- ASR 流式改造方案（7 步，预估 12 天）

## v3.0-20261017
### 新增
- V3.0 Phase 0-5 全量实现，32 个测试全过
- Phase 0：成长事件（xAPI）、成长模型（代码级禁打分）、策略版本化
- Phase 1：4 技能系统、事件桥接、提示撤除、5 行为测试
- Phase 2：长期记忆、间隔复习、成长轨迹
- Phase 3：6 类学习来源、Numberblocks 六步链
- Phase 4：设备绑定、OTA、户外模式（软件层）
- Phase 5：研究管线、教研员、发展监测、家长助手 v2
- 儿童教育宪章 v2.0、Skill 体系设计规范 v3.0

## v1.1-20261016
### 新增
- V1.1 基线：教学策略引擎（11 策略）、学习档案（SQLite 三级证据）、教学闭环 CLI
- Numberblocks《认识数字 3》演示
- PostgreSQL 迁移（6 表，18/18 通过）
- sherpa-onnx 真实 ASR、edge-tts 验证
- 四大核心文档 v1.0：教育宪章、教学策略库、能力地图、课程规范
### 标注
- tag `v1.1-baseline`
