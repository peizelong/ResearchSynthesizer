"""共享 LLM 客户端 - 供主题融合/视角比较/逻辑链等节点调用。

封装 DeepSeek 与 Ollama 两种 provider，统一接口：
    client.complete(system, user) -> str

子类 LLMFusionClient 增加 complete_json(system, user) -> dict | list，
自动解析 JSON 并容错处理 markdown 代码块。
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

import httpx

from synthesizer.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_API_URL,
    DEEPSEEK_MODEL,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_LLM_MODEL,
)

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM 客户端抽象基类。"""

    name: str = "abstract"

    @abstractmethod
    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        """返回 LLM 原始文本响应。"""
        ...


class DeepSeekClient(LLMClient):
    name = "deepseek"

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未配置")
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": 8192,
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            DEEPSEEK_API_URL or "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class OllamaClient(LLMClient):
    name = "ollama"

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        payload = {
            "model": OLLAMA_LLM_MODEL or "qwen2.5",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "format": "json",
            "temperature": temperature,
        }
        resp = httpx.post(
            f"{OLLAMA_BASE_URL or 'http://localhost:11434'}/api/chat",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


class DemoLLMClient(LLMClient):
    """测试用客户端 - 不调用任何 LLM，按 user 内容关键词返回固定 JSON。

    覆盖 5 类节点调用：
      - "聚类" / "cluster"  → 主题聚类结果
      - "融合" / "merge"    → 融合主题
      - "视角" / "angle"    → 视角比较
      - "逻辑链" / "logic"  → 逻辑链重建
      - "产业链" / "company"→ 公司映射
    """

    name = "demo"

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        text = (system + "\n" + user).lower()

        if "聚类" in user or "cluster" in text:
            # 从输入中提取所有 article_id，使下游节点能匹配到对应文章叙事
            import re

            article_ids = re.findall(r'"article_id"\s*:\s*"([^"]+)"', user)
            return json.dumps({
                "clusters": [
                    {
                        "theme_label": "电池安全材料升级",
                        "sub_directions": ["固态电池安全", "隔膜材料升级", "电池热失控防护"],
                        "article_ids": article_ids,
                        "raw_themes": ["固态电池安全", "隔膜材料升级", "电池热失控防护"],
                    }
                ]
            }, ensure_ascii=False)

        if "融合" in user or "merge" in text:
            # 尝试从输入 cluster JSON 中提取 theme_label 原样回传，
            # 使 demo 在重跑/多主题场景中可区分（默认值用于无输入情况）。
            import re

            label_match = re.search(r'"theme_label"\s*:\s*"([^"]+)"', user)
            theme_label = label_match.group(1) if label_match else "电池安全材料升级"
            return json.dumps({
                "theme_label": theme_label,
                "sub_directions": ["隔膜材料", "阻燃材料", "热失控防护"],
                "consensus": "多篇文章都提到电池安全问题正在扩展到多个材料环节。",
            }, ensure_ascii=False)

        if "视角" in user or "angle" in text:
            return json.dumps({
                "article_angles": {
                    "article_A": "从政策和安全监管角度切入。",
                    "article_B": "从产业链供需角度切入。",
                },
                "divergence_points": ["有的偏产业逻辑，有的偏短线题材。"],
            }, ensure_ascii=False)

        if "逻辑链" in user or "logic" in text:
            return json.dumps({
                "consensus": "安全要求提升是共同主线。",
                "combined_logic_chain": "安全事故/监管趋严 → 电池安全要求提升 → 隔膜/阻燃/热管理材料需求提升 → 低位细分公司被重新定价",
            }, ensure_ascii=False)

        if "产业链" in user or "company" in text:
            return json.dumps({
                "upstream": ["基础化工材料", "膜材料"],
                "midstream": ["隔膜", "涂覆材料", "热管理材料"],
                "downstream": ["动力电池", "储能", "电动车"],
                "companies": [
                    {"name": "公司A", "direction": "隔膜", "article_ids": []},
                    {"name": "公司B", "direction": "阻燃材料", "article_ids": []},
                ],
                "catalysts": ["政策推动", "产业事故", "新技术量产"],
            }, ensure_ascii=False)

        return json.dumps({}, ensure_ascii=False)


def get_llm_client(provider: str | None = None) -> LLMClient:
    """根据配置返回 LLM 客户端实例。"""
    name = (provider or LLM_PROVIDER or "deepseek").strip().lower()
    if name == "deepseek":
        return DeepSeekClient()
    if name == "ollama":
        return OllamaClient()
    if name == "demo":
        return DemoLLMClient()
    return DemoLLMClient()


def parse_llm_json(raw: str) -> dict | list:
    """容错解析 LLM 返回的 JSON 文本。

    - 去除 markdown 代码块围栏
    - 定位首个 { / [ 与末尾 } / ]
    - 返回 dict 或 list；解析失败返回空 dict
    """
    if not raw or not raw.strip():
        return {}
    text = raw.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

    start = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start == -1:
        return {}

    close_ch = "}" if text[start] == "{" else "]"
    end = text.rfind(close_ch)
    if end == -1 or end < start:
        return {}

    try:
        data = json.loads(text[start:end + 1])
        return data if isinstance(data, (dict, list)) else {}
    except json.JSONDecodeError:
        return {}


class LLMFusionClient:
    """高层封装：complete_json 自动解析 JSON。供融合节点使用。"""

    def __init__(self, client: LLMClient | None = None):
        self.client = client or get_llm_client()

    def complete_json(self, system: str, user: str, temperature: float = 0.2) -> dict | list:
        raw = self.client.complete(system, user, temperature=temperature)
        return parse_llm_json(raw)
