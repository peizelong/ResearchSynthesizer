from __future__ import annotations

from synthesizer.extractors.base import ExtractedNarrative, NarrativeExtractor


class DemoNarrativeExtractor(NarrativeExtractor):
    """测试用叙事提取器 - 不调用任何 LLM，返回固定叙事。

    返回电池安全材料升级方向的示例叙事，便于测试主题融合流程。
    """

    model_name = "demo"

    def extract(self, title: str, content: str, source: str = "") -> ExtractedNarrative:
        # 根据标题/内容关键词返回不同视角，模拟多文章多角度场景
        text = (title or "") + (content or "")

        if "政策" in text or "监管" in text:
            return ExtractedNarrative(
                main_themes=["固态电池安全", "电池安全监管"],
                background="近期电池安全事故频发，监管层加强安全要求。",
                catalysts=["政策推动", "产业事故"],
                industry_segments=["隔膜", "阻燃材料"],
                companies=["公司A", "公司B"],
                logic_chains=["安全事故频发 → 监管趋严 → 高性能材料需求提升"],
                angle="从政策和安全监管角度切入，强调安全事故后监管趋严。",
                sentiment="乐观",
                time_window="2026年下半年",
            )

        if "供需" in text or "渗透" in text:
            return ExtractedNarrative(
                main_themes=["隔膜材料升级", "高性能材料渗透率提升"],
                background="电池能量密度提升推动材料体系升级。",
                catalysts=["新技术量产", "渗透率提升"],
                industry_segments=["隔膜", "涂覆材料"],
                companies=["公司A", "公司C"],
                logic_chains=["能量密度提升 → 高性能材料渗透率提升 → 相关公司受益"],
                angle="从产业链供需角度切入，强调高性能材料渗透率提升。",
                sentiment="乐观",
                time_window="2026-2027年",
            )

        if "资金" in text or "补涨" in text or "题材" in text:
            return ExtractedNarrative(
                main_themes=["电池热失控防护", "低位材料股补涨"],
                background="市场资金开始扩散到低位安全材料环节。",
                catalysts=["资金扩散", "题材轮动"],
                industry_segments=["热管理", "防护结构"],
                companies=["公司B", "公司D"],
                logic_chains=["主线扩散 → 低位材料股被重新定价 → 补涨"],
                angle="从资金审美和题材扩散角度切入，强调低位材料股可能补涨。",
                sentiment="乐观",
                time_window="短期",
            )

        # 默认视角：公司映射
        return ExtractedNarrative(
            main_themes=["固态电池安全", "电池安全材料升级"],
            background="电池安全相关上市公司梳理。",
            catalysts=["产业事故", "新技术量产"],
            industry_segments=["隔膜", "阻燃材料", "热管理"],
            companies=["公司A", "公司B", "公司C", "公司D"],
            logic_chains=["安全要求提升 → 多环节材料需求提升 → 相关上市公司受益"],
            angle="从公司映射角度切入，列举相关上市公司。",
            sentiment="中性",
            time_window="2026年",
        )
