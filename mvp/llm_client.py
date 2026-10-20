"""LLM 对话接线 —— pluggable 后端。

- 默认 stub 模式（无 key 时）：返回规则话术，不伪装成模型输出。
- 真实模式：OpenAI 兼容接口（sub2api 经网关，实测 serving agnes-3.0-flash）。
- key 只走环境变量 LLM_API_KEY，不进代码、不进仓库、不进日志。
- 失败时抛 LLMError，由调用方降级为规则策略（教学闭环本身不依赖 LLM）。

主机实测：
  LLM_API_KEY=$(cat /home/ubuntu/.pi-sub2api-key) \\
  LLM_BASE_URL=http://127.0.0.1:3012/v1 \\
  python3 -c "from llm_client import chat; print(chat('用一句话介绍你自己'))"
"""
import json
import os
import urllib.request


class LLMError(Exception):
    pass


def _config():
    return {
        "base_url": os.environ.get("LLM_BASE_URL", "").rstrip("/"),
        "api_key": os.environ.get("LLM_API_KEY", ""),
        "model": os.environ.get("LLM_MODEL", "agnes-3.0-flash"),
    }


def available():
    """是否配置了真实后端。"""
    c = _config()
    return bool(c["base_url"] and c["api_key"])


def stub_reply(prompt):
    """stub 话术（明确标注非模型输出）。"""
    return "[stub] 收到：「%s」。真实模型未接入时，用教学策略引擎的规则话术代替。" % (
        prompt[:40],)


def chat(prompt, system="你是一个 5 岁孩子的 AI 成长伙伴，说话简短、温暖、适龄。"):
    """对话一次。无配置时返回 stub；失败时抛 LLMError。"""
    c = _config()
    if not available():
        return stub_reply(prompt)
    body = json.dumps({
        "model": c["model"],
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 1500,
    }).encode()
    req = urllib.request.Request(
        c["base_url"] + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + c["api_key"]},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        return d["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise LLMError("LLM 调用失败：%s %s" % (type(e).__name__, e))
