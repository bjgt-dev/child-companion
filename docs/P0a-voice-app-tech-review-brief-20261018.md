# 技术部评审 Brief：P0a voice-app（儿童陪伴 agent 语音链路）

- 评审对象：/home/ubuntu/child-companion/voice-app/（app.py、index.html、README.md）
- 背景回执：/data/p0a/p0a-001-v2-receipt.md（10-15 FunASR 失败实证）
- 评审方：Claude Code（产品技术部）
- 发起：2026-10-18，董事长令"代码完成后走技术部评审"

## 交付物现状（Noesis 2026-10-18 实查，非转述）

- 10-15：FunASR（Docker，paraformer-large online 1.7GB）在 ARM64 上输出垃圾文本（"坡坡坡…"），量化/非量化均复现 → 路线放弃，有回执但未投递。
- 10-17：pivot 至 sherpa-onnx streaming zipformer zh int8（/data/p0a/sherpa-onnx-streaming-zipformer-zh-int8-2025-06-30），建成 Flask 端到端应用：手机浏览器录音 → 上传 → ffmpeg 转 16k WAV → sherpa-onnx ASR → strategy_engine（V1.1 MVP）→ llm_client（经 omemo）→ edge-tts → MP3 回放。
- README 声称实测（10-17）：ASR（5.5s 音频 → 1.3-1.9s 解码）识别率 ~100%（同音字除外）；LLM 2.5-9.5s（上游 agnes-3.0-flash 波动大）；TTS ~1-1.7s；端到端 ~6.5s。
- 服务当前运行中（:18080，10-17 晚间有真实 /api/talk 200 日志，10-18 当天有健康检查 200）。

## 评审要点

1. ASR 选型变更裁决：sherpa-onnx 是否可接受为 v2.1 P0a 验收（原文"FunASR 流式可用"）的等价物？约束口径 A（语音数据只在自家 VPS）是否仍然满足？
2. 延迟预算：端到端 ~6.5s vs v2.1 P1 验收 <4s。主要变量是 LLM 上游（2.5-9.5s）。给出优化建议，或接受偏差的书面理由。
3. edge-tts 偶发 NoAudioReceived（微软服务端波动）：代码中重试/降级逻辑是否完备？Piper 备选（/data/p0a/piper 已就绪）是否已接入 fallback？
4. 访问控制：Flask 监听 0.0.0.0:18080。确认是否仅 Tailscale 可达；若公网可达，必须收紧后再进 P0b。
5. 数据生命周期：audio/ 目录留存策略；是否符合 v2.1 §4（加密存、家长可删、90 天自动清）？omemo.env 凭据 handling 是否安全？日志是否记录儿童语音原文（隐私）？
6. 与 V1.1 MVP 的衔接：strategy_engine / learning_store 调用是否正确？learning_store 的证据分级与家长删除接口是否接通？
7. 代码质量：并发、异常处理、模型常驻内存的资源占用、ffmpeg 依赖。

## 通过标准

- 逐条给出 通过 / 有条件通过（列整改项）/ 不通过。
- 整改项区分"P0b 前置"与"可后置"。
- 不许在没有实际执行验证的情况下声称通过（V1.1 第十五章纪律）。
- 评审结论回投递 /home/ubuntu/shared/noesis-inbox/。
