from __future__ import annotations

import httpx

from synthesizer.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from synthesizer.extractors.base import ExtractedNarrative, NarrativeExtractor
from synthesizer.extractors.prompt_builder import (
    build_narrative_prompt,
    chunk_article,
    parse_llm_json,
)


class DeepSeekNarrativeExtractor(NarrativeExtractor):
    """基于 DeepSeek API 的单文叙事提取器。"""

    model_name = "deepseek-chat"

    def extract(self, title: str, content: str) -> ExtractedNarrative:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未配置，无法调用 DeepSeek 叙事提取器")

        chunks = chunk_article(content)
        if not chunks:
            return ExtractedNarrative()

        # 单篇文章一次性提取（chunks 合并取首块为主，超长则取前 2 块拼接）
        merged_content = "\n\n".join(chunks[:2]) if len(chunks) > 1 else chunks[0]
        prompt = build_narrative_prompt(title, merged_content)
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": "Output only valid JSON object."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
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
        raw = resp.json()["choices"][0]["message"]["content"]
        data = parse_llm_json(raw)
        return _build_narrative(data)


def _build_narrative(item: dict) -> ExtractedNarrative:
    def _str_list(key: str) -> list[str]:
        val = item.get(key, [])
        if isinstance(val, list):
            return [str(x) for x in val if x]
        if isinstance(val, str):
            return [val] if val else []
        return []

    sentiment = str(item.get("sentiment") or "中性")
    if sentiment not in ("乐观", "中性", "谨慎"):
        sentiment = "中性"

    return ExtractedNarrative(
        main_themes=_str_list("main_themes"),
        background=str(item.get("background") or ""),
        catalysts=_str_list("catalysts"),
        industry_segments=_str_list("industry_segments"),
        companies=_str_list("companies"),
        logic_chains=_str_list("logic_chains"),
        angle=str(item.get("angle") or ""),
        sentiment=sentiment,
        time_window=str(item.get("time_window") or ""),
    )
