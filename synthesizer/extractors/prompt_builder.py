from __future__ import annotations

import json
import re


_NARRATIVE_PROMPT_TEMPLATE = """你是投研叙事提取专家。你的任务是从单篇投研/社区/产业文章中提取结构化叙事，重点是识别文章在讲什么方向、用什么角度、串什么逻辑。

# 提取字段
- main_themes: 文章的核心方向（list[str]，通常 1-5 个）。例如 "固态电池安全"、"AI算力扩散"、"机器人低位补涨"。
- background: 文章交代的产业背景（一段话）。
- catalysts: 催化因素（list[str]），如 "政策推动"、"产业事故"、"新技术量产"。
- industry_segments: 文章提到的产业链环节（list[str]），如 "隔膜"、"阻燃材料"、"热管理"。
- companies: 文章提到的相关公司（list[str]，公司名）。
- logic_chains: 作者的推演逻辑（list[str]，每条用箭头串联）。例如 "电池安全问题突出 → 隔膜重要性提升 → 相关公司受益"。
- angle: 文章的切入角度（一句话），如 "从政策安全监管角度切入"。
- sentiment: 情绪强度，取值 "乐观" | "中性" | "谨慎"。
- time_window: 时间窗口（如 "2026年下半年"、"短期"、"中长期"）。

# 重要约束
1. 只提取文章明确表达的内容，不要臆测。
2. logic_chains 必须反映作者的推演顺序，用 → 串联。
3. main_themes 用短词组，不要长句。
4. 输出必须是合法 JSON 对象，不要任何解释文字。

# 输出格式
{{
  "main_themes": ["..."],
  "background": "...",
  "catalysts": ["..."],
  "industry_segments": ["..."],
  "companies": ["..."],
  "logic_chains": ["... → ... → ..."],
  "angle": "...",
  "sentiment": "乐观|中性|谨慎",
  "time_window": "..."
}}

# 输入
标题: {title}

正文:
{content}
"""


def build_narrative_prompt(title: str, content: str) -> str:
    """构建单文叙事提取 prompt。"""
    return _NARRATIVE_PROMPT_TEMPLATE.format(title=title or "", content=content or "")


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
