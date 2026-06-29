from __future__ import annotations

from synthesizer.services.llm import (
    DemoLLMClient,
    LLMFusionClient,
    parse_llm_json,
)
from synthesizer.services.prompts import (
    build_angle_prompt,
    build_cluster_prompt,
    build_company_prompt,
    build_logic_prompt,
    build_merge_prompt,
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
    def test_cluster_prompt_contains_themes(self):
        prompt = build_cluster_prompt([{"article_id": "a1", "main_themes": ["HBM", "AI算力"]}])
        assert "HBM" in prompt
        assert "clusters" in prompt

    def test_merge_prompt_contains_label(self):
        prompt = build_merge_prompt({"theme_label": "电池安全", "sub_directions": ["隔膜"]})
        assert "电池安全" in prompt
        assert "consensus" in prompt

    def test_angle_prompt_contains_articles(self):
        prompt = build_angle_prompt("电池安全", [{"article_id": "a1", "angle": "政策角度"}])
        assert "电池安全" in prompt
        assert "article_angles" in prompt

    def test_logic_prompt_contains_label(self):
        prompt = build_logic_prompt("电池安全", [{"article_id": "a1", "logic_chains": ["x → y"]}])
        assert "combined_logic_chain" in prompt

    def test_company_prompt_contains_companies(self):
        prompt = build_company_prompt("电池安全", [{"article_id": "a1", "companies": ["公司A"]}])
        assert "upstream" in prompt
        assert "公司A" in prompt
