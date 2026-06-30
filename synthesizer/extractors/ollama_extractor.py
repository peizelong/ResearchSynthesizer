from __future__ import annotations

import httpx

from synthesizer.config import OLLAMA_BASE_URL, OLLAMA_LLM_MODEL
from synthesizer.extractors.base import ExtractedNarrative, NarrativeExtractor
from synthesizer.extractors.prompt_builder import chunk_article, parse_llm_json
from synthesizer.extractors.deepseek_extractor import _build_narrative
from synthesizer.services.prompts import UNIT_EXTRACTION_SYSTEM, build_unit_extraction_prompt


class OllamaNarrativeExtractor(NarrativeExtractor):
    """基于 Ollama 本地 LLM 的单文叙事提取器。"""

    model_name = OLLAMA_LLM_MODEL or "qwen2.5"

    def extract(self, title: str, content: str, source: str = "") -> ExtractedNarrative:
        base_url = OLLAMA_BASE_URL or "http://localhost:11434"
        chunks = chunk_article(content)
        if not chunks:
            return ExtractedNarrative()

        merged_content = "\n\n".join(chunks[:2]) if len(chunks) > 1 else chunks[0]
        prompt = build_unit_extraction_prompt(title=title, source=source, content=merged_content)
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": UNIT_EXTRACTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "temperature": 0.1,
        }
        resp = httpx.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=300,
        )
        resp.raise_for_status()
        raw = resp.json()["message"]["content"]
        data = parse_llm_json(raw)
        return _build_narrative(data)
