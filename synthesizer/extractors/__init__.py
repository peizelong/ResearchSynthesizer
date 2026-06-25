from __future__ import annotations

from synthesizer.config import EXTRACTOR_MODEL
from synthesizer.extractors.base import ClaimExtractor, ExtractedClaim
from synthesizer.extractors.deepseek_extractor import DeepSeekExtractor
from synthesizer.extractors.demo_extractor import DemoExtractor


def get_extractor() -> ClaimExtractor:
    """根据配置 EXTRACTOR_MODEL 返回对应的抽取器实例。"""
    name = (EXTRACTOR_MODEL or "").strip().lower()
    if name == "deepseek":
        return DeepSeekExtractor()
    if name == "demo":
        return DemoExtractor()
    return DemoExtractor()


__all__ = [
    "get_extractor",
    "DeepSeekExtractor",
    "DemoExtractor",
    "ClaimExtractor",
    "ExtractedClaim",
]
