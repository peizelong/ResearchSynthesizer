"""叙事融合各节点的 LLM prompt 模板。

5 个调用 LLM 的节点：
  - theme_cluster: 把多篇文章的 main_themes 语义聚类
  - theme_merge:   把一个聚类合并为统一融合主题
  - angle_compare: 比较同一主题下各文章的切入视角
  - logic_chain:   重建综合逻辑链
  - company_mapping: 产业链环节 + 公司映射
"""
from __future__ import annotations

import json

# ============================================================
# theme_cluster_node
# ============================================================
CLUSTER_SYSTEM = "你是投研主题聚类专家。你的任务是把多篇文章提到的一系列主题方向按语义归并到大方向。只输出 JSON。"

CLUSTER_USER_TEMPLATE = """请对下列主题方向做语义聚类。

# 输入
文章与主题清单（JSON）：
{themes_json}

# 任务
1. 把表面词不同但实质属于同一大方向的主题归为一组。
2. 例如 "固态电池安全"、"隔膜材料升级"、"电池热失控防护" 都属于 "电池安全材料升级"。
3. 每组给出一个融合后的主题标签（theme_label）和它包含的子方向（sub_directions）。
4. 记录该组涉及的 article_ids（从输入中获取）。

# 输出格式（严格 JSON，不要任何解释文字）
{{
  "clusters": [
    {{
      "theme_label": "融合后的主题标签",
      "sub_directions": ["子方向1", "子方向2"],
      "article_ids": ["article_id_1", "article_id_2"],
      "raw_themes": ["原始主题1", "原始主题2"]
    }}
  ]
}}
"""


def build_cluster_prompt(article_themes: list[dict]) -> str:
    """article_themes: [{"article_id": "...", "main_themes": ["...", "..."]}, ...]"""
    return CLUSTER_USER_TEMPLATE.format(themes_json=json.dumps(article_themes, ensure_ascii=False, indent=2))


# ============================================================
# theme_merge_node
# ============================================================
MERGE_SYSTEM = "你是投研主题融合专家。你的任务是给一个主题聚类生成统一的融合主题描述。只输出 JSON。"

MERGE_USER_TEMPLATE = """请把下列属于同一大方向的主题合并为一个融合主题。

# 输入
聚类信息（JSON）：
{cluster_json}

# 任务
1. 给出更精炼的 theme_label。
2. 整理 sub_directions（去重、归并）。
3. 用一段话概括 consensus（多文共识）。

# 输出格式（严格 JSON）
{{
  "theme_label": "融合主题标签",
  "sub_directions": ["子方向1", "子方向2"],
  "consensus": "多篇文章共同在讲什么的一句话概括"
}}
"""


def build_merge_prompt(cluster: dict) -> str:
    return MERGE_USER_TEMPLATE.format(cluster_json=json.dumps(cluster, ensure_ascii=False, indent=2))


# ============================================================
# angle_compare_node
# ============================================================
ANGLE_SYSTEM = "你是投研视角比较专家。你的任务是识别同一主题下不同文章的切入角度差异。只输出 JSON。"

ANGLE_USER_TEMPLATE = """请比较下列文章在同一个主题下的切入角度。

# 主题
{theme_label}

# 涉及文章的叙事摘要（JSON）
{articles_json}

# 任务
1. 对每篇文章给出一句话描述它的切入角度（article_angles）。
2. 总结分歧点（divergence_points）。

# 输出格式（严格 JSON）
{{
  "article_angles": {{
    "<article_id>": "该文章的切入角度一句话描述",
    ...
  }},
  "divergence_points": ["分歧点1", "分歧点2"]
}}
"""


def build_angle_prompt(theme_label: str, articles: list[dict]) -> str:
    """articles: [{"article_id": "...", "angle": "...", "background": "...", "logic_chains": [...]}]"""
    return ANGLE_USER_TEMPLATE.format(
        theme_label=theme_label,
        articles_json=json.dumps(articles, ensure_ascii=False, indent=2),
    )


# ============================================================
# logic_chain_node
# ============================================================
LOGIC_SYSTEM = "你是投研逻辑链重建专家。你的任务是把多篇文章的碎片逻辑串成完整逻辑链。只输出 JSON。"

LOGIC_USER_TEMPLATE = """请基于下列多篇文章的叙事，重建该主题的综合逻辑链。

# 主题
{theme_label}

# 多篇文章的逻辑链与背景（JSON）
{articles_json}

# 任务
1. 用一句话总结 consensus（多文共识）。
2. 用箭头串联完整逻辑链 combined_logic_chain（产业背景 → 核心变化 → 市场叙事 → 公司映射）。

# 输出格式（严格 JSON）
{{
  "consensus": "多文共识的一句话",
  "combined_logic_chain": "步骤A → 步骤B → 步骤C → 步骤D"
}}
"""


def build_logic_prompt(theme_label: str, articles: list[dict]) -> str:
    return LOGIC_USER_TEMPLATE.format(
        theme_label=theme_label,
        articles_json=json.dumps(articles, ensure_ascii=False, indent=2),
    )


# ============================================================
# company_mapping_node
# ============================================================
COMPANY_SYSTEM = "你是产业链映射专家。你的任务是把主题涉及的公司归到上中下游并标注方向。只输出 JSON。"

COMPANY_USER_TEMPLATE = """请基于下列多篇文章的叙事，整理该主题的产业链映射。

# 主题
{theme_label}

# 多篇文章的公司、催化、产业链环节（JSON）
{articles_json}

# 任务
1. 把涉及环节归到 upstream / midstream / downstream。
2. companies 列出每家公司及其方向（direction），并标注 article_ids。
3. catalysts 汇总催化因素（去重）。

# 输出格式（严格 JSON）
{{
  "upstream": ["上游环节1", "上游环节2"],
  "midstream": ["中游环节1"],
  "downstream": ["下游环节1"],
  "companies": [
    {{"name": "公司名", "direction": "方向", "article_ids": ["article_id"]}}
  ],
  "catalysts": ["催化因素1", "催化因素2"]
}}
"""


def build_company_prompt(theme_label: str, articles: list[dict]) -> str:
    return COMPANY_USER_TEMPLATE.format(
        theme_label=theme_label,
        articles_json=json.dumps(articles, ensure_ascii=False, indent=2),
    )
