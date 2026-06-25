"""规则聚类器 - 基于 direction_tag 字面值分组"""
import re
from collections import defaultdict

from synthesizer.models import Claim


def normalize_tag(tag: str | None) -> str:
    """标准化方向标签：去空格、去标点、转小写"""
    if not tag:
        return ""
    # 去除标点和空白
    cleaned = re.sub(r"[\s\W_]+", "", tag).lower()
    return cleaned


def rule_based_group(claims: list[Claim]) -> dict[str, list[Claim]]:
    """按 direction_tag 标准化值分组"""
    groups: dict[str, list[Claim]] = defaultdict(list)
    for c in claims:
        key = normalize_tag(c.direction_tag)
        groups[key].append(c)
    return dict(groups)


def compute_angle_distribution(claims: list[Claim]) -> dict:
    """计算角度分布"""
    dist: dict[str, int] = defaultdict(int)
    for c in claims:
        angle = c.direction_angle or "unknown"
        dist[angle] += 1
    return dict(dist)


def compute_source_distribution(claims: list[Claim]) -> dict:
    """计算来源分布"""
    dist: dict[str, int] = defaultdict(int)
    for c in claims:
        if c.article:
            dist[c.article.source] += 1
    return dict(dist)


def select_representative(claims: list[Claim]) -> str | None:
    """选择代表性 claim（置信度最高）"""
    if not claims:
        return None
    return max(claims, key=lambda c: c.confidence).id
