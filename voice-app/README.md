# 小蛋糕语音 App（真实端到端链路测试）

## 链路
手机浏览器录音 → 上传 arm-agent → ffmpeg 转 16k WAV
→ sherpa-onnx ASR（自有模型） → strategy_engine 策略 → llm_client（经 omemo）
→ edge-tts → MP3 返回 → 手机自动播放

## 访问
http://100.103.193.123:18080/（需 Tailscale 网络）

## 运维
- 启动：`/tmp/start_voice_app.sh`
- 日志：`/tmp/voice-app.log`
- 停止：`pkill -f "voice-app/app.py"`
- 端口：18080

## 实测数据（2026-10-17）
- ASR：5.5s 音频 → 1.3-1.9s 解码，识别率 ~100%（同音字 小朋友/琪琪 除外）
- LLM：2.5-9.5s（上游 agnes-3.0-flash 延迟波动大）
- TTS：~1-1.7s（41 字）
- 端到端：~6.5s（含转码）

## 已知问题
- edge-tts 偶发 NoAudioReceived（微软服务端波动，重试即可）
- LLM 延迟不稳定（2.5s ~ 9.5s），是端到端最大变量
- ASR 对含糊语音（孩子嗓子哑）的鲁棒性待真人实测
