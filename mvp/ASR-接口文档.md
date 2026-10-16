# ASR 接口文档（儿童 AI 成长伙伴 MVP）

- 验证时间：2026-10-16 21:00 CST
- ASR 引擎：sherpa-onnx **sense_voice**（中文/英文/日韩/粤语），本地离线运行
- 状态：✅ **独立验证通过，可用**

## 1. 部署与代码中的调用路径

| 层级 | 位置 |
|------|------|
| 服务选型配置 | main/xiaozhi-server/data/.config.yaml → selected_module.ASR: SherpaASR；ASR.SherpaASR.type: sherpa_onnx_local |
| Provider 实现 | main/xiaozhi-server/core/providers/asr/sherpa_onnx_local.py（class ASRProvider） |
| 工厂创建 | main/xiaozhi-server/core/utils/asr.py 的 create_instance("sherpa_onnx_local", config, delete_audio_file) |
| 服务内入口 | await provider.speech_to_text(opus_data, session_id, artifacts) → 返回 (text, wav_file_path) |

## 2. 模型与环境

- 模型目录：/home/ubuntu/xiaozhi-server/main/xiaozhi-server/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17
  - model.int8.onnx（int8 量化，239MB）+ tokens.txt
  - 来源：ModelScope pengzhendong/sherpa-onnx-sense-voice-zh-en-ja-ko-yue
- Python 环境：/home/ubuntu/xiaozhi-server/xiaozhi-venv（sherpa_onnx 1.12.29，已验证）
- 加载参数：num_threads=2，sample_rate=16000，feature_dim=80，decoding_method="greedy_search"，use_itn=True
- 首次加载约 **6.9s**（进程常驻后摊销），整机 12GB 内存约用 5GB，尚有余量

## 3. 音频输入要求

- 格式：**单声道 16-bit PCM WAV**（wave 模块可读）
- 采样率：任意——内部自动重采样到 16kHz（已验证 22050Hz 输入正常转写）
- 服务内部流程：ESP32 来的 opus 数据 → 解码为 wav 文件 → 送转写（speech_to_text 的 requires_file() == True）

## 4. 从 Python 独立调用（最小示例，不依赖服务）

```python
import wave
import numpy as np
import sherpa_onnx

MODEL_DIR = ("/home/ubuntu/xiaozhi-server/main/xiaozhi-server/models/"
             "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17")

model = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=f"{MODEL_DIR}/model.int8.onnx",
    tokens=f"{MODEL_DIR}/tokens.txt",
    num_threads=2,
    sample_rate=16000,
    feature_dim=80,
    decoding_method="greedy_search",
    debug=False,
    use_itn=True,
)

def transcribe(wav_path: str) -> str:
    with wave.open(wav_path) as f:
        assert f.getnchannels() == 1 and f.getsampwidth() == 2
        samples = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
        samples = (samples.astype(np.float32) / 32768)
        sr = f.getframerate()
    stream = model.create_stream()
    stream.accept_waveform(sr, samples)   # 非 16k 自动重采样
    model.decode_stream(stream)
    return stream.result.text

print(transcribe("/tmp/asr-test.wav"))
```

运行：/home/ubuntu/xiaozhi-server/xiaozhi-venv/bin/python script.py

## 5. 验证实测数据（独立进程，非服务内）

| 测试音频 | 时长 | 原文 | 转写结果 | 解码耗时 |
|----------|------|------|----------|----------|
| /tmp/asr-test.wav（edge-tts 现场生成） | 4.46s | 小朋友你好，我叫小智，今天想听什么故事呢？ | 小朋友你好，我叫小智。今天想听什么故事呢？ | **0.35s** |
| /home/ubuntu/p0a/piper-test.wav | 2.05s | — | 你好，我叫小智语音。（与部署回执一致） | **0.45s** |

- 准确率：第一句 19/19 字全对，仅逗号被 ITN 转为句号（use_itn=True 的标点归一化，不影响语义）
- 实时率（RTF）：约 0.08–0.2，远快于实时，满足儿童对话场景
- 注意：转写是**离线整句**模式（OfflineRecognizer），不是流式；服务内也是录完音再整句转写

## 6. 使用注意事项

1. **不要重启 xiaozhi-server 主服务**做验证——转写可用独立进程完成，与服务互不干扰。
2. 模型已下载完成，**不要重复下载**（磁盘 / 分区剩约 9G）。
3. ESP32 麦克风采集的音频先经 opus 解码成 wav 再转写；采样率不必强求 16k，单声道+16bit 是硬要求。
4. 儿童语音建议：句式短、语速慢时准确率最高；环境噪声大时先经 VAD（服务已配 SileroVAD）切分。
