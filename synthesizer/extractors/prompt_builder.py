from __future__ import annotations

import json
import re

from synthesizer.services.prompts import build_unit_extraction_prompt


def build_narrative_prompt(title: str, content: str) -> str:
    """兼容旧函数名；现在构建“单文叙事单元抽取” prompt。"""
    return build_unit_extraction_prompt(title=title, source="", content=content)


def build_extraction_prompt(title: str, content: str) -> str:
    """向后兼容别名 - 等价于 build_narrative_prompt。"""
    return build_narrative_prompt(title, content)


def chunk_article(content: str, max_tokens: int = 3000) -> list[str]:
    """按段落对文章分块。

    估算口径：中文约 1 字 ≈ 1 token，英文约 2 字符 ≈ 1 token，统一按
    max_tokens * 2 字符作为单块上限。
    """
    if not content or not content.strip():
        return []

    max_chars = max(max_tokens * 2, 1)
    text = content.strip()

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 1 and len(text) > max_chars:
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if para_len > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            for i in range(0, para_len, max_chars):
                chunks.append(para[i:i + max_chars])
            continue
        if current and current_len + para_len + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len + 2

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def parse_llm_json(raw: str) -> dict:
    """容错解析 LLM 返回的 JSON 对象。

    返回 dict；解析失败返回空 dict。
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
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
