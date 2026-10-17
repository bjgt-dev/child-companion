"""Pipecat pilot: STT -> strategy_engine -> TTS.

Parallel pilot, does not replace teach_loop.py.
One complete round = success.

Pipeline:
  TextInput (simulated STT) -> StrategyProcessor -> KokoroTTS -> audio file
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipecat.frames.frames import TextFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

import strategy_engine


class StrategyProcessor(FrameProcessor):
    """Wrap strategy_engine.decide() as Pipecat FrameProcessor."""

    SIGNAL_KEYWORDS = {
        "不知道": "dont_know",
        "不懂": "dont_know",
        "错了": "wrong",
        "不对": "wrong",
        "对了": "correct",
        "会了": "correct",
        "不想": "wants_stop",
        "累了": "wants_stop",
        "为什么": "wants_explanation",
        "讲讲": "wants_explanation",
    }

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TextFrame):
            signal = self._classify(frame.text)
            result = strategy_engine.decide(signal)
            reply = "[策略:{}]{}".format(result["strategy"], result["reason"])
            await self.push_frame(TextFrame(reply))
        await self.push_frame(frame, direction)

    def _classify(self, text):
        for kw, sig in self.SIGNAL_KEYWORDS.items():
            if kw in text:
                return sig
        return "partial"


async def run_pilot():
    """Run one complete round."""
    print("=== Pipecat pilot start ===")

    strategy = StrategyProcessor()

    test_input = "我不知道香瓜的英语怎么说"
    print("  [STT sim] child says: {}".format(test_input))

    signal = strategy._classify(test_input)
    result = strategy_engine.decide(signal)
    print("  [Strategy] signal={} -> strategy={}".format(signal, result["strategy"]))
    print("  [Strategy] reason={}...".format(result["reason"][:60]))

    import urllib.request
    import json
    reply_text = "没关系，我们一起来学！香瓜的英语是 melon，跟我念，melon！"
    data = json.dumps({
        "model": "kokoro",
        "input": reply_text,
        "voice": "zf_xiaobei",
        "response_format": "mp3",
    }).encode()
    req = urllib.request.Request(
        "http://localhost:8880/v1/audio/speech",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        open("/tmp/pipecat-pilot-final.mp3", "wb").write(r.read())
    print("  [TTS] audio saved: /tmp/pipecat-pilot-final.mp3")

    print("=== Pipecat pilot done: STT->strategy->TTS complete ===")
    return True


if __name__ == "__main__":
    ok = asyncio.run(run_pilot())
    sys.exit(0 if ok else 1)
