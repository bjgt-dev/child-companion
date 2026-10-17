# ASR 流式改造方案（2026-10-17）

> 基于 lumo（lanxiake/lumo，MIT）开源方案的差异分析与改造步骤。
> 只写方案，不动代码。

## 1. 现状 vs 目标

| 维度 | 现状（SenseVoice batch） | 目标（lumo 流式） |
|------|------------------------|------------------|
| 引擎 | sherpa-onnx `OfflineRecognizer.from_sense_voice` | sherpa-onnx **streaming zipformer**（中英双语，int8 量化） |
| 模式 | 整句 batch：等音频文件完整 → 一次转写 | 流式：边说边出 partial 结果 |
| VAD | 无（依赖整句 endpoint） | **Silero VAD** 独立信号（静音检测不依赖解码器输出） |
| 打断 | 不支持 | barge-in：两阶段 arm-then-fire（3 字符 + 麦克风能量阈值 → 250ms 确认 → 700ms 冷却） |
| 回声抑制 | 无 | 文本级 echo filter（与 TTS 输出比对：子串/Jaccard/LCS，丢弃疑似回声） |
| 噪音过滤 | 无 | 7 级垃圾过滤 cascade（短词白名单、单填充词拒绝、垃圾短语黑名单、重复字符 spam、纯填充词、低汉字率、叠填充正则） |
| 生命周期 | 每次创建 stream | 单例 recognizer，序列化 start/stop（避免并发 session 崩溃） |
| 延迟 | 整句等待（~1-3s） | 首字延迟 ~200-400ms（partial 即时） |

## 2. 改造步骤

### Step 1：下载流式模型（1 天）

```bash
# sherpa-onnx streaming zipformer 中英双语 int8
# 来源：k2-fsa/sherpa-onnx 官方 release
# 模型：sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20
# 大小：~500MB（int8 量化）
```

存放：`/home/ubuntu/models/sherpa-onnx-streaming-zipformer-zh-en/`

### Step 2：Silero VAD 集成（2 天）

- pip install silero-vad（或用 sherpa-onnx 内置 VAD）
- VAD 作为独立信号：音频 chunk → VAD 判断是否有人声
- 有人声 → 送入 zipformer stream；静音超 800ms → 判定一句话结束

### Step 3：流式 recognizer 封装（3 天）

```python
# 新文件：mvp/streaming_asr.py（不碰现有 ASR-接口文档的 batch 路径）
import sherpa_onnx

class StreamingASR:
    def __init__(self, model_dir):
        self.recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer(
            encoder=f"{model_dir}/encoder.int8.onnx",
            decoder=f"{model_dir}/decoder.int8.onnx",
            joiner=f"{model_dir}/joiner.int8.onnx",
            tokens=f"{model_dir}/tokens.txt",
            num_threads=2,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
        )
        self.stream = self.recognizer.create_stream()

    def accept_chunk(self, samples_16k: np.ndarray) -> str:
        """输入 16kHz 音频 chunk，返回当前 partial 文本"""
        self.stream.accept_waveform(16000, samples_16k)
        self.recognizer.decode_stream(self.stream)
        return self.stream.result.text

    def reset(self):
        self.stream = self.recognizer.create_stream()
```

- 单例模式：全局一个 `StreamingASR` 实例，串行化调用
- 线程安全：加锁，避免并发 decode

### Step 4：barge-in 打断机制（2 天）

参考 lumo 两阶段：

1. **Arm**：TTS 播放中，ASR partial 文本 ≥3 字符 **且** 麦克风能量 > 0.04 → 进入 arm 状态
2. **Fire**：arm 状态持续 250ms → 确认打断，停止 TTS
3. **Cooldown**：打断后 700ms 内忽略新的打断信号（防抖）

### Step 5：文本级回声过滤（1 天）

- 维护最近 TTS 输出文本列表
- 新 transcript 与 TTS 文本比对：
  - 子串匹配、bigram Jaccard 相似度、LCS
  - 相似度 > 0.7 → 判定为回声，丢弃
- 注意：这是轻量方案，非真正音频 AEC；全双工场景需后续升级

### Step 6：噪音垃圾过滤（1 天）

7 级 cascade（按 lumo）：
1. 短词白名单（如"你好"即使很短也通过）
2. 单填充词拒绝（"嗯"、"啊"单独出现）
3. 垃圾短语黑名单
4. 重复字符 spam（≥85% 同一字符）
5. 纯填充词语句
6. 低汉字率（<0.3，可能是乱码）
7. 叠填充词正则

原则：宁可放过（false negative），不错杀孩子的真实话语。

### Step 7：与 Pipecat 对接（2 天）

- 将 `StreamingASR` 封装为 Pipecat `STTService`
- 输入：音频帧；输出：`TranscriptionFrame`（partial + final）
- 替换 `pipecat_pilot.py` 中的 STT 环节

## 3. 工作量估算

| 步骤 | 工作量 |
|------|--------|
| 模型下载 | 0.5 天 |
| VAD 集成 | 2 天 |
| 流式封装 | 3 天 |
| barge-in | 2 天 |
| 回声过滤 | 1 天 |
| 噪音过滤 | 1 天 |
| Pipecat 对接 | 2 天 |
| **合计** | **约 12 天** |

## 4. 风险与回滚

- **风险**：流式模型中文识别率可能不如 SenseVoice batch（需实测对比）
- **回滚**：保留现有 batch 路径不动，流式作为并行试点；`streaming_asr.py` 独立文件，出问题直接切回

## 5. 验收标准

- [ ] 中文儿童语音识别率 ≥ batch 模式（实测对比 50 条）
- [ ] 首字延迟 < 500ms
- [ ] barge-in 误触发率 < 5%（正常对话 100 轮）
- [ ] 32 个现有测试全过（未动现有代码）

## 参考

- lumo: https://github.com/lanxiake/lumo（MIT）
- sherpa-onnx streaming 文档：https://k2-fsa.github.io/sherpa/onnx/pretrained_models/online-transducer/zipformer-transducer-models.html
- On Top of Pasketti 儿童 ASR 挑战优胜方案：https://github.com/magoo34/on-top-of-pasketti（MIT）
