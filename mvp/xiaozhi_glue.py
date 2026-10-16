"""xiaozhi-server <-> 教学闭环 胶水层（V1.1 第七章落地）。

链路（模拟设备语音端到端）：
    设备语音(wav) -> ASR(Sherpa, 借 xiaozhi-server provider)
    -> 教学闭环(teach_loop.Session + strategy_engine.decide)
    -> 真实 LLM(agnes-3.0-flash, 策略提示词引导)
    -> TTS(EdgeTTS, 借 xiaozhi-server provider) -> 回复音频(mp3)

设计取舍（能跑通为先）：
- 不改 xiaozhi-server 一行代码，只借用它的 provider 类做 ASR/TTS/LLM。
- 教学逻辑全部复用 mvp 现有模块（teach_loop / strategy_engine / learning_store）。
- 孩子话语 -> 观察信号 用规则启发式 infer_signal（v1，显式标注，不伪装智能）。
- key 只走配置文件（xiaozhi-server data/.config.yaml，600 权限），本模块不碰 key。

用法：
    from xiaozhi_glue import ChildCompanion
    c = ChildCompanion(db_path="data/e2e.db", goal_id=1)
    r = await c.handle_utterance("child.wav")
    # r = {"asr_text","signal","strategy","strategy_reason","reply","audio_path"}
    c.finish()
"""

import asyncio
import os
import sys
import uuid

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from learning_store import Store
from teach_loop import Session
from strategy_engine import decide, STRATEGIES

XZ = "/home/ubuntu/xiaozhi-server/main/xiaozhi-server"
XZ_CFG = os.path.join(XZ, "data", ".config.yaml")

# ---- 策略 -> LLM 提示词引导（v1 手写映射） ----
STRATEGY_HINT = {
    "explore": "先跟随孩子的好奇心，用开放式回应陪他探索，不要直接甩标准答案。",
    "socratic": "用一个简短的问题引导孩子自己发现答案，不要直接告诉他答案。",
    "scaffold": "从最少的提示开始，一步一步给孩子搭梯子，慢慢引导。",
    "explain": "直接、清楚地解释，用孩子能懂的比喻，控制在3句话以内。",
    "demo": "建议用身边的实物（积木、手指、水果）来演示这个道理。",
    "game": "把回应包进一个小游戏里，让孩子在玩中学。",
    "transfer": "换一个新例子考考孩子，看他是不是真的理解了。",
    "review": "温和地带孩子复习之前学过的内容。",
    "adjust": "降低难度，用更简单的话重新讲一遍。",
    "comfort_pause": "先安抚孩子的情绪，不要继续提问，允许休息。",
    "wrapup": "总结今天的发现，温暖地结束这次聊天。",
}

BASE_SYSTEM = (
    "你是孩子的 AI 成长伙伴，温暖、耐心，像大姐姐一样。"
    "孩子约 5-6 岁，请用简单易懂的中文短句回答，必要时用拼音标注难字。"
    "多鼓励、多提问引导思考，绝不说教。回答控制在 3 句话以内。"
)


def infer_signal(text):
    """孩子话语 -> 观察信号（规则启发式 v1）。"""
    t = text.strip()
    if any(k in t for k in ("不玩了", "累了", "不想玩", "停下", "不说了", "睡觉")):
        return "wants_stop"
    if any(k in t for k in ("不要", "不回答", "别问了")):
        return "refuse"
    if any(k in t for k in ("不知道", "不会", "不懂")):
        return "dont_know"
    if any(k in t for k in ("为什么", "怎么", "告诉我", "讲讲", "是什么")) or t.endswith(("?", "？", "吗")):
        return "wants_explanation"
    return "wants_explanation"  # 默认：孩子在表达/提问 -> 直接回应解释


def load_xiaozhi_config():
    with open(XZ_CFG) as f:
        return yaml.safe_load(f)


_providers = {}


