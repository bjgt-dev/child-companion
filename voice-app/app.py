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
import random
import re
_CN_DIGIT = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
def _cn_to_int(s):
    s = s.strip()
    if s.isdigit():
        return int(s)
    if s in ('十一','十二'):
        return 11 if s == '十一' else 12
    if s == '十':
        return 10
    return _CN_DIGIT.get(s)
import wave
import subprocess
import asyncio
import numpy as np

from flask import Flask, request, jsonify, send_from_directory

MVP_DIR = "/home/ubuntu/child-companion/mvp"
APP_DIR = "/home/ubuntu/child-companion/voice-app"
AUDIO_DIR = os.path.join(APP_DIR, "audio")
SONG_DIR = "/data/child-audio"  # 点歌音频库（只读）
SONG_KEYWORDS = ("唱歌", "儿歌", "放首歌", "来首歌", "唱一首", "放一首",
                 "放歌", "听歌", "英文歌", "中文歌", "再放一首", "还要听",
                 "播放", "音乐", "来一首", "唱首", "放音乐", "听音乐")
SLEEP_KEYWORDS = ("分钟后关", "分钟后停", "分钟后睡", "定时关", "定时停",
                    "讲完就睡", "听完就睡", "讲完这个就睡")

PLAY_HISTORY = []  # [{"title":..., "url":..., "kind":"song"/"story"}]，内存，重启清空
CTRL_PREV_KW = ("上一首", "刚才那首", "回放上一首", "前一首")
CTRL_NOW_KW = ("现在放的是什么", "现在播的是什么", "这是什么歌", "这是什么故事",
               "现在是什么", "播的是什么")
CTRL_VOL_UP_KW = ("大声点", "声音大一点", "大点声", "音量大一点")
CTRL_VOL_DOWN_KW = ("小声点", "声音小一点", "小点声", "音量小一点")
CTRL_VOL_MAX_KW = ("声音最大", "音量最大", "开到最大")

