"""提示逐渐撤除 + 依赖度指标 —— Phase 1"""
from __future__ import annotations

class PromptFading:
    """同一目标连续3次独立完成 → 自动降提示等级。"""
    LEVELS = ["大量帮助", "少量提示", "独立"]
    def __init__(self):
        self._streak = {}  # (child, goal) -> 连续独立次数
        self._level = {}   # (child, goal) -> 当前等级下标
    def record(self, child_id, goal, help_level):
        key = (child_id, goal)
        lvl = self.LEVELS.index(help_level) if help_level in self.LEVELS else 2
        self._level[key] = lvl
        if help_level == "独立":
            self._streak[key] = self._streak.get(key, 0) + 1
        else:
            self._streak[key] = 0
        # 连续3次独立 → 降一档（更少帮助）
        if self._streak.get(key, 0) >= 3 and lvl > 0:
            self._level[key] = lvl - 1
            self._streak[key] = 0
    def suggest_level(self, child_id, goal):
        return self.LEVELS[self._level.get((child_id, goal), 2)]

class DependencyMeter:
    """依赖度：连续10次索要答案 → 触发'你想先自己试试吗？'"""
    def __init__(self, threshold=10):
        self._count = {}; self.threshold = threshold
    def record_ask(self, child_id):
        c = self._count.get(child_id, 0) + 1
        self._count[child_id] = c
        return c >= self.threshold
    def record_try(self, child_id):
        self._count[child_id] = 0
