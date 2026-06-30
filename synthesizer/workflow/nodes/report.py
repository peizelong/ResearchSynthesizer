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
from synthesizer.services import LLMFusionClient
from synthesizer.services.prompts import REPORT_SYSTEM, build_report_prompt
from synthesizer.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


def _render_report(state: WorkflowState, batch, article_title_map: dict[str, str]) -> str:
    lines: list[str] = []
    merged_themes = state.get("merged_themes", [])
    narratives = state.get("narratives", [])

    lines.append(f"# 多文章方向聚合报告：{batch.name or batch.id}")
    lines.append("")
    lines.append(f"- 批次 ID: `{batch.id}`")
    lines.append(f"- 文章数: {len(batch.article_ids) if batch.article_ids else 0}")
    lines.append(f"- 叙事单元数: {len(narratives)}")
    lines.append(f"- 聚合方向数: {len(merged_themes)}")
    if batch.description:
        lines.append(f"- 说明: {batch.description}")
    lines.append("")

    lines.append("## 一、核心结论")
    lines.append("")
    if merged_themes:
        lines.append(f"- 本批文章共聚合出 {len(merged_themes)} 个方向。")
        for theme in merged_themes[:4]:
            consensus = theme.get("consensus") or "材料中反复出现该方向。"
            lines.append(f"- **{theme['theme_label']}**：{consensus}")
    else:
        lines.append("- 本批次未生成聚合方向。")
    lines.append("")

    lines.append("## 二、去重后的方向总览")
    lines.append("")
    lines.append("| 序号 | 聚合方向 | 子方向 | 来源文章数 | 代表公司 | 核心逻辑 |")
    lines.append("|---|---|---|---|---|---|")
    if merged_themes:
        for i, theme in enumerate(merged_themes, 1):
            companies = _company_names(theme.get("companies", []) or [])[:6]
            logic = theme.get("combined_logic_chain") or theme.get("consensus") or ""
            lines.append(
                f"| {i} | {theme['theme_label']} | "
                f"{'、'.join(theme.get('sub_directions', []) or []) or '-'} | "
                f"{len(set(theme.get('article_ids', []) or []))} | "
                f"{'、'.join(companies) or '-'} | "
                f"{logic or '-'} |"
            )
    else:
        lines.append("| - | - | - | - | - | - |")
    lines.append("")

    lines.append("## 三、核心方向详解")
    lines.append("")
    for i, theme in enumerate(merged_themes, 1):
        lines.append(f"### 方向 {i}：{theme['theme_label']}")
        lines.append("")

        lines.append("#### 1. 合并后的方向描述")
        lines.append(theme.get("consensus") or "材料中反复出现该方向。")
        lines.append("")

        lines.append("#### 2. 合并了哪些相近叫法")
        aliases = theme.get("aliases", []) or theme.get("sub_directions", []) or []
        if aliases:
            for alias in aliases:
                lines.append(f"- {alias}")
        else:
            lines.append("_暂无_")
        lines.append("")

        lines.append("#### 3. 多文共识")
        lines.append(theme.get("consensus") or "_暂无_")
        lines.append("")

        lines.append("#### 4. 不同切入角度")
        angles = theme.get("article_angles", {}) or {}
        divergence = theme.get("divergence_points", []) or []
        if angles:
            for aid, angle in angles.items():
                title = article_title_map.get(aid, aid)
                lines.append(f"- **{title}**：{angle or '暂无'}")
        elif divergence:
            for angle in divergence:
                lines.append(f"- {angle}")
        else:
            lines.append("_暂无_")
        lines.append("")

        lines.append("#### 5. 综合逻辑链")
        lines.append(theme.get("combined_logic_chain") or "_暂无_")
        lines.append("")

        lines.append("#### 6. 涉及产业链环节")
        lines.append(f"- 上游：{'、'.join(theme.get('upstream', []) or []) or '暂无'}")
        lines.append(f"- 中游：{'、'.join(theme.get('midstream', []) or []) or '暂无'}")
        lines.append(f"- 下游：{'、'.join(theme.get('downstream', []) or []) or '暂无'}")
        lines.append("")

        lines.append("#### 7. 反复出现公司")
        companies = theme.get("companies", []) or []
        if companies:
            for company in companies:
                lines.append(f"- {_company_line(company)}")
        else:
            lines.append("_暂无_")
        lines.append("")

        lines.append("#### 8. 需要保留的子方向")
        sub_dirs = theme.get("sub_directions", []) or []
        if sub_dirs:
            for sub_dir in sub_dirs:
                lines.append(f"- {sub_dir}")
        else:
            lines.append("_暂无_")
        lines.append("")

    lines.append("## 四、相关但不应合并的方向")
    lines.append("")
    not_merged = state.get("not_merged", []) or []
    related = []
    for theme in merged_themes:
        for item in theme.get("related_directions", []) or []:
            related.append({"direction": item, "reason": f"与 {theme['theme_label']} 相关但未合并"})
    if not_merged or related:
        for item in not_merged:
            lines.append(
                f"- {item.get('direction_a', '')} / {item.get('direction_b', '')}："
                f"{item.get('reason', '')}"
            )
        for item in related:
            lines.append(f"- {item['direction']}：{item['reason']}")
    else:
        lines.append("_暂无_")
    lines.append("")

    lines.append("## 五、文章覆盖情况")
    lines.append("")
    if article_title_map:
        for article_id, title in article_title_map.items():
            covered = [
                theme["theme_label"]
                for theme in merged_themes
                if article_id in (theme.get("article_ids", []) or [])
            ]
            lines.append(f"- **{title}**（`{article_id}`）：{'、'.join(covered) if covered else '暂无聚合方向'}")
    else:
        lines.append("_暂无文章信息_")
    lines.append("")

    errors = state.get("errors", [])
    quality_issues = state.get("quality_issues", [])
    if errors or quality_issues:
        lines.append("## 处理日志")
        lines.append("")
        for err in errors:
            lines.append(f"- {err}")
        for issue in quality_issues:
            lines.append(f"- {issue.get('description', issue)}")
        lines.append("")

    lines.append("*本报告由 Narrative Synthesizer 投研叙事融合系统生成。*")
    return "\n".join(lines)


