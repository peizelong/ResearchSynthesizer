from __future__ import annotations

import json
import re

_PROMPT_TEMPLATE = """你是市场研究方向抽取专家。你的任务是从财经/研究文章中抽取结构化论断(claim)，重点是识别可能影响市场的"关键方向"。

# 关键方向定义
关键方向是指可能影响市场的主题方向，例如"HBM供应紧张"、"AI算力需求增长"、"半导体国产替代"、"美联储降息"等。一个方向通常由主体(subject)与其趋势/状态(predicate)共同构成。

# 论断类型(claim_type)
- direction: 关键方向论断，描述某个主题的方向性趋势(需填写 direction_tag 与 direction_angle)
- fact: 事实性论断(数据、事件、客观状态)
- prediction: 预测性论断(对未来情况的判断)
- causality: 因果关系论断(A 导致/推动/抑制 B)

# 阐述角度(direction_angle)
每条论断从下列角度之一阐述:
- policy: 政策法规
- industry: 产业链/供需
- company: 公司/竞争
- tech: 技术/产品
- macro: 宏观/金融

# 输出格式
输出一个 JSON 对象，形如:
{{"claims": [ ... ]}}
claims 为 JSON 数组，每个元素包含以下字段:
- claim_type: 论断类型(direction|fact|prediction|causality)
- subject: 论断主体(如 "HBM存储"、"AI算力")
- predicate: 主体的趋势/状态/动作(如 "供应紧张"、"需求增长")
- object_value: 对象或取值，可为 null
- direction_tag: 关键方向标签(如 "HBM供应紧张")；非 direction 论断可为 null
- direction_angle: 阐述角度(policy|industry|company|tech|macro)
- evidence_text: 证据原文，必须从输入原文中逐字照抄
- confidence: 置信度，0 到 1 之间的浮点数

# 重要约束
1. evidence_text 必须原文照抄，严禁总结、改写或翻译。
2. 仅抽取原文明确支持的论断，不得臆测或补充原文之外的信息。
3. 同一方向只抽取一次，避免重复。
4. 若文中没有可抽取的明确论断，返回 {{"claims": []}}。
5. 输出必须是合法 JSON，不要包含任何解释性文字。

# 输入
标题: {title}

正文:
{content}
"""


def build_extraction_prompt(title: str, content: str) -> str:
    """按设计文档第 6.3 节构建抽取 prompt。"""
    return _PROMPT_TEMPLATE.format(title=title or "", content=content or "")


def chunk_article(content: str, max_tokens: int = 3000) -> list[str]:
    """按段落对文章分块，超长文章会被切分为多块以便分多次抽取。

    估算口径: 中文约 1 字 ≈ 1 token，英文约 2 字符 ≈ 1 token，统一按
    max_tokens * 2 字符作为单块上限(留有余量)。
    """
    if not content or not content.strip():
        return []

    max_chars = max(max_tokens * 2, 1)
    text = content.strip()

    # 优先按空行分段
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    # 若无空行且整体超长，退化为按单换行分段
    if len(paragraphs) <= 1 and len(text) > max_chars:
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        # 单段超长则强制按字符切分
        if para_len > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            for i in range(0, para_len, max_chars):
                chunks.append(para[i:i + max_chars])
            continue
        # 累加后超长则收尾当前块
        if current and current_len + para_len + 2 > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += para_len + 2  # +2 估算段落间分隔符长度

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def parse_llm_json(raw: str) -> list[dict]:
    """解析 LLM 返回的 JSON，容错处理 markdown 代码块标记与首尾非 JSON 文本。

    兼容两种返回形态:
    - 直接的 JSON 数组 [{"claim_type": ...}, ...]
    - JSON 对象 {"claims": [...]} (response_format=json_object 模式下的实际返回)
    """
    if not raw or not raw.strip():
        return []

    text = raw.strip()

    # 去除 markdown 代码块标记 (```json ... ``` 或 ``` ... ```)
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]  # 去掉首行围栏
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]  # 去掉末行围栏
            text = "\n".join(lines).strip()

    # 定位首个 { 或 [ 与对应的最后一个 } 或 ]
    start = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start == -1:
        return []

    close_ch = "}" if text[start] == "{" else "]"
    end = text.rfind(close_ch)
    if end == -1 or end < start:
        return []

    candidate = text[start:end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return []

    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        # 从对象中提取第一个列表值(如 "claims")
        for value in data.values():
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        # 单个对象视为单条论断
        return [data]
    return []
