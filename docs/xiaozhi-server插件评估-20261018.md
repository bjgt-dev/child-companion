# xiaozhi-esp32-server 插件机制评估报告

- 评估时间：2026-10-18 22:05（Noesis 亲手实测，非转述）
- 仓库：xinnan-tech/xiaozhi-esp32-server（main/xiaozhi-server，Python）
- 评估方法：git clone 全量源码，逐项核对 ASR/LLM/TTS 插拔点

## 插件机制

`core/providers/{asr,llm,tts,vad,memory,intent}/` 下各 provider 继承 `*ProviderBase` 抽象基类，
`config.yaml` 中 `selected_module` 一行即切换实现。属标准策略模式，插拔点清晰。

## 三个插拔点核对结果

| 我们的部件 | 小智原生 provider | 文件 | 迁移方式 |
|---|---|---|---|
| sherpa-onnx 本地 ASR | SherpaOnnx | `core/providers/asr/sherpa_onnx_local.py`（`ASRProviderBase`，config 含 `model_dir`/`model_type`，支持 paraformer/sense_voice） | 改 `selected_module.ASR: SherpaOnnx`，`model_dir` 指向现有模型目录，零代码改动 |
| edge-tts（晓晓音色） | EdgeTTS | `core/providers/tts/edge.py` | 改 `selected_module.TTS: EdgeTTS`，零代码改动；孩子已认证该音色 |
| LLM（OpenAI 兼容） | OpenAI 兼容 provider | `core/providers/llm/openai/openai.py`；另有 `ChatGLMLLM`（智谱原生，支持 function_call） | `base_url` 指向 new-api（glm-4-flash 免费），或直用 ChatGLMLLM |

## 大脑接入点

- `Intent: function_call` + `plugins_func/`：我们的 strategy_engine（点歌/听故事/11 策略）可做成 function_call 插件。
- `Memory: mem_local_short`：本地记忆、不上传外部，对应 learning_store 理念（长期记忆仍用我们的 learning_store）。
- 三层护栏+安全词转家长：建议做成 LLM 上游封装层（在 openai provider 外包一层审核），不污染协议壳。

## 工作量评估：小

ASR/TTS/LLM 三件全是原生 provider 位，改配置即完成；主要工作量只剩"大脑"接入
（strategy_engine + 护栏 + 安全词），约 1-2 天。无需重写语音链路。

## 结论

采用 xiaozhi-esp32-server 当协议壳技术可行，替换成本低，与 2026-10-18 董事长定案一致。
WebSocket 全双工 + 实时打断（barge-in）+ VAD + 设备管理后台 + OTA 均为原生能力，
正是我们 HTTP 版 voice-app 缺的。
