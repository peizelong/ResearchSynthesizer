"""Narrative Synthesizer LangGraph workflow。

分层叙事融合流水线：
    article_extract → direction_merge → merge_quality_check → report
"""
from synthesizer.workflow.graph import build_workflow_graph, run_workflow

__all__ = ["build_workflow_graph", "run_workflow"]
