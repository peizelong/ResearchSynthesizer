from __future__ import annotations

from synthesizer.extractors.base import ClaimExtractor, ExtractedClaim


class DemoExtractor(ClaimExtractor):
    """测试用抽取器，不调用任何 LLM，返回固定的示例论断。"""

    model_name = "demo"

    def extract(self, title: str, content: str) -> list[ExtractedClaim]:
        return [
            ExtractedClaim(
                claim_type="direction",
                subject="HBM存储",
                predicate="供应紧张",
                direction_tag="HBM供应紧张",
                direction_angle="industry",
                evidence_text="HBM存储供应紧张，价格上涨。",
                confidence=0.8,
            ),
            ExtractedClaim(
                claim_type="direction",
                subject="AI算力",
                predicate="需求增长",
                direction_tag="AI算力需求增长",
                direction_angle="industry",
                evidence_text="AI算力需求持续增长。",
                confidence=0.75,
            ),
            ExtractedClaim(
                claim_type="fact",
                subject="半导体",
                predicate="国产替代加速",
                direction_tag="半导体国产替代",
                direction_angle="policy",
                evidence_text="政策推动半导体国产替代加速。",
                confidence=0.7,
            ),
        ]
