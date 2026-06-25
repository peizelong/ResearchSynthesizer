"""抽取器测试。"""
from __future__ import annotations

from synthesizer.extractors import get_extractor, DemoExtractor
from synthesizer.extractors.prompt_builder import build_extraction_prompt, parse_llm_json


class TestDemoExtractor:
    def test_returns_fixed_claims(self):
        extractor = DemoExtractor()
        claims = extractor.extract("测试标题", "测试正文")
        assert len(claims) == 3

    def test_claims_have_required_fields(self):
        extractor = DemoExtractor()
        claims = extractor.extract("测试标题", "测试正文")
        for c in claims:
            assert c.claim_type
            assert c.subject
            assert c.predicate
            assert c.direction_tag
            assert c.direction_angle in {"policy", "industry", "company", "tech", "macro"}
            assert 0.0 <= c.confidence <= 1.0

    def test_model_name(self):
        assert DemoExtractor().model_name == "demo"


class TestGetExtractor:
    def test_returns_demo_when_configured(self, monkeypatch):
        monkeypatch.setattr("synthesizer.extractors.EXTRACTOR_MODEL", "demo")
        ext = get_extractor()
        assert ext.model_name == "demo"


class TestPromptBuilder:
    def test_build_extraction_prompt_contains_title_and_content(self):
        prompt = build_extraction_prompt("测试标题", "测试正文内容")
        assert "测试标题" in prompt
        assert "测试正文内容" in prompt

    def test_parse_llm_json_valid_object(self):
        raw = '{"claims": [{"claim_type": "direction", "subject": "X", "predicate": "Y"}]}'
        parsed = parse_llm_json(raw)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["subject"] == "X"

    def test_parse_llm_json_valid_array(self):
        raw = '[{"claim_type": "fact", "subject": "A", "predicate": "B"}]'
        parsed = parse_llm_json(raw)
        assert len(parsed) == 1
        assert parsed[0]["subject"] == "A"

    def test_parse_llm_json_with_code_fence(self):
        raw = '```json\n{"claims": []}\n```'
        parsed = parse_llm_json(raw)
        assert parsed == []

    def test_parse_llm_json_empty_returns_empty(self):
        assert parse_llm_json("") == []

    def test_parse_llm_json_invalid_returns_empty(self):
        parsed = parse_llm_json("not a json")
        assert parsed == []
