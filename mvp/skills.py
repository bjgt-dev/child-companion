"""4个教练 Skill —— Phase 1"""
from __future__ import annotations

class EnglishCoach:
    """英语陪练"""
    WORDS = {"apple": "苹果", "banana": "香蕉", "cat": "猫", "dog": "狗", "red": "红色"}
    def quiz(self, word):
        return {"q": f"{word} 是什么意思？", "a": self.WORDS.get(word, "?")}
    def check(self, word, answer):
        ok = self.WORDS.get(word) == answer.strip()
        return {"correct": ok, "help": "独立" if ok else "少量提示"}

class MathCoach:
    """数学引导（参考开源 adaptive 模式：按表现调难度）"""
    def __init__(self): self.level = 1; self.streak = 0
    def problem(self):
        import random
        a = random.randint(1, 5 * self.level); b = random.randint(1, 5 * self.level)
        return {"q": f"{a} + {b} = ?", "a": a + b}
    def check(self, correct: bool):
        if correct: self.streak += 1
        else: self.streak = 0
        if self.streak >= 3 and self.level < 3:
            self.level += 1; self.streak = 0
        elif not correct and self.level > 1:
            self.level -= 1
        return {"level": self.level}

class StoryCoach:
    """故事表达"""
    def prompt(self, topic="小兔子"):
        return {"q": f"讲一个关于{topic}的故事吧", "hint": "有开头、经过、结尾"}
    def check(self, story: str):
        has_begin = any(w in story for w in ["从前", "有一天", "以前"])
        has_end = any(w in story for w in ["最后", "从此", "结束"])
        return {"complete": has_begin and has_end, "has_begin": has_begin, "has_end": has_end}

class EmotionCoach:
    """情绪认知"""
    EMOTIONS = {"开心": "嘴角上扬", "难过": "想哭的感觉", "生气": "握紧拳头", "害怕": "心跳加快"}
    def quiz(self):
        import random
        e = random.choice(list(self.EMOTIONS))
        return {"q": f"{e}是什么感觉？", "a": self.EMOTIONS[e]}
    def check(self, emotion, answer):
        # 不做诊断，只确认孩子能命名情绪
        return {"named": emotion in self.EMOTIONS}
