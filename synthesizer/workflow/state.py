"""Narrative Synthesizer workflow 状态定义。

7 节点流水线：
    article_extract → theme_cluster → theme_merge →
    angle_compare → logic_chain → company_mapping → report

State 在节点间流转，每个节点返回 dict 增量更新 State。
`errors` 用 Annotated[list[str], add] 累加。
`merged_themes` 跨 4 个节点（merge/angle/logic/company）逐步回填字段，
LangGraph 默认 dict 替换语义要求每节点返回完整 list（不能只返回增量字段），
所以每个回填节点都返回完整的 merged_themes 列表。
"""
from __future__ import annotations

from operator import add
from typing import Annotated, NotRequired, TypedDict


class ArticleNarrativeData(TypedDict):
    """article_extract_node 产出的单文叙事（内存态，对应 ArticleNarrative 模型）。"""

    narrative_id: str          # ArticleNarrative.id
    article_id: str
    main_themes: list[str]
    direction: NotRequired[str]
    sub_direction: NotRequired[str]
    unit_type: NotRequired[str]
    background: str
    catalysts: list[str]
    industry_segments: list[str]
    companies: list
    logic_chains: list[str]
    logic_chain: NotRequired[list[str]]
    angle: str
    source_quotes: NotRequired[list[str]]
    importance: NotRequired[str]
    sentiment: str
    time_window: str


class MergedThemeData(TypedDict):
    """跨节点逐步填充的融合主题（内存态，对应 MergedTheme 模型）。

    - theme_cluster_node: 不产出 MergedThemeData，只产出 raw_clusters
    - theme_merge_node: 填充 theme_id / theme_label / sub_directions / article_ids / member_count
    - angle_compare_node: 回填 article_angles / divergence_points
    - logic_chain_node: 回填 consensus / combined_logic_chain
    - company_mapping_node: 回填 upstream / midstream / downstream / companies / catalysts
    """

    theme_id: str              # MergedTheme.id
    theme_label: str
    sub_directions: list[str]
    article_ids: list[str]
    member_count: int
    # angle_compare_node
    article_angles: dict[str, str]
    divergence_points: list[str]
    # logic_chain_node
    consensus: str
    combined_logic_chain: str
    # company_mapping_node
    upstream: list[str]
    midstream: list[str]
    downstream: list[str]
    companies: list[dict]      # [{name, direction, article_ids}]
    catalysts: list[str]
    aliases: NotRequired[list[str]]
    source_unit_ids: NotRequired[list[str]]
    related_directions: NotRequired[list[str]]
    merge_reason: NotRequired[str]


class RawCluster(TypedDict):
    """theme_cluster_node 产出的原始聚类（未合并）。"""

    theme_label: str
    sub_directions: list[str]
    article_ids: list[str]
    raw_themes: list[str]
    source_unit_ids: NotRequired[list[str]]
    consensus: NotRequired[str]
    different_angles: NotRequired[list[str]]
    combined_logic_chain: NotRequired[list]
    catalysts: NotRequired[list[str]]
    industry_segments: NotRequired[list[str]]
    companies: NotRequired[list[dict]]
    related_directions: NotRequired[list[str]]
    merge_reason: NotRequired[str]


class WorkflowState(TypedDict):
    """workflow 流转状态。"""

    # 入参
    batch_id: str
    article_ids: list[str]

    # article_extract_node 产出
    narratives: list[ArticleNarrativeData]

    # theme_cluster_node 产出
    raw_clusters: list[RawCluster]

    # theme_merge_node + angle_compare + logic_chain + company_mapping 逐步回填
    merged_themes: list[MergedThemeData]

    # report_node 产出
    report: str

    # quality_check_node 产出
    not_merged: NotRequired[list[dict]]
    quality_issues: NotRequired[list[dict]]

    # 跨节点累加错误日志
    errors: Annotated[list[str], add]
