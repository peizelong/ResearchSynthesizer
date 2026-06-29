from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExtractedNarrative:
    """单篇文章的叙事提取结果。

    对应 article_extract_node 的产出，字段覆盖：
      核心方向 / 产业背景 / 催化因素 / 产业链环节 /
      相关公司 / 作者推演逻辑 / 切入角度 / 情绪强度 / 时间窗口
    """

    main_themes: list[str] = field(default_factory=list)        # 核心方向
    background: str = ""                                          # 产业背景
    catalysts: list[str] = field(default_factory=list)           # 催化因素
    industry_segments: list[str] = field(default_factory=list)   # 产业链环节
    companies: list[str] = field(default_factory=list)           # 相关公司
    logic_chains: list[str] = field(default_factory=list)        # 作者推演逻辑
    angle: str = ""                                               # 切入角度
    sentiment: str = "中性"                                       # 乐观|中性|谨慎
    time_window: str = ""                                         # 时间窗口


class NarrativeExtractor(ABC):
    """叙事提取器抽象基类。

    实现类：DeepSeekNarrativeExtractor / OllamaNarrativeExtractor / DemoNarrativeExtractor。
    """

    model_name: str

    @abstractmethod
    def extract(self, title: str, content: str) -> ExtractedNarrative:
        """从单篇文章提取结构化叙事。"""
        ...
