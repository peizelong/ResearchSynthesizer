from __future__ import annotations

import httpx

from synthesizer.config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL
from synthesizer.extractors.base import ExtractedNarrative, ExtractedNarrativeUnit, NarrativeExtractor
from synthesizer.extractors.prompt_builder import chunk_article, parse_llm_json
from synthesizer.services.prompts import UNIT_EXTRACTION_SYSTEM, build_unit_extraction_prompt


class DeepSeekNarrativeExtractor(NarrativeExtractor):
    """基于 DeepSeek API 的单文叙事提取器。"""

    model_name = "deepseek-chat"

    def extract(self, title: str, content: str, source: str = "") -> ExtractedNarrative:
        if not DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY 未配置，无法调用 DeepSeek 叙事提取器")

        chunks = chunk_article(content)
        if not chunks:
            return ExtractedNarrative()

        # 单篇文章一次性提取（chunks 合并取首块为主，超长则取前 2 块拼接）
        merged_content = "\n\n".join(chunks[:2]) if len(chunks) > 1 else chunks[0]
        prompt = build_unit_extraction_prompt(title=title, source=source, content=merged_content)
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": UNIT_EXTRACTION_SYSTEM},
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


def _str_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return []


def _companies(value, direction: str) -> list[dict]:
    result: list[dict] = []
    if not isinstance(value, list):
        value = [value] if value else []
    for item in value:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            result.append({
                "name": name,
                "reason": str(item.get("reason") or "").strip(),
                "related_direction": str(item.get("related_direction") or direction).strip(),
                "segment": str(item.get("segment") or "").strip(),
                "source_quote": str(item.get("source_quote") or "").strip(),
            })
        else:
            name = str(item or "").strip()
            if name:
                result.append({
                    "name": name,
                    "reason": "",
                    "related_direction": direction,
                    "segment": "",
                    "source_quote": "",
                })
    return result


def _logic_chain(item: dict) -> list[str]:
    value = item.get("logic_chain", item.get("logic_chains", []))
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return []


def _build_unit(item: dict) -> ExtractedNarrativeUnit | None:
    themes = _str_list(item.get("main_themes", []))
    direction = str(item.get("direction") or (themes[0] if themes else "")).strip()
    if not direction:
        return None
    sub_direction = str(item.get("sub_direction") or (themes[1] if len(themes) > 1 else "")).strip()

    unit_type = str(item.get("unit_type") or "other").strip()
    allowed_unit_types = {
        "macro_event",
        "industry_cycle",
        "technology_chain",
        "price_hike",
        "bottleneck",
        "capacity_expansion",
        "company_mapping",
        "policy_catalyst",
        "announcement",
        "other",
    }
    if unit_type not in allowed_unit_types:
        unit_type = "other"

    importance = str(item.get("importance") or "core").strip()
    if importance not in {"core", "secondary", "mention"}:
        importance = "core"

    return ExtractedNarrativeUnit(
        direction=direction,
        sub_direction=sub_direction,
        unit_type=unit_type,
        angle=str(item.get("angle") or "").strip(),
        logic_chain=_logic_chain(item),
        catalysts=_str_list(item.get("catalysts", [])),
        industry_segments=_str_list(item.get("industry_segments", [])),
        companies=_companies(item.get("companies", []), direction),
        source_quotes=_str_list(item.get("source_quotes", []))[:3],
        importance=importance,
    )


def _build_narrative(item: dict) -> ExtractedNarrative:
    if not isinstance(item, dict):
        return ExtractedNarrative(article_summary="正文信息不足")

    units_data = item.get("units", [])
    units: list[ExtractedNarrativeUnit] = []
    if isinstance(units_data, list):
        for raw_unit in units_data:
            if isinstance(raw_unit, dict):
                unit = _build_unit(raw_unit)
                if unit:
                    units.append(unit)

    if not units:
        legacy_unit = _build_unit(item)
        if legacy_unit:
            units.append(legacy_unit)

    sentiment = str(item.get("sentiment") or "中性")
    if sentiment not in ("乐观", "中性", "谨慎"):
        sentiment = "中性"

    return ExtractedNarrative(
        document_type=str(item.get("document_type") or "single_theme_article"),
        article_summary=str(item.get("article_summary") or item.get("background") or ""),
        units=units,
        background=str(item.get("article_summary") or item.get("background") or ""),
        sentiment=sentiment,
        time_window=str(item.get("time_window") or ""),
    )
