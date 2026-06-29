from synthesizer.config import EXTRACTOR_MODEL
from synthesizer.extractors.base import ExtractedNarrative, NarrativeExtractor
from synthesizer.extractors.deepseek_extractor import DeepSeekNarrativeExtractor
from synthesizer.extractors.demo_extractor import DemoNarrativeExtractor
from synthesizer.extractors.ollama_extractor import OllamaNarrativeExtractor


def get_extractor() -> NarrativeExtractor:
    """根据配置 EXTRACTOR_MODEL 返回对应的叙事提取器实例。"""
    name = (EXTRACTOR_MODEL or "").strip().lower()
    if name == "deepseek":
        return DeepSeekNarrativeExtractor()
    if name == "ollama":
        return OllamaNarrativeExtractor()
    if name == "demo":
        return DemoNarrativeExtractor()
    return DemoNarrativeExtractor()


__all__ = [
    "get_extractor",
    "DeepSeekNarrativeExtractor",
    "DemoNarrativeExtractor",
    "OllamaNarrativeExtractor",
    "NarrativeExtractor",
    "ExtractedNarrative",
]
