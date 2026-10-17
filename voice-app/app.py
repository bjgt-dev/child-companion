"""儿童 AI 伴侣 - 本地语音 App 后端（真实端到端链路测试）

链路：前端录音上传 -> ffmpeg 转 16k WAV -> sherpa-onnx ASR
     -> strategy_engine 策略 -> llm_client (经 omemo) -> edge-tts -> 返回音频

运行：cd /home/ubuntu/child-companion/voice-app && python3 app.py
访问：http://<arm-agent-ip>:18080/
"""
import os
import sys
import time
import uuid
import wave
import subprocess
import asyncio
import numpy as np

from flask import Flask, request, jsonify, send_from_directory

MVP_DIR = "/home/ubuntu/child-companion/mvp"
APP_DIR = "/home/ubuntu/child-companion/voice-app"
AUDIO_DIR = os.path.join(APP_DIR, "audio")
MODEL_DIR = "/data/p0a/sherpa-onnx-streaming-zipformer-zh-int8-2025-06-30"

sys.path.insert(0, MVP_DIR)

# ---- 加载 omemo.env（LLM 经 omemo 记忆代理） ----
def load_env_file(path):
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v

load_env_file(os.path.join(MVP_DIR, "omemo.env"))

import sherpa_onnx
import strategy_engine
from llm_client import chat as llm_chat
import edge_tts

app = Flask(__name__)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---- ASR 模型（启动时加载一次） ----
print("[app] loading ASR model...", flush=True)
t0 = time.time()
recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
    tokens=f"{MODEL_DIR}/tokens.txt",
    encoder=f"{MODEL_DIR}/encoder.int8.onnx",
    decoder=f"{MODEL_DIR}/decoder.onnx",
    joiner=f"{MODEL_DIR}/joiner.int8.onnx",
    num_threads=2,
    provider="cpu",
    sample_rate=16000,
    feature_dim=80,
    decoding_method="greedy_search",
    modeling_unit="cjkchar",
)
print(f"[app] ASR model loaded in {time.time()-t0:.1f}s", flush=True)


def convert_to_16k_wav(src, dst):
    """任意音频 -> 16kHz 单声道 16-bit WAV"""
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-ar", "16000", "-ac", "1",
         "-c:a", "pcm_s16le", dst],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
    )


def asr_transcribe(wav_path):
    with wave.open(wav_path, "rb") as wf:
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        raw = wf.readframes(wf.getnframes())
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    if wf.getnchannels() == 2:
        samples = samples.reshape(-1, 2).mean(axis=1)

    s = recognizer.create_stream()
    s.accept_waveform(16000, samples)
    tail = np.zeros(int(0.66 * 16000), dtype=np.float32)
    s.accept_waveform(16000, tail)
    s.input_finished()
    while recognizer.is_ready(s):
        recognizer.decode_stream(s)
    return recognizer.get_result(s).strip()


def tts_to_mp3(text, out_path):
    async def _run():
        communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural", rate="-20%")
        await communicate.save(out_path)
    asyncio.run(_run())


SYSTEM_PROMPT = (
    "你是小蛋糕，一个 5 岁孩子的 AI 成长伙伴。"
    "说话简短（1-2 句话）、温暖、适龄，像好朋友一样。"
    "孩子嗓子有点哑，多关心她。"
)


@app.route("/")
def index():
    return send_from_directory(APP_DIR, "index.html")


@app.route("/audio/<name>")
def audio(name):
    return send_from_directory(AUDIO_DIR, name)


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/talk", methods=["POST"])
def talk():
    timings = {}
    rid = uuid.uuid4().hex[:8]
    try:
        # 1. 收音频
        f = request.files.get("audio")
        if not f:
            return jsonify({"ok": False, "error": "no audio file"}), 400
        raw_path = os.path.join(AUDIO_DIR, f"{rid}_in")
        f.save(raw_path)
        wav_path = os.path.join(AUDIO_DIR, f"{rid}_16k.wav")
        t = time.time()
        convert_to_16k_wav(raw_path, wav_path)
        timings["convert"] = round(time.time() - t, 2)
        os.remove(raw_path)

        # 2. ASR
        t = time.time()
        text_in = asr_transcribe(wav_path)
        timings["asr"] = round(time.time() - t, 2)
        os.remove(wav_path)
        if not text_in:
            return jsonify({"ok": False, "error": "asr_empty",
                            "timings": timings}), 200

        # 3. 策略引擎
        t = time.time()
        decision = strategy_engine.decide("explore")
        timings["strategy"] = round(time.time() - t, 3)
        strategy = decision["strategy"]

        # 4. LLM
        t = time.time()
        prompt = f"孩子说：「{text_in}」。用温暖简短的话回应（1-2 句）。"
        text_out = None
        last_err = None
        for _a in range(3):
            try:
                text_out = llm_chat(prompt, system=SYSTEM_PROMPT)
                break
            except Exception as _e:
                last_err = _e
                time.sleep(2)
        if text_out is None:
            # LLM 降级：用规则话术，保证孩子永远有回应
            fallback_replies = [
                '奇奇，小蛋糕听到你啦！你刚才说的话我记住了，我们继续玩吧！',
                '嗯嗯，小蛋糕在听！你说得真好，我们再聊一会儿吧！',
                '奇奇真棒！小蛋糕最喜欢跟你说话了，你还想聊什么呀？',
            ]
            import random
            text_out = random.choice(fallback_replies)
            timings['llm_fallback'] = True
        timings["llm"] = round(time.time() - t, 2)

        # 5. TTS
        t = time.time()
        mp3_name = f"{rid}_out.mp3"
        tts_to_mp3(text_out, os.path.join(AUDIO_DIR, mp3_name))
        timings["tts"] = round(time.time() - t, 2)

        timings["total"] = round(sum(timings.values()), 2)
        return jsonify({
            "ok": True,
            "text_in": text_in,
            "strategy": strategy,
            "strategy_reason": decision.get("reason", ""),
            "text_out": text_out,
            "audio_url": f"/audio/{mp3_name}",
            "timings": timings,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}",
                        "timings": timings}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=18080, threaded=True)
