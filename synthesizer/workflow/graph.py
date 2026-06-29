"""LangGraph 编排：7 节点叙事融合流水线。

article_extract → theme_cluster → theme_merge →
angle_compare → logic_chain → company_mapping → report

每个节点闭包绑定 db session（与可选 extractor / llm），便于测试注入。
固定路径，无动态分支。
"""
from __future__ import annotations

import logging

from langgraph.graph import END, StateGraph

from synthesizer.extractors import NarrativeExtractor, get_extractor
from synthesizer.services import LLMFusionClient
from synthesizer.workflow.nodes import (
    build_angle_compare_node,
    build_article_extract_node,
    build_company_mapping_node,
    build_logic_chain_node,
    build_report_node,
    build_theme_cluster_node,
    build_theme_merge_node,
)
from synthesizer.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def build_workflow_graph(
    db,
    extractor: NarrativeExtractor | None = None,
    llm: LLMFusionClient | None = None,
):
    """构建 workflow 编译图。

    Args:
        db: SQLAlchemy Session，节点闭包绑定。
        extractor: 单文叙事提取器；None 时用 get_extractor()。
        llm: 融合节点用的 LLMFusionClient；None 时新建（默认 provider）。
    """
    if llm is None:
        llm = LLMFusionClient()

    graph = StateGraph(WorkflowState)

    graph.add_node("article_extract", build_article_extract_node(db, extractor=extractor))
    graph.add_node("theme_cluster", build_theme_cluster_node(db, llm=llm))
    graph.add_node("theme_merge", build_theme_merge_node(db, llm=llm))
    graph.add_node("angle_compare", build_angle_compare_node(db, llm=llm))
    graph.add_node("logic_chain", build_logic_chain_node(db, llm=llm))
    graph.add_node("company_mapping", build_company_mapping_node(db, llm=llm))
    graph.add_node("report", build_report_node(db))

    graph.set_entry_point("article_extract")
    graph.add_edge("article_extract", "theme_cluster")
    graph.add_edge("theme_cluster", "theme_merge")
    graph.add_edge("theme_merge", "angle_compare")
    graph.add_edge("angle_compare", "logic_chain")
    graph.add_edge("logic_chain", "company_mapping")
    graph.add_edge("company_mapping", "report")
    graph.add_edge("report", END)

    return graph.compile()


def run_workflow(
    db,
    batch_id: str,
    article_ids: list[str],
    extractor: NarrativeExtractor | None = None,
    llm: LLMFusionClient | None = None,
) -> WorkflowState:
    """便利函数：构建图并同步执行，返回最终 state。"""
    graph = build_workflow_graph(db, extractor=extractor, llm=llm)
    initial_state: WorkflowState = {
        "batch_id": batch_id,
        "article_ids": article_ids,
        "narratives": [],
        "raw_clusters": [],
        "merged_themes": [],
        "report": "",
        "errors": [],
    }
    return graph.invoke(initial_state)
