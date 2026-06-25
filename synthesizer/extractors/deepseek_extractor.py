from __future__ import annotations

import httpx

from synthesizer.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from synthesizer.extractors.base import ClaimExtractor, ExtractedClaim
from synthesizer.extractors.prompt_builder import (
    build_extraction_prompt,
    chunk_article,
    parse_llm_json,
)


class DeepSeekExtractor(ClaimExtractor):
    """基于 DeepSeek API 的论断抽取器。"""

    model_name = "deepseek-chat"
    API_URL = "https://api.deepseek.com/v1/chat/completions"

    def extract(self, title: str, content: str) -> list[ExtractedClaim]:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未配置，无法调用 DeepSeek 抽取器")

        chunks = chunk_article(content)
        all_claims: list[ExtractedClaim] = []
        seen: set[tuple[str, str, str | None]] = set()

        for chunk in chunks:
            prompt = build_extraction_prompt(title, chunk)
            payload = {
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "Output only valid JSON array."},
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
                DEEPSEEK_API_URL or self.API_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]

            for item in parse_llm_json(raw):
                claim = _build_claim(item)
                key = (claim.subject, claim.predicate, claim.object_value)
                if key in seen:
                    continue
                seen.add(key)
                all_claims.append(claim)

        return all_claims


def _build_claim(item: dict) -> ExtractedClaim:
    conf = item.get("confidence", 0.5)
    try:
        confidence = float(conf) if conf is not None else 0.5
    except (TypeError, ValueError):
        confidence = 0.5
    return ExtractedClaim(
        claim_type=item.get("claim_type", "fact") or "fact",
        subject=item.get("subject", "") or "",
        predicate=item.get("predicate", "") or "",
        object_value=item.get("object_value"),
        direction_tag=item.get("direction_tag"),
        direction_angle=item.get("direction_angle"),
        evidence_text=item.get("evidence_text", "") or "",
        confidence=confidence,
    )
