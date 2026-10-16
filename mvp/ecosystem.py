"""学习生态 —— Phase 3：6类来源接入 + Numberblocks六步链"""
from __future__ import annotations

# 6类学习来源
SOURCES = {
    "course": "结构化课程（Khan Kids）",
    "video": "视频（Numberblocks/YT Kids）",
    "book": "绘本",
    "toy": "玩具（积木/拼图/桌游）",
    "life": "现实生活",
    "ai": "AI活动",
}

# Numberblocks 六步链模板（数字1-10）
def numberblocks_chain(n: int):
    return {
        "number": n,
        "steps": [
            {"step": "输入", "activity": f"看 Numberblocks 第{n}集"},
            {"step": "对话", "activity": "你发现了什么？"},
            {"step": "动手", "activity": f"用积木搭出{n}"},
            {"step": "生活", "activity": f"找家里{n}个一样的东西"},
            {"step": "迁移", "activity": f"{n}个苹果再拿来2个呢？"},
            {"step": "创造", "activity": f"设计有{n}个房间的房子"},
        ],
    }

def source_to_event(source_type: str, description: str):
    """学习来源 → xAPI 事件 verb 映射。"""
    verb_map = {
        "course": "completed", "video": "watched", "book": "read",
        "toy": "played", "life": "observed", "ai": "completed",
    }
    if source_type not in SOURCES:
        raise ValueError(f"未知来源: {source_type}")
    return {"verb": verb_map[source_type], "object_type": source_type}

class ResourceCurator:
    """家长登记孩子看了什么 → 生成4步活动建议。"""
    def suggest(self, source_type, title):
        if source_type == "video" and "numberblocks" in title.lower():
            # 提取数字
            import re
            m = re.search(r"\d+", title)
            n = int(m.group()) if m else 1
            chain = numberblocks_chain(min(n, 10))
            return chain["steps"][1:5]  # 对话→动手→生活→迁移
        return [
            {"step": "对话", "activity": f"聊聊{title}：印象最深的是什么？"},
            {"step": "动手", "activity": f"用实物重现{title}里的场景"},
            {"step": "生活", "activity": f"在家里找找和{title}相关的东西"},
            {"step": "迁移", "activity": f"如果换个场景，还会吗？"},
        ]
