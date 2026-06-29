"""Narrative Synthesizer LangGraph workflow。

7 节点叙事融合流水线：
    article_extract → theme_cluster → theme_merge →
    angle_compare → logic_chain → company_mapping → report
"""
from synthesizer.workflow.graph import build_workflow_graph, run_workflow

__all__ = ["build_workflow_graph", "run_workflow"]