def init_providers():
    """初始化 ASR / LLM / TTS provider（借 xiaozhi-server 的实现）。"""
    if _providers:
        return _providers
    os.chdir(XZ)  # create_instance 用相对路径找 provider，必须先 cd
    sys.path.insert(0, XZ)
    cfg = load_xiaozhi_config()

    from core.utils import asr as asr_util, llm as llm_util, tts as tts_util

    sel = cfg["selected_module"]
    asr_cfg = cfg["ASR"][sel["ASR"]]
    asr_type = asr_cfg.get("type", sel["ASR"])
    delete_audio = str(cfg.get("delete_audio", True)).lower() in ("true", "1", "yes")
    _providers["asr"] = asr_util.create_instance(asr_type, asr_cfg, delete_audio)

    llm_cfg = cfg["LLM"][sel["LLM"]]
    llm_type = llm_cfg.get("type", sel["LLM"])
    _providers["llm"] = llm_util.create_instance(llm_type, llm_cfg)

    tts_cfg = cfg["TTS"][sel["TTS"]]
    tts_type = tts_cfg.get("type", sel["TTS"])
    _providers["tts"] = tts_util.create_instance(tts_type, tts_cfg, delete_audio)

    _providers["prompt"] = cfg.get("prompt", "")
    return _providers


class ChildCompanion:
    """一次陪伴会话：ASR -> 教学闭环 -> LLM -> TTS。"""

    def __init__(self, db_path, goal_id):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.store = Store(db_path)
        self.store.init_db()
        self.session = Session(self.store, goal_id)
        self.p = init_providers()
        self.sid = "glue-" + uuid.uuid4().hex[:8]

    async def handle_utterance(self, wav_path):
        """处理一段孩子语音，返回各段结果。"""
        from core.providers.asr.base import ASRProviderBase

        asr = self.p["asr"]
        artifacts = ASRProviderBase.AudioArtifacts(
            pcm_frames=[], pcm_bytes=b"", file_path=wav_path, temp_path=None
        )
        asr_text, _ = await asr.speech_to_text([], self.sid, artifacts)
        asr_text = (asr_text or "").strip()
        if not asr_text:
            return {"asr_text": "", "error": "ASR 无结果"}

        # 教学闭环：观察信号 -> 策略
        signal = infer_signal(asr_text)
        d = self.session.child_signal(signal, note="孩子原话：%s" % asr_text[:60])
        strategy = d["strategy"]
        hint = STRATEGY_HINT.get(strategy, "")

        # 真实 LLM（策略引导）
        llm = self.p["llm"]
        system = BASE_SYSTEM + "\n本次教学策略：%s（%s）。%s" % (
            strategy, STRATEGIES.get(strategy, ""), hint)
        dialogue = [
            {"role": "system", "content": system},
            {"role": "user", "content": asr_text},
        ]
        chunks = []
        for ch in llm.response(self.sid, dialogue):
            chunks.append(ch)
        reply = "".join(chunks).strip()

        # TTS
        tts = self.p["tts"]
        out_dir = os.path.join(HERE, "data", "glue_out")
        os.makedirs(out_dir, exist_ok=True)
        audio_path = os.path.join(out_dir, "reply-%s.mp3" % uuid.uuid4().hex[:8])
        await tts.text_to_speak(reply, audio_path)

        return {
            "asr_text": asr_text,
            "signal": signal,
            "strategy": strategy,
            "strategy_reason": d["reason"],
            "reply": reply,
            "audio_path": audio_path,
        }

    def brief(self):
        self.session.brief()

    def finish(self, review_days=2):
        self.session.finish(review_days=review_days)
        self.store.close()


async def main():
    import sys as _s
    wav = os.path.abspath(_s.argv[1])
    db = os.path.join(HERE, "data", "glue_e2e.db")
    if os.path.exists(db):
        os.remove(db)
    store = Store(db)
    store.init_db()
    gid = store.add_goal(3, "对颜色变化的好奇与表达", prerequisites="能说完整句子")
    store.set_mastery(gid, "exploring")
    store.close()

    c = ChildCompanion(db, gid)
    print("======== 教学闭环简报 ========")
    c.brief()
    print("\n======== 处理孩子语音 ========")
    r = await c.handle_utterance(wav)
    print("[ASR 转写] %s" % r.get("asr_text"))
    print("[观察信号] %s" % r.get("signal"))
    print("[教学策略] %s —— %s" % (r.get("strategy"), r.get("strategy_reason")))
    print("[LLM 回复] %s" % r.get("reply"))
    print("[TTS 音频] %s (%d bytes)" % (
        r.get("audio_path"),
        os.path.getsize(r["audio_path"]) if r.get("audio_path") else 0))
    c.finish()
    print("\nE2E_DONE")


if __name__ == "__main__":
    # 必须在事件循环启动前初始化：provider 的 import 链里含 asyncio.run()
    init_providers()
    asyncio.run(main())
