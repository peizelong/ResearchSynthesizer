"""report_node: 报告生成 - 基于完整 merged_themes 渲染叙事融合 Markdown 报告。

不调 LLM，纯模板渲染。报告结构对应需求文档：
  # 多文章叙事融合报告
  ## 一、共同关注方向
  ## 二、方向 N：{theme_label}
    ### 1. 多文共识
    ### 2. 不同文章的切入角度
    ### 3. 综合逻辑链
    ### 4. 涉及产业链环节
    ### 5. 文章中反复出现的公司
    ### 6. 需要保留的差异视角
    ### 7. 催化因素
"""
from __future__ import annotations

import logging

from synthesizer.repositories import ArticleRepository, BatchRepository, NarrativeRepository
from synthesizer.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def _render_report(state: WorkflowState, batch, article_title_map: dict[str, str]) -> str:
    lines: list[str] = []
    merged_themes = state.get("merged_themes", [])
    narratives = state.get("narratives", [])

    # 标题与摘要
    lines.append(f"# 多文章叙事融合报告：{batch.name or batch.id}")
    lines.append("")
    lines.append(f"- 批次 ID: `{batch.id}`")
    lines.append(f"- 文章数: {len(batch.article_ids) if batch.article_ids else 0}")
    lines.append(f"- 融合主题数: {len(merged_themes)}")
    lines.append(f"- 提取叙事数: {len(narratives)}")
    if batch.description:
        lines.append(f"- 说明: {batch.description}")
    lines.append("")

    # 一、共同关注方向
    lines.append("## 一、共同关注方向")
    lines.append("")
    if merged_themes:
        for i, theme in enumerate(merged_themes, 1):
            lines.append(f"{i}. {theme['theme_label']}")
        lines.append("")
    else:
        lines.append("_本批次未生成融合主题。_")
        lines.append("")

    # 二、每个方向详细
    for i, theme in enumerate(merged_themes, 1):
        lines.append(f"## 二、方向 {i}：{theme['theme_label']}")
        lines.append("")

        # 1. 多文共识
        lines.append("### 1. 多文共识")
        lines.append("")
        consensus = theme.get("consensus") or "_（无）_"
        lines.append(consensus)
        lines.append("")

        # 2. 不同文章的切入角度
        lines.append("### 2. 不同文章的切入角度")
        lines.append("")
        article_angles = theme.get("article_angles", {}) or {}
        if article_angles:
            for aid, angle in article_angles.items():
                title = article_title_map.get(aid, aid)
                lines.append(f"**{title}**（`{aid}`）：")
                lines.append(angle or "_（无）_")
                lines.append("")
        else:
            lines.append("_（无视角数据）_")
            lines.append("")

        # 3. 综合逻辑链
        lines.append("### 3. 综合逻辑链")
        lines.append("")
        chain = theme.get("combined_logic_chain") or "_（无）_"
        lines.append(chain)
        lines.append("")

        # 4. 涉及产业链环节
        lines.append("### 4. 涉及产业链环节")
        lines.append("")
        lines.append("**上游**：")
        upstream = theme.get("upstream", []) or []
        lines.append("、".join(upstream) if upstream else "_（无）_")
        lines.append("")
        lines.append("**中游**：")
        midstream = theme.get("midstream", []) or []
        lines.append("、".join(midstream) if midstream else "_（无）_")
        lines.append("")
        lines.append("**下游**：")
        downstream = theme.get("downstream", []) or []
        lines.append("、".join(downstream) if downstream else "_（无）_")
        lines.append("")

        # 5. 文章中反复出现的公司
        lines.append("### 5. 文章中反复出现的公司")
        lines.append("")
        companies = theme.get("companies", []) or []
        if companies:
            for c in companies:
                name = c.get("name", "") if isinstance(c, dict) else str(c)
                direction = c.get("direction", "") if isinstance(c, dict) else ""
                direction_str = f"（{direction}）" if direction else ""
                lines.append(f"- {name}{direction_str}")
            lines.append("")
        else:
            lines.append("_（无）_")
            lines.append("")

        # 6. 需要保留的差异视角
        lines.append("### 6. 需要保留的差异视角")
        lines.append("")
        divergence = theme.get("divergence_points", []) or []
        if divergence:
            for d in divergence:
                lines.append(f"- {d}")
            lines.append("")
        else:
            lines.append("_（无明显分歧）_")
            lines.append("")

        # 7. 催化因素
        lines.append("### 7. 催化因素")
        lines.append("")
        catalysts = theme.get("catalysts", []) or []
        if catalysts:
            for cat in catalysts:
                lines.append(f"- {cat}")
            lines.append("")
        else:
            lines.append("_（无）_")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 处理日志
    errors = state.get("errors", [])
    if errors:
        lines.append("## 处理日志")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("*本报告由 Narrative Synthesizer 投研叙事融合系统生成。*")

    return "\n".join(lines)


def build_report_node(db):
    """返回绑定 db 的 report_node 闭包。"""

    def report_node(state: WorkflowState) -> dict:
        batch_repo = BatchRepository(db)
        article_repo = ArticleRepository(db)

        batch_repo.update_status(state["batch_id"], "running", stage="generate_report")

        batch = batch_repo.get(state["batch_id"])
        if not batch:
            return {"report": "_批次不存在_", "errors": [f"report: batch {state['batch_id']} not found"]}

        # 拉取文章标题用于报告
        article_title_map: dict[str, str] = {}
        for aid in batch.article_ids or []:
            a = article_repo.get(aid)
            if a:
                article_title_map[aid] = a.title

        report = _render_report(state, batch, article_title_map)

        batch_repo.update_status(state["batch_id"], "completed", stage="report_done")

        logger.info(
            "report: batch %s -> %d chars markdown",
            state["batch_id"], len(report),
        )
        return {"report": report}

    return report_node
