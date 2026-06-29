"""Narrative Synthesizer 7 节点 workflow 单元测试 + 端到端测试。

覆盖：
  - TestArticleExtractNode   单文提取
  - TestThemeClusterNode     主题聚类（LLM + 字面兜底）
  - TestThemeMergeNode       方向融合（创建 MergedTheme）
  - TestAngleCompareNode     视角差异回填
  - TestLogicChainNode       逻辑链重建
  - TestCompanyMappingNode   产业链/公司映射
  - TestReportNode           Markdown 报告渲染
  - TestRunWorkflowEndToEnd  端到端跑完整 7 节点
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from synthesizer.extractors import DemoNarrativeExtractor
from synthesizer.models import Article, ResearchBatch
from synthesizer.repositories import NarrativeRepository, ThemeRepository
from synthesizer.services.llm import DemoLLMClient, LLMClient, LLMFusionClient
from synthesizer.workflow import run_workflow
from synthesizer.workflow.nodes.angle_compare import build_angle_compare_node
from synthesizer.workflow.nodes.article_extract import build_article_extract_node
from synthesizer.workflow.nodes.company_mapping import build_company_mapping_node
from synthesizer.workflow.nodes.logic_chain import build_logic_chain_node
from synthesizer.workflow.nodes.report import build_report_node
from synthesizer.workflow.nodes.theme_cluster import build_theme_cluster_node
from synthesizer.workflow.nodes.theme_merge import build_theme_merge_node


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture()
def articles_for_narrative(db_session) -> list[Article]:
    now = datetime.utcnow()
    articles = []
    titles = [
        "政策推动电池安全监管",
        "隔膜供需与渗透率提升",
        "资金扩散低位材料股补涨",
    ]
    for i, title in enumerate(titles):
        a = Article(
            id=str(uuid4()),
            source="jiuyan_web",
            source_article_id=f"n_{i}",
            url=f"https://example.com/n/{i}",
            title=title,
            content=f"文章 {i} 正文。",
            crawled_at=now,
            trust_level="B",
            extraction_status="pending",
        )
        db_session.add(a)
        articles.append(a)
    db_session.commit()
    return articles


@pytest.fixture()
def batch_for_narrative(db_session, articles_for_narrative) -> ResearchBatch:
    batch = ResearchBatch(
        id=str(uuid4()),
        name="叙事测试批次",
        article_ids=[a.id for a in articles_for_narrative],
        status="pending",
        created_at=datetime.utcnow(),
    )
    db_session.add(batch)
    db_session.commit()
    return batch


# ============================================================
# TestArticleExtractNode
# ============================================================
class TestArticleExtractNode:
    def test_produces_narratives_for_each_article(self, db_session, batch_for_narrative, articles_for_narrative):
        node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        state = {
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        }
        result = node(state)
        assert len(result["narratives"]) == 3
        for n in result["narratives"]:
            assert n["narrative_id"]
            assert n["article_id"]
            assert isinstance(n["main_themes"], list)
            assert len(n["main_themes"]) > 0

    def test_persists_narratives_to_db(self, db_session, batch_for_narrative, articles_for_narrative):
        node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        repo = NarrativeRepository(db_session)
        rows = repo.list_by_article_ids([a.id for a in articles_for_narrative])
        assert len(rows) == 3

    def test_idempotent_skip_existing(self, db_session, batch_for_narrative, articles_for_narrative):
        node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        # 第一次
        first = node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        assert len(first["narratives"]) == 3
        # 第二次：应跳过已存在的
        second = node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        assert len(second["narratives"]) == 3  # 仍返回内存态，但不新增 db 行
        repo = NarrativeRepository(db_session)
        assert len(repo.list_by_article_ids([a.id for a in articles_for_narrative])) == 3

    def test_missing_article_records_error(self, db_session, batch_for_narrative):
        node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        result = node({
            "batch_id": batch_for_narrative.id,
            "article_ids": ["nonexistent-id"],
        })
        assert any("not found" in e for e in result["errors"])


# ============================================================
# TestThemeClusterNode
# ============================================================
class TestThemeClusterNode:
    def test_produces_raw_clusters_from_llm(self, db_session, batch_for_narrative, articles_for_narrative):
        # 先跑 extract
        extract_node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        extract_result = extract_node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })

        node = build_theme_cluster_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({"narratives": extract_result["narratives"], "batch_id": batch_for_narrative.id})
        assert len(result["raw_clusters"]) >= 1
        for c in result["raw_clusters"]:
            assert c["theme_label"]
            assert isinstance(c["sub_directions"], list)

    def test_fallback_to_literal_grouping_on_empty_narratives(self, db_session, batch_for_narrative):
        node = build_theme_cluster_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({"narratives": [], "batch_id": batch_for_narrative.id})
        assert result["raw_clusters"] == []

    def test_literal_grouping_when_llm_returns_empty(self, db_session):
        """LLM 返回空时按字面分组。"""

        class EmptyLLM(LLMClient):
            name = "empty"

            def complete(self, system, user, temperature=0.2):
                return "{}"

        node = build_theme_cluster_node(db_session, llm=LLMFusionClient(EmptyLLM()))
        narratives = [
            {"article_id": "a1", "main_themes": ["HBM", "AI算力"]},
            {"article_id": "a2", "main_themes": ["HBM"]},
        ]
        result = node({"narratives": narratives, "batch_id": "batch-x"})
        # 兜底应按字面分组：HBM 与 AI算力 两个 cluster
        labels = [c["theme_label"] for c in result["raw_clusters"]]
        assert "HBM" in labels
        assert "AI算力" in labels


# ============================================================
# TestThemeMergeNode
# ============================================================
class TestThemeMergeNode:
    def test_creates_merged_themes_in_db(self, db_session, batch_for_narrative):
        node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        raw_clusters = [
            {
                "theme_label": "电池安全",
                "sub_directions": ["隔膜", "阻燃"],
                "article_ids": ["a1", "a2"],
                "raw_themes": ["固态电池安全", "隔膜升级"],
            }
        ]
        result = node({
            "batch_id": batch_for_narrative.id,
            "raw_clusters": raw_clusters,
        })
        assert len(result["merged_themes"]) == 1
        m = result["merged_themes"][0]
        assert m["theme_id"]
        assert m["theme_label"]
        assert m["member_count"] == 2

        # db 验证
        repo = ThemeRepository(db_session)
        rows = repo.list_by_batch(batch_for_narrative.id)
        assert len(rows) == 1
        assert rows[0].theme_label == m["theme_label"]

    def test_clears_old_themes_on_rerun(self, db_session, batch_for_narrative):
        node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        # 第一次
        node({
            "batch_id": batch_for_narrative.id,
            "raw_clusters": [{"theme_label": "t1", "sub_directions": [], "article_ids": ["a1"], "raw_themes": []}],
        })
        # 第二次：应清掉旧的
        node({
            "batch_id": batch_for_narrative.id,
            "raw_clusters": [{"theme_label": "t2", "sub_directions": [], "article_ids": ["a1"], "raw_themes": []}],
        })
        repo = ThemeRepository(db_session)
        rows = repo.list_by_batch(batch_for_narrative.id)
        assert len(rows) == 1
        assert rows[0].theme_label == "t2"

    def test_empty_raw_clusters_returns_empty(self, db_session, batch_for_narrative):
        node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({"batch_id": batch_for_narrative.id, "raw_clusters": []})
        assert result["merged_themes"] == []


# ============================================================
# TestAngleCompareNode
# ============================================================
class TestAngleCompareNode:
    def test_fills_article_angles_and_divergence(self, db_session, batch_for_narrative, articles_for_narrative):
        # 先跑 extract + cluster + merge
        extract_node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        extract_result = extract_node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        cluster_node = build_theme_cluster_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        cluster_result = cluster_node({
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        merge_node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        merge_result = merge_node({
            "raw_clusters": cluster_result["raw_clusters"],
            "batch_id": batch_for_narrative.id,
        })

        node = build_angle_compare_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({
            "merged_themes": merge_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })

        assert len(result["merged_themes"]) >= 1
        for m in result["merged_themes"]:
            assert isinstance(m["article_angles"], dict)
            assert isinstance(m["divergence_points"], list)

    def test_empty_merged_themes_returns_empty(self, db_session):
        node = build_angle_compare_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({"merged_themes": [], "narratives": []})
        assert result["merged_themes"] == []


# ============================================================
# TestLogicChainNode
# ============================================================
class TestLogicChainNode:
    def test_fills_consensus_and_logic_chain(self, db_session, batch_for_narrative, articles_for_narrative):
        # 准备 merged_themes（复用前面节点）
        extract_node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        extract_result = extract_node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        cluster_node = build_theme_cluster_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        cluster_result = cluster_node({
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        merge_node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        merge_result = merge_node({
            "raw_clusters": cluster_result["raw_clusters"],
            "batch_id": batch_for_narrative.id,
        })
        angle_node = build_angle_compare_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        angle_result = angle_node({
            "merged_themes": merge_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })

        node = build_logic_chain_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({
            "merged_themes": angle_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })

        for m in result["merged_themes"]:
            assert m["consensus"]  # 非空
            assert m["combined_logic_chain"]  # 非空

    def test_empty_merged_themes(self, db_session):
        node = build_logic_chain_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        assert node({"merged_themes": [], "narratives": []})["merged_themes"] == []


# ============================================================
# TestCompanyMappingNode
# ============================================================
class TestCompanyMappingNode:
    def test_fills_upstream_midstream_downstream_companies(self, db_session, batch_for_narrative, articles_for_narrative):
        # 准备完整前置 state
        extract_node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        extract_result = extract_node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        cluster_node = build_theme_cluster_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        cluster_result = cluster_node({
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        merge_node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        merge_result = merge_node({
            "raw_clusters": cluster_result["raw_clusters"],
            "batch_id": batch_for_narrative.id,
        })
        angle_node = build_angle_compare_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        angle_result = angle_node({
            "merged_themes": merge_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        logic_node = build_logic_chain_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        logic_result = logic_node({
            "merged_themes": angle_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })

        node = build_company_mapping_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        result = node({
            "merged_themes": logic_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })

        for m in result["merged_themes"]:
            assert isinstance(m["upstream"], list)
            assert isinstance(m["midstream"], list)
            assert isinstance(m["downstream"], list)
            assert isinstance(m["companies"], list)
            assert isinstance(m["catalysts"], list)
            # DemoLLM 应返回非空公司
            assert len(m["companies"]) > 0

    def test_empty_merged_themes(self, db_session):
        node = build_company_mapping_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        assert node({"merged_themes": [], "narratives": []})["merged_themes"] == []


# ============================================================
# TestReportNode
# ============================================================
class TestReportNode:
    def test_renders_full_report(self, db_session, batch_for_narrative, articles_for_narrative):
        # 准备完整 state（merged_themes 已被 4 个节点回填）
        extract_node = build_article_extract_node(db_session, extractor=DemoNarrativeExtractor())
        extract_result = extract_node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
        })
        cluster_node = build_theme_cluster_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        cluster_result = cluster_node({
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        merge_node = build_theme_merge_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        merge_result = merge_node({
            "raw_clusters": cluster_result["raw_clusters"],
            "batch_id": batch_for_narrative.id,
        })
        angle_node = build_angle_compare_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        angle_result = angle_node({
            "merged_themes": merge_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        logic_node = build_logic_chain_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        logic_result = logic_node({
            "merged_themes": angle_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })
        company_node = build_company_mapping_node(db_session, llm=LLMFusionClient(DemoLLMClient()))
        company_result = company_node({
            "merged_themes": logic_result["merged_themes"],
            "narratives": extract_result["narratives"],
            "batch_id": batch_for_narrative.id,
        })

        node = build_report_node(db_session)
        result = node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
            "narratives": extract_result["narratives"],
            "merged_themes": company_result["merged_themes"],
            "errors": [],
        })

        report = result["report"]
        assert "# 多文章叙事融合报告" in report
        assert "## 一、共同关注方向" in report
        assert "### 1. 多文共识" in report
        assert "### 2. 不同文章的切入角度" in report
        assert "### 3. 综合逻辑链" in report
        assert "### 4. 涉及产业链环节" in report
        assert "### 5. 文章中反复出现的公司" in report
        assert "### 6. 需要保留的差异视角" in report
        assert "### 7. 催化因素" in report
        assert batch_for_narrative.name in report

    def test_marks_batch_completed(self, db_session, batch_for_narrative, articles_for_narrative):
        node = build_report_node(db_session)
        node({
            "batch_id": batch_for_narrative.id,
            "article_ids": [a.id for a in articles_for_narrative],
            "narratives": [],
            "merged_themes": [],
            "errors": [],
        })
        db_session.expire_all()
        batch = db_session.query(ResearchBatch).filter(ResearchBatch.id == batch_for_narrative.id).first()
        assert batch.status == "completed"
        assert batch.current_stage == "report_done"


# ============================================================
# TestRunWorkflowEndToEnd
# ============================================================
class TestRunWorkflowEndToEnd:
    """端到端：跑完整 7 节点 workflow（DemoExtractor + DemoLLMClient）。"""

    def test_returns_final_state_with_all_fields(self, db_session, batch_for_narrative, articles_for_narrative):
        final_state = run_workflow(
            db=db_session,
            batch_id=batch_for_narrative.id,
            article_ids=[a.id for a in articles_for_narrative],
            extractor=DemoNarrativeExtractor(),
            llm=LLMFusionClient(DemoLLMClient()),
        )
        assert "narratives" in final_state
        assert "raw_clusters" in final_state
        assert "merged_themes" in final_state
        assert "report" in final_state
        assert "errors" in final_state

    def test_produces_narratives_for_all_articles(self, db_session, batch_for_narrative, articles_for_narrative):
        final_state = run_workflow(
            db=db_session,
            batch_id=batch_for_narrative.id,
            article_ids=[a.id for a in articles_for_narrative],
            extractor=DemoNarrativeExtractor(),
            llm=LLMFusionClient(DemoLLMClient()),
        )
        assert len(final_state["narratives"]) == 3

    def test_produces_merged_themes(self, db_session, batch_for_narrative, articles_for_narrative):
        final_state = run_workflow(
            db=db_session,
            batch_id=batch_for_narrative.id,
            article_ids=[a.id for a in articles_for_narrative],
            extractor=DemoNarrativeExtractor(),
            llm=LLMFusionClient(DemoLLMClient()),
        )
        assert len(final_state["merged_themes"]) >= 1
        for m in final_state["merged_themes"]:
            # 所有回填字段都应有内容
            assert m["theme_label"]
            assert m["article_angles"]  # dict 非空
            assert m["consensus"]
            assert m["combined_logic_chain"]
            assert isinstance(m["companies"], list)
            assert len(m["companies"]) > 0

    def test_report_contains_all_sections(self, db_session, batch_for_narrative, articles_for_narrative):
        final_state = run_workflow(
            db=db_session,
            batch_id=batch_for_narrative.id,
            article_ids=[a.id for a in articles_for_narrative],
            extractor=DemoNarrativeExtractor(),
            llm=LLMFusionClient(DemoLLMClient()),
        )
        report = final_state["report"]
        assert "# 多文章叙事融合报告" in report
        assert "## 一、共同关注方向" in report

    def test_marks_batch_completed(self, db_session, batch_for_narrative, articles_for_narrative):
        run_workflow(
            db=db_session,
            batch_id=batch_for_narrative.id,
            article_ids=[a.id for a in articles_for_narrative],
            extractor=DemoNarrativeExtractor(),
            llm=LLMFusionClient(DemoLLMClient()),
        )
        db_session.expire_all()
        batch = db_session.query(ResearchBatch).filter(ResearchBatch.id == batch_for_narrative.id).first()
        assert batch.status == "completed"
        assert batch.current_stage == "report_done"
