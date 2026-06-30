from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _company_name(company) -> str:
    if isinstance(company, dict):
        return str(company.get("name") or "").strip()
    return str(company or "").strip()


@dataclass
class ExtractedNarrativeUnit:
    """可独立参与方向聚合的单个叙事单元。"""

    direction: str = ""
    sub_direction: str = ""
    unit_type: str = "other"
    angle: str = ""
    logic_chain: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)
    industry_segments: list[str] = field(default_factory=list)
    companies: list[dict] = field(default_factory=list)
    source_quotes: list[str] = field(default_factory=list)
    importance: str = "core"

    @property
    def main_themes(self) -> list[str]:
        return _dedupe([self.direction, self.sub_direction])

    @property
    def logic_chains(self) -> list[str]:
        return self.logic_chain


@dataclass
class ExtractedNarrative:
    """单篇文章的叙事单元提取结果。

    新结构是一篇文章拆成多个 ExtractedNarrativeUnit。下面保留旧字段，
    是为了兼容已有测试和 DemoExtractor；旧字段会自动折成一个 unit。
    """

    document_type: str = "single_theme_article"
    article_summary: str = ""
    units: list[ExtractedNarrativeUnit] = field(default_factory=list)

    main_themes: list[str] = field(default_factory=list)        # 核心方向
    background: str = ""                                          # 产业背景
    catalysts: list[str] = field(default_factory=list)           # 催化因素
    industry_segments: list[str] = field(default_factory=list)   # 产业链环节
    companies: list = field(default_factory=list)                # 相关公司/公司映射
    logic_chains: list[str] = field(default_factory=list)        # 作者推演逻辑
    angle: str = ""                                               # 切入角度
    sentiment: str = "中性"                                       # 乐观|中性|谨慎
    time_window: str = ""                                         # 时间窗口

    def __post_init__(self) -> None:
        if not self.units and (
            self.main_themes
            or self.catalysts
            or self.industry_segments
            or self.companies
            or self.logic_chains
            or self.angle
        ):
            direction = self.main_themes[0] if self.main_themes else ""
            sub_direction = self.main_themes[1] if len(self.main_themes) > 1 else ""
            company_mentions = []
            for company in self.companies:
                name = _company_name(company)
                if not name:
                    continue
                if isinstance(company, dict):
                    company_mentions.append(company)
                else:
                    company_mentions.append({
                        "name": name,
                        "reason": "",
                        "related_direction": direction,
                        "segment": "",
                        "source_quote": "",
                    })
            self.units = [
                ExtractedNarrativeUnit(
                    direction=direction,
                    sub_direction=sub_direction,
                    unit_type="other",
                    angle=self.angle,
                    logic_chain=self.logic_chains,
                    catalysts=self.catalysts,
                    industry_segments=self.industry_segments,
                    companies=company_mentions,
                    source_quotes=[],
                    importance="core",
                )
            ]

        if self.units:
            if not self.main_themes:
                themes: list[str] = []
                for unit in self.units:
                    themes.extend(unit.main_themes)
                self.main_themes = _dedupe(themes)
            if not self.catalysts:
                self.catalysts = _dedupe([x for unit in self.units for x in unit.catalysts])
            if not self.industry_segments:
                self.industry_segments = _dedupe([x for unit in self.units for x in unit.industry_segments])
            if not self.companies:
                self.companies = _dedupe([
                    _company_name(company)
                    for unit in self.units
                    for company in unit.companies
                    if _company_name(company)
                ])
            if not self.logic_chains:
                chains: list[str] = []
                for unit in self.units:
                    if unit.logic_chain:
                        chains.append(" → ".join(unit.logic_chain))
                self.logic_chains = chains
            if not self.angle and self.units:
                self.angle = self.units[0].angle
        if not self.article_summary:
            self.article_summary = self.background

    def as_units(self) -> list[ExtractedNarrativeUnit]:
        return self.units


class NarrativeExtractor(ABC):
    """叙事提取器抽象基类。

    实现类：DeepSeekNarrativeExtractor / OllamaNarrativeExtractor / DemoNarrativeExtractor。
    """

    model_name: str

    @abstractmethod
    def extract(self, title: str, content: str, source: str = "") -> ExtractedNarrative:
        """从单篇文章提取结构化叙事单元。"""
        ...
