from __future__ import annotations

from synthesizer.services.llm import (
    DemoLLMClient,
    LLMFusionClient,
    parse_llm_json,
)
from synthesizer.services.prompts import (
    build_cluster_prompt,
    build_direction_merge_prompt,
    build_merge_quality_check_prompt,
    build_report_prompt,
    build_unit_extraction_prompt,
)


class TestParseLlmJson:
    def test_plain_json_object(self):
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_markdown_fenced(self):
        raw = "```json\n{\"a\": 1}\n```"
        assert parse_llm_json(raw) == {"a": 1}

    def test_with_surrounding_text(self):
        raw = '好的，结果如下：\n{"a": 1, "b": [1,2]}\n以上。'
        assert parse_llm_json(raw) == {"a": 1, "b": [1, 2]}

    def test_empty(self):
        assert parse_llm_json("") == {}
        assert parse_llm_json("not json") == {}


class TestDemoLLMClient:
    def test_cluster_response(self):
        client = DemoLLMClient()
        result = LLMFusionClient(client).complete_json("system", "请进行主题聚类")
        assert "clusters" in result
        assert result["clusters"][0]["theme_label"]

    def test_merge_response(self):
        client = DemoLLMClient()
        result = LLMFusionClient(client).complete_json("system", "请进行方向融合")
        assert "theme_label" in result
        assert "sub_directions" in result

    def test_angle_response(self):
        client = DemoLLMClient()
        result = LLMFusionClient(client).complete_json("system", "请做视角比较")
        assert "article_angles" in result

    def test_logic_response(self):
        client = DemoLLMClient()
        result = LLMFusionClient(client).complete_json("system", "请重建逻辑链")
        assert "combined_logic_chain" in result

    def test_company_response(self):
        client = DemoLLMClient()
        result = LLMFusionClient(client).complete_json("system", "请做产业链映射")
        assert "upstream" in result
        assert "companies" in result


class TestPromptBuilders:
    def test_unit_extraction_prompt_contains_units(self):
        prompt = build_unit_extraction_prompt("测试标题", "jiuyan_web", "测试正文")
        assert "测试标题" in prompt
        assert "测试正文" in prompt
        assert "叙事单元" in prompt
        assert "units" in prompt

    def test_direction_merge_prompt_contains_units(self):
        units = [{"unit_id": "u1", "article_id": "a1", "direction": "HBM", "sub_direction": "AI算力"}]
        prompt = build_direction_merge_prompt(units)
        assert "HBM" in prompt
        assert "merged_directions" in prompt

    def test_report_prompt_contains_markdown_structure(self):
        prompt = build_report_prompt([{"direction_name": "电池安全", "sub_directions": ["隔膜"]}])
        assert "多文章方向聚合报告" in prompt
        assert "方向 N" in prompt

    def test_quality_check_prompt_contains_checks(self):
        prompt = build_merge_quality_check_prompt(
            [{"unit_id": "u1", "direction": "电池安全"}],
            [{"direction_name": "电池安全"}],
        )
        assert "has_issue" in prompt
        assert "over_merge" in prompt

    def test_cluster_prompt_compatibility_wrapper(self):
        prompt = build_cluster_prompt([{"unit_id": "u1", "article_id": "a1", "direction": "HBM"}])
        assert "HBM" in prompt
        assert "merged_directions" in prompt