# --- 断点续播书签 ---
import sqlite3 as _sql
_BM_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bookmarks.db")
def _bm_init():
    c = _sql.connect(_BM_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS bookmarks(
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT,
        url TEXT, offset_sec REAL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.commit(); c.close()
_bm_init()
def bm_save(kind, title, url, offset_sec):
    if offset_sec < 5:
        return
    c = _sql.connect(_BM_DB)
    c.execute("INSERT INTO bookmarks(kind,title,url,offset_sec) VALUES(?,?,?,?)",
              (kind, title, url, offset_sec))
    c.execute("DELETE FROM bookmarks WHERE id NOT IN (SELECT id FROM bookmarks ORDER BY id DESC LIMIT 20)")
    c.commit(); c.close()
def bm_latest():
    c = _sql.connect(_BM_DB)
    r = c.execute("SELECT kind,title,url,offset_sec FROM bookmarks ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    return r
CTRL_VOL_MIN_KW = ("声音最小", "音量最小", "静音", "关掉声音")

def _title_from_file(fname, kind):
    import re as _re
    base = fname.rsplit(".", 1)[0]
    if kind == "story":
        m = _re.match(r"kameila_(\d+)_(.*)", base)
        if m:
            return "卡梅拉第%s集 %s" % (int(m.group(1)), m.group(2))
        return base
    m = _re.match(r"english_\d+_\d+_(.*)", base)
    if m:
        return m.group(1).replace("_", " ").title()
    m = _re.match(r"english_\d+_(.*)", base)
    if m:
        return m.group(1).replace("_", " ").title()
    return base

_CN_DIGIT = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}

def _parse_cn_minutes(text):
    """解析中文分钟数：半小时→30，三十分钟→30，十分钟→10，一小时→60"""
    import re as _re
    if "半" in text and ("小时" in text or "钟头" in text):
        return 30
    m = _re.search(r"([一二两三四五六七八九]?)十([一二三四五六七八九]?)\s*(分钟|分)", text)
    if m:
        return _CN_DIGIT.get(m.group(1), 1) * 10 + _CN_DIGIT.get(m.group(2), 0)
    m2 = _re.search(r"([一二三四五六七八九])\s*(分钟|分)", text)
    if m2:
        return _CN_DIGIT[m2.group(1)]
    if "小时" in text or "钟头" in text:
        m3 = _re.search(r"([一二两三四五六七八九])\s*(个)?\s*(小时|钟头)", text)
        if m3:
            return _CN_DIGIT[m3.group(1)] * 60
        return 60
    return 0
STORY_KEYWORDS = ("讲故事", "听故事", "卡梅", "来个故事", "再讲一个", "再来一个", "故事")
# P0-2 安全词：命中直接安抚+通知家长，跳过 LLM
SAFETY_KEYWORDS = ("我害怕", "好害怕", "我怕", "有人敲门", "有人来了", "陌生人",
                   "我疼", "好疼", "疼", "受伤", "流血", "救命",
                   "不舒服", "头疼", "肚子疼", "头晕", "想吐", "发烧", "生病了")
# P0-1 本地事实表：儿童高频问答，命中直接回答不经过 LLM
FACT_ANSWERS = {
    "苹果": "apple", "香蕉": "banana", "橙子": "orange", "西瓜": "watermelon",
    "葡萄": "grape", "草莓": "strawberry", "梨": "pear", "桃子": "peach",
    "猫": "cat", "狗": "dog", "鸟": "bird", "鱼": "fish",
    "兔子": "rabbit", "熊": "bear", "猴子": "monkey", "大象": "elephant",
    "红色": "red", "蓝色": "blue", "黄色": "yellow", "绿色": "green",
    "黑色": "black", "白色": "white", "粉色": "pink", "橙色": "orange",
    "一": "one", "二": "two", "三": "three", "四": "four", "五": "five",
    "六": "six", "七": "seven", "八": "eight", "九": "nine", "十": "ten",
}
MODEL_DIR = "/home/ubuntu/xiaozhi-server/main/xiaozhi-server/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"

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
from concurrent.futures import ThreadPoolExecutor as _TPE
# LLM 熔断线程池（3s 超时，超时线程后台自生自灭，不阻塞）
_llm_pool = _TPE(max_workers=2, thread_name_prefix="llm")
LLM_TIMEOUT = 3.0
import edge_tts

app = Flask(__name__)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ---- ASR 模型（启动时加载一次） ----
print("[app] loading ASR model...", flush=True)
t0 = time.time()
recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=f"{MODEL_DIR}/model.int8.onnx",
    tokens=f"{MODEL_DIR}/tokens.txt",
    num_threads=2,
    use_itn=True,
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
    recognizer.decode_stream(s)
    return s.result.text.strip()


def tts_to_mp3(text, out_path):
    async def _run():
        communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural", rate="-20%")
        await communicate.save(out_path)
    asyncio.run(_run())


# 孩子昵称走环境变量 CHILD_NAME，默认"小朋友"（绝不在代码里写真实姓名）
CHILD_NAME = os.environ.get("CHILD_NAME", "小朋友")

SYSTEM_PROMPT = (
    "你是小蛋糕，一个 5 岁孩子的 AI 成长伙伴。"
    "说话简短（1-2 句话）、温暖、适龄，像好朋友一样。"
)


@app.route("/")
def index():
    return send_from_directory(APP_DIR, "index.html")


@app.route("/audio/<name>")
def audio(name):
    return send_from_directory(AUDIO_DIR, name)


@app.route("/songs/<path:subpath>")
def songs(subpath):
    return send_from_directory(SONG_DIR, subpath)


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


@app.route("/api/bookmark", methods=["POST"])
def bookmark():
    d = request.get_json(force=True, silent=True) or {}
    url = d.get("url", "")
    if not url or not url.startswith("/songs/"):
        return jsonify({"ok": False})
    kind = "story" if "/kameila/" in url else "song"
    title = _title_from_file(url.rsplit("/", 1)[-1], kind)
    bm_save(kind, title, url, float(d.get("offset_sec", 0)))
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


        # 2.3 安全词前置（最高优先级）：命中则跳过一切，直接安抚+通知家长
        _safety_hit = any(k in text_in for k in SAFETY_KEYWORDS)
        if _safety_hit:
            _t = "别怕，小蛋糕在这里，爸爸妈妈马上就来！"
            try:
                with open(os.path.join(APP_DIR, "safety_alerts.log"), "a") as _af:
                    _af.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {text_in}\n")
            except Exception:
                pass
            _f = os.path.join(AUDIO_DIR, rid + "_safety.mp3")
            tts_to_mp3(_t, _f)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                            "audio_url": f"/audio/{rid}_safety.mp3",
                            "strategy": "safety_alert",
                            "timings": {"asr": timings["asr"]}})

        # 2.4 播放控制（最高优先级）（上一首/现在放什么/音量）
        _ctrl_done = False
        if any(k in text_in for k in CTRL_PREV_KW):
            _ctrl_done = True
            if len(PLAY_HISTORY) >= 2:
                _prev = PLAY_HISTORY[-2]
                _t = "好，回到上一首：" + _prev["title"]
                _f = os.path.join(AUDIO_DIR, rid + "_prev.mp3")
                tts_to_mp3(_t, _f)
                PLAY_HISTORY.append(_prev)
                return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                                "audio_url": _prev["url"],
                                "announce_url": f"/audio/{rid}_prev.mp3",
                                "strategy": "ctrl_prev",
                                "timings": {"asr": timings["asr"]}})
            _t = "还没有上一首呢，我们先听一首吧！"
            _f = os.path.join(AUDIO_DIR, rid + "_prev.mp3")
            tts_to_mp3(_t, _f)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                            "audio_url": f"/audio/{rid}_prev.mp3",
                            "strategy": "ctrl_prev_empty",
                            "timings": {"asr": timings["asr"]}})
        if any(k in text_in for k in ("继续播放", "接着放", "继续听", "接着听", "从刚才继续")):
            _bm = bm_latest()
            if _bm:
                _kind, _title, _url, _off = _bm
                _mm = int(_off // 60)
                _t = f"好，接着放{_title}，从{_mm}分钟开始！"
                _f = os.path.join(AUDIO_DIR, rid + "_resume.mp3")
                tts_to_mp3(_t, _f)
                return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                                "audio_url": _url,
                                "announce_url": f"/audio/{rid}_resume.mp3",
                                "resume_offset": _off,
                                "strategy": "ctrl_resume",
                                "timings": {"asr": timings["asr"]}})
            _t = "还没有上次的记录呢，你想听什么？"
            _f = os.path.join(AUDIO_DIR, rid + "_resume.mp3")
            tts_to_mp3(_t, _f)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                            "audio_url": f"/audio/{rid}_resume.mp3",
                            "strategy": "ctrl_resume_empty",
                            "timings": {"asr": timings["asr"]}})
        if any(k in text_in for k in CTRL_NOW_KW):
            _ctrl_done = True
            if PLAY_HISTORY:
                _now = PLAY_HISTORY[-1]
                _t = "现在放的是" + _now["title"]
            else:
                _t = "现在还没有播放呢，你想听什么？"
            _f = os.path.join(AUDIO_DIR, rid + "_now.mp3")
            tts_to_mp3(_t, _f)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                            "audio_url": f"/audio/{rid}_now.mp3",
                            "strategy": "ctrl_now",
                            "timings": {"asr": timings["asr"]}})
        _vol = None
        if any(k in text_in for k in CTRL_VOL_MAX_KW):
            _vol = "max"
        elif any(k in text_in for k in CTRL_VOL_MIN_KW):
            _vol = "min"
        elif any(k in text_in for k in CTRL_VOL_UP_KW):
            _vol = "up"
        elif any(k in text_in for k in CTRL_VOL_DOWN_KW):
            _vol = "down"
        if _vol:
            _ctrl_done = True
            _vt = {"max": "好，声音开到最大！", "min": "好，声音关到最小了。",
                   "up": "好，声音大一点！", "down": "好，声音小一点！"}[_vol]
            _f = os.path.join(AUDIO_DIR, rid + "_vol.mp3")
            tts_to_mp3(_vt, _f)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _vt,
                            "audio_url": f"/audio/{rid}_vol.mp3",
                            "strategy": "ctrl_vol", "volume_action": _vol,
                            "timings": {"asr": timings["asr"]}})

        # 2.5 点歌/听故事意图：命中则直接放缓存音频，跳过 LLM/TTS（又快又对）
        _intent = None
        # 故事优先：含故事关键词时不触发点歌（如"播放卡梅拉"）
        _has_story_kw = any(k in text_in for k in STORY_KEYWORDS)
        if any(k in text_in for k in SONG_KEYWORDS) and not _has_story_kw:
            _intent = ("english", "play_song", "点歌意图命中，播放缓存儿歌", None)
        if _intent:
            _subdir, _strategy, _reason, _say = _intent
            try:
                candidates = sorted(
                    f for f in os.listdir(os.path.join(SONG_DIR, _subdir))
                    if f.endswith(".mp3"))
            except OSError:
                candidates = []
            if candidates:
                song = random.choice(candidates)
                timings["media"] = song
                _song_title = _title_from_file(song, "song")
                _say = f"好呀，英文儿歌《{_song_title}》，开始啦！"
                PLAY_HISTORY.append({"title": _song_title,
                                     "url": "/songs/" + _subdir + "/" + song,
                                     "kind": "song"})
                timings["total"] = round(sum(
                    v for v in timings.values() if isinstance(v, (int, float))), 2)
                return jsonify({
                    "ok": True,
                    "text_in": text_in,
                    "strategy": _strategy,
                    "strategy_reason": _reason,
                    "text_out": _say,
                    "audio_url": "/songs/" + _subdir + "/" + song,
                    "timings": timings,
                })
            text_in = text_in + "（音频库暂无缓存，请用语言回应）"

        # 2.5b 睡眠定时（优先于点歌/故事）
        _sleep_hit = any(k in text_in for k in SLEEP_KEYWORDS)
        _sleep_min = 0
        if _sleep_hit:
            m = re.search(r"(\d+)\s*分钟", text_in)
            if m:
                _sleep_min = int(m.group(1))
            else:
                _sleep_min = _parse_cn_minutes(text_in)
            if _sleep_min > 0:
                _t = f"好呀，{_sleep_min}分钟后小蛋糕自动关掉，你安心听吧，晚安！"
            else:
                _t = "好，讲完这个我们就睡觉啦，晚安！"
            _f2 = os.path.join(AUDIO_DIR, rid + "_sleep.mp3")
            tts_to_mp3(_t, _f2)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _t,
                            "audio_url": f"/audio/{rid}_sleep.mp3",
                            "strategy": "sleep_timer", "sleep_minutes": _sleep_min,
                            "timings": {"asr": timings["asr"]}})

