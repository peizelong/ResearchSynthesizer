"""Narrative Synthesizer workflow 节点集合。

7 节点流水线：
    article_extract → theme_cluster → theme_merge →
    angle_compare → logic_chain → company_mapping → report

每个节点是闭包工厂 `build_xxx_node(db, ...) -> callable(state) -> dict`，
绑定 db session 与可选依赖（extractor / llm），便于测试注入。
"""
from synthesizer.workflow.nodes.article_extract import build_article_extract_node
from synthesizer.workflow.nodes.theme_cluster import build_theme_cluster_node
from synthesizer.workflow.nodes.theme_merge import build_theme_merge_node
from synthesizer.workflow.nodes.angle_compare import build_angle_compare_node
from synthesizer.workflow.nodes.logic_chain import build_logic_chain_node
from synthesizer.workflow.nodes.company_mapping import build_company_mapping_node
from synthesizer.workflow.nodes.report import build_report_node

__all__ = [
    "build_article_extract_node",
    "build_theme_cluster_node",
    "build_theme_merge_node",
    "build_angle_compare_node",
    "build_logic_chain_node",
    "build_company_mapping_node",
    "build_report_node",
]
