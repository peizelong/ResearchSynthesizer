from __future__ import annotations

from synthesizer.extractors import (
    DemoNarrativeExtractor,
    ExtractedNarrative,
    get_extractor,
)
from synthesizer.extractors.prompt_builder import (
    build_narrative_prompt,
    chunk_article,
    parse_llm_json,
)


class TestPromptBuilder:
    def test_prompt_contains_title_and_content(self):
        prompt = build_narrative_prompt("测试标题", "测试正文")
        assert "测试标题" in prompt
        assert "测试正文" in prompt
        assert "units" in prompt
        assert "叙事单元" in prompt

    def test_chunk_article_empty(self):
        assert chunk_article("") == []
        assert chunk_article("   ") == []

    def test_chunk_article_short(self):
        assert chunk_article("短文本") == ["短文本"]

    def test_chunk_article_long(self):
        content = "\n\n".join([f"段落{i}" * 500 for i in range(5)])
        chunks = chunk_article(content, max_tokens=500)
        assert len(chunks) >= 2

    def test_parse_llm_json_object(self):
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_parse_llm_json_markdown(self):
        assert parse_llm_json("```json\n{\"a\": 1}\n```") == {"a": 1}

    def test_parse_llm_json_invalid(self):
        assert parse_llm_json("not json") == {}


class TestDemoNarrativeExtractor:
    def test_policy_angle(self):
        extractor = DemoNarrativeExtractor()
        result = extractor.extract("政策推动电池安全", "监管趋严")
        assert "固态电池安全" in result.main_themes
        assert "政策推动" in result.catalysts
        assert result.sentiment == "乐观"

    def test_supply_demand_angle(self):
        extractor = DemoNarrativeExtractor()
        result = extractor.extract("隔膜供需", "渗透率提升")
        assert "隔膜材料升级" in result.main_themes
        assert "供需" in result.angle or "渗透" in result.angle

    def test_capital_angle(self):
        extractor = DemoNarrativeExtractor()
        result = extractor.extract("资金补涨", "题材扩散")
        assert "低位材料股补涨" in result.main_themes

    def test_default_company_angle(self):
        extractor = DemoNarrativeExtractor()
        result = extractor.extract("无关标题", "无关内容")
        assert result.companies  # 非空

    def test_extracted_narrative_defaults(self):
        n = ExtractedNarrative()
        assert n.main_themes == []
        assert n.sentiment == "中性"
        assert n.background == ""


class TestGetExtractor:
    def test_returns_demo_by_default(self, monkeypatch):
        monkeypatch.setattr("synthesizer.extractors.EXTRACTOR_MODEL", "demo")
        extractor = get_extractor()
        assert extractor.model_name == "demo"

    def test_returns_deepseek(self, monkeypatch):
        monkeypatch.setattr("synthesizer.extractors.EXTRACTOR_MODEL", "deepseek")
        extractor = get_extractor()
        assert extractor.model_name == "deepseek-chat"