def _company_names(companies: list) -> list[str]:
    names: list[str] = []
    for company in companies:
        if isinstance(company, dict):
            name = str(company.get("name") or "").strip()
        else:
            name = str(company or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _company_line(company) -> str:
    if not isinstance(company, dict):
        return str(company)
    name = company.get("name", "")
    reasons = company.get("reasons") or ([company.get("reason")] if company.get("reason") else [])
    segments = company.get("segments") or ([company.get("segment")] if company.get("segment") else [])
    details = []
    if segments:
        details.append(f"环节：{'、'.join(str(x) for x in segments if x)}")
    if reasons:
        details.append(f"原因：{'、'.join(str(x) for x in reasons if x)}")
    return f"{name}（{'；'.join(details)}）" if details else str(name)


def build_report_node(db, llm: LLMFusionClient | None = None):
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

        report = ""
        if llm is not None and state.get("merged_themes"):
            try:
                directions = [_theme_to_direction_payload(theme) for theme in state.get("merged_themes", [])]
                report = llm.complete_text(
                    system=REPORT_SYSTEM,
                    user=build_report_prompt(directions, state.get("not_merged", [])),
                    temperature=0.2,
                ).strip()
            except Exception:
                logger.exception("report LLM call failed, fallback to template renderer")

        if not report or "# 多文章方向聚合报告" not in report:
            report = _render_report(state, batch, article_title_map)

        batch_repo.update_status(state["batch_id"], "completed", stage="report_done")

        logger.info(
            "report: batch %s -> %d chars markdown",
            state["batch_id"], len(report),
        )
        return {"report": report}

    return report_node


def _theme_to_direction_payload(theme: dict) -> dict:
    companies = theme.get("companies", []) or []
    return {
        "direction_name": theme.get("theme_label", ""),
        "aliases": theme.get("aliases", []) or [],
        "sub_directions": theme.get("sub_directions", []) or [],
        "source_unit_ids": theme.get("source_unit_ids", []) or [],
        "source_article_ids": theme.get("article_ids", []) or [],
        "consensus": theme.get("consensus", "") or "",
        "different_angles": theme.get("divergence_points", []) or [],
        "combined_logic_chain": theme.get("combined_logic_chain", "") or "",
        "catalysts": theme.get("catalysts", []) or [],
        "industry_segments": (
            (theme.get("upstream", []) or [])
            + (theme.get("midstream", []) or [])
            + (theme.get("downstream", []) or [])
        ),
        "companies": companies,
        "related_directions": theme.get("related_directions", []) or [],
        "merge_reason": theme.get("merge_reason", "") or "",
    }
