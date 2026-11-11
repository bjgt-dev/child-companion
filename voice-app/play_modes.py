"""儿童英语开口 3 玩法试点模块（纯逻辑，无音频、无网络、不录真声）
来源借鉴：YouTube 成人口语课的方法思路，只取玩法，不取 31 分钟讲授。
与第一课《小兔子的水果篮》一致的规则：慢速、说错不说"错了"只温柔再问、
奖励只用贴纸/星星、不打分、不排名、不记孩子语音原文。
输入是模拟的 ASR 转写文本（试点用固定例句），不是孩子真实语音。
"""
import difflib
import re

ENCOURAGE = "你说出来了，真棒！我们再来一次。"
REASK = "再听一次，跟小兔子一起说，好吗？"
STAR = "一颗星星给你，今天开口说英语啦！"

def _norm(s):
    return re.sub(r"[^a-z ]", "", (s or "").lower()).strip()

def _sim(a, b):
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()

def shadowing(target, utterance):
    """玩法1 影子跟读：听一句立刻模仿。接近即鼓励，中文/空音只温柔再问。"""
    if not _norm(utterance):
        return {"result": "reask", "say": REASK}
    if _norm(utterance) == _norm(target) or _sim(utterance, target) >= 0.6:
        return {"result": "encourage", "say": ENCOURAGE}
    # 中文回答：不判对，温柔再问英文
    if re.search(r"[\u4e00-\u9fff]", utterance or ""):
        return {"result": "reask", "say": REASK}
    return {"result": "reask", "say": REASK}

def object_naming(item_en, utterance):
    """玩法2 实物指认：看实物说英文名，不经过翻译。中文回答不判对。"""
    if not _norm(utterance):
        return {"result": "reask", "say": REASK}
    if _norm(utterance) == _norm(item_en):
        return {"result": "encourage", "say": ENCOURAGE}
    return {"result": "reask", "say": REASK}

def narrating_play(verb, item_en, utterance):
    """玩法3 边做边说：边玩边说简单句，须同时含动作词和物品词。"""
    u = _norm(utterance)
    if verb in u and _norm(item_en) in u:
        return {"result": "encourage", "say": ENCOURAGE}
    return {"result": "reask", "say": REASK}

# 一课样例：6 步，约 3-5 分钟，混用 3 玩法，角色小兔子白白，场景水果篮延续
LESSON_STEPS = [
    {"mode": "shadowing", "prompt": "Apple, please.", "target": "Apple, please."},
    {"mode": "object_naming", "prompt": "看，篮子里这个是什么？用英文说。", "target": "banana"},
    {"mode": "narrating_play", "prompt": "小兔子在摘草莓，边摘边说。", "verb": "picking", "target": "strawberry"},
    {"mode": "shadowing", "prompt": "I want an apple.", "target": "I want an apple."},
    {"mode": "object_naming", "prompt": "看，篮子里这个是什么？用英文说。", "target": "apple"},
    {"mode": "narrating_play", "prompt": "小兔子在买香蕉，边买边说。", "verb": "buying", "target": "banana"},
]
MAX_STEPS = 6  # 3-5 分钟游戏式：6 步封顶，超时/超步即结束，不拖堂

def run_lesson(utterances):
    """跑一课样例。utterances 为模拟转写列表。返回步数、鼓励数、是否得星。"""
    steps = LESSON_STEPS[:MAX_STEPS]
    results = []
    for step, utt in zip(steps, utterances):
        if step["mode"] == "shadowing":
            r = shadowing(step["target"], utt)
        elif step["mode"] == "object_naming":
            r = object_naming(step["target"], utt)
        else:
            r = narrating_play(step["verb"], step["target"], utt)
        results.append({"mode": step["mode"], "prompt": step["prompt"], **r})
    done = len(results) == MAX_STEPS
    return {"steps_done": len(results), "encouraged": sum(1 for r in results if r["result"] == "encourage"),
            "star": STAR if done else None, "results": results, "max_steps": MAX_STEPS}