# 2.6 卡梅拉选集：模糊发音 + 数字选集 + 问第几集
        _story_hit = any(k in text_in for k in STORY_KEYWORDS)
        _num_only = bool(re.fullmatch(r"\s*第?\s*[0-9一二三四五六七八九十]{1,3}\s*集?\s*", text_in))
        if _story_hit or _num_only:
            _ep_dir = os.path.join(SONG_DIR, "kameila")
            try:
                _ep_files = sorted(f for f in os.listdir(_ep_dir) if f.endswith(".mp3"))
            except OSError:
                _ep_files = []

            def _ep_info(fn):
                m = re.match(r"kameila_(\d+)_(.+)\.mp3$", fn)
                return (int(m.group(1)), m.group(2)) if m else (0, fn)

            def _story_resp(_fn, _say, _strategy, _reason):
                timings["media"] = _fn
                PLAY_HISTORY.append({"title": _title_from_file(_fn, "story"),
                                     "url": "/songs/kameila/" + _fn,
                                     "kind": "story"})
                timings["total"] = round(sum(
                    v for v in timings.values() if isinstance(v, (int, float))), 2)
                return jsonify({
                    "ok": True, "text_in": text_in, "strategy": _strategy,
                    "strategy_reason": _reason, "text_out": _say,
                    "audio_url": "/songs/kameila/" + _fn, "timings": timings})

            if _ep_files:
                _n = None
                _max_ep = len(_ep_files)
                _m = re.search(r"第?\s*([0-9]{1,2}|[一二三四五六七八九十]{1,3})\s*集", text_in)
                if _m:
                    _c = _cn_to_int(_m.group(1))
                    if _c and 1 <= _c <= _max_ep:
                        _n = _c
                if _n is None:
                    _m2 = re.fullmatch(r"\s*([0-9]{1,2}|[一二三四五六七八九十]{1,3})\s*", text_in)
                    if _m2:
                        _c = _cn_to_int(_m2.group(1))
                        if _c and 1 <= _c <= _max_ep:
                            _n = _c
                if _n is not None:
                    _fn = _ep_files[_n - 1]
                    _title = _ep_info(_fn)[1]
                    return _story_resp(
                        _fn, f"好呀，卡梅拉第{_n}集《{_title}》，开始啦！",
                        "play_story", f"选集播放第{_n}集")
                if any(k in text_in for k in ("再讲一个", "再来一个", "换一个", "换一集", "随便")):
                    _fn = random.choice(_ep_files)
                    _num2, _title2 = _ep_info(_fn)
                    return _story_resp(
                        _fn, f"好呀，换卡梅拉第{_num2}集《{_title2}》！",
                        "play_story", "随机换一集")
                # 没说集数：直接从第1集开始放（用户说"放"就是要听）
                _fn = _ep_files[0]
                _title = _ep_info(_fn)[1]
                return _story_resp(
                    _fn, f"好呀，卡梅拉第1集《{_title}》，开始啦！想听别的集告诉小蛋糕数字就行！",
                    "play_story", "默认从第1集播放")
                # 问第几集（TTS 生成问题语音）
                _q = (f"卡梅拉第一季一共有{len(_ep_files)}集，"
                      f"你想听第几集？告诉小蛋糕数字就行啦！")
                _qname = f"{rid}_ask.mp3"
                _t = time.time()
                tts_to_mp3(_q, os.path.join(AUDIO_DIR, _qname))
                timings["tts"] = round(time.time() - _t, 2)
                timings["total"] = round(sum(
                    v for v in timings.values() if isinstance(v, (int, float))), 2)
                return jsonify({
                    "ok": True, "text_in": text_in, "strategy": "ask_episode",
                    "strategy_reason": "询问选集", "text_out": _q,
                    "audio_url": f"/audio/{_qname}", "timings": timings})
            text_in = text_in + "（故事库暂无缓存，请用语言回应）"


        # 2.7 本地事实校验表：高频问题直接给标准答案，不经过 LLM（防幻觉）
        _fact_answer = None
        if any(p in text_in for p in ("英语怎么说", "英文怎么说", "英文是什么", "英语是什么")):
            for _kw, _en in FACT_ANSWERS.items():
                if _kw in text_in:
                    # 英语沉浸：英文先行+中文解释+英文鼓励
                    _praise = random.choice(["Very good!", "Excellent!", "Wonderful!", "Great job!"])
                    _fact_answer = f"{_en}! {_kw}用英语说就是 {_en}，{_praise} 你真棒！"
                    break
        if _fact_answer:
            _f = os.path.join(AUDIO_DIR, rid + "_fact.mp3")
            tts_to_mp3(_fact_answer, _f)
            return jsonify({"ok": True, "text_in": text_in, "text_out": _fact_answer,
                            "audio_url": f"/audio/{rid}_fact.mp3",
                            "strategy": "fact_table",
                            "timings": {"asr": timings["asr"]}})

        # 2.8 英语沉浸检测：孩子说了英文就用英文鼓励强化
        _has_english = bool(re.search(r"[a-zA-Z]{2,}", text_in))
        _en_praise = ""
        if _has_english:
            _en_praise = random.choice(["Wow, you speak English! ", "Great English! ", "I love your English! "])

        # 3. 策略引擎
        t = time.time()
        decision = strategy_engine.decide("explore")
        timings["strategy"] = round(time.time() - t, 3)
        strategy = decision["strategy"]

        # 4. LLM（3s 熔断：超时/异常直接降级，保证端到端 <4s）
        t = time.time()
        prompt = f"孩子说：「{text_in}」。用温暖简短的话回应（1-2 句）。"
        text_out = None
        try:
            fut = _llm_pool.submit(llm_chat, prompt, SYSTEM_PROMPT)
            text_out = fut.result(timeout=LLM_TIMEOUT)
        except Exception as _e:
            timings["llm_breaker"] = True
        if text_out is None:
            # LLM 降级：用规则话术，保证孩子永远有回应
            fallback_replies = [
                f"{CHILD_NAME}，小蛋糕听到你啦！你刚才说的话我记住了，我们继续玩吧！",
                '嗯嗯，小蛋糕在听！你说得真好，我们再聊一会儿吧！',
                f"{CHILD_NAME}真棒！小蛋糕最喜欢跟你说话了，你还想聊什么呀？",
            ]
            text_out = random.choice(fallback_replies)
            timings['llm_fallback'] = True
        timings["llm"] = round(time.time() - t, 2)

        # 4.5 打断确认：用户打断了媒体且走 LLM 路径时，前加一句确认
        _interrupted = request.form.get("interrupted") == "1"
        if _interrupted and text_out and not text_out.startswith("好，停下啦"):
            text_out = "好，停下啦，" + text_out

        # 4.8 英语沉浸：孩子说了英文，前加英文鼓励
        if _en_praise and text_out:
            text_out = _en_praise + text_out

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
