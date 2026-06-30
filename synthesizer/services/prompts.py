"""分层叙事融合 Prompt。

核心原则：
    把文章拆成可以独立参与方向聚合的叙事单元；
    再把多个叙事单元做同义合并、父子整理和方向去重；
    最后输出一份综合报告。
"""
from __future__ import annotations

import json


# ============================================================
# Prompt 1: 单文叙事单元抽取
# ============================================================
UNIT_EXTRACTION_SYSTEM = """你是投研文章叙事单元抽取器。

你的任务是从一篇投研文章、社区纪要、产业链梳理、舆情合集或公告整理中，抽取可以独立参与后续方向聚合的“叙事单元”。

重要原则：
1. 不要判断真假。
2. 不要做投资建议。
3. 不要给可靠性评分。
4. 不要做外部证据验证。
5. 只提取文章中明确出现的方向、逻辑、催化、公司和产业链环节。
6. 如果一篇文章包含多个方向，必须拆成多个叙事单元。
7. 一个叙事单元只能表达一个核心方向，不要把多个方向混在一起。
8. 公司必须绑定到对应方向，不能只输出公司名列表。
9. 每个叙事单元都要保留原文短句作为 source_quotes，便于后续回看。
10. 输出必须是合法 JSON，不要输出 Markdown，不要输出解释文字。
"""


UNIT_EXTRACTION_USER_TEMPLATE = """请从下面文章中抽取叙事单元。

# 文章信息

标题：
{title}

来源：
{source}

正文：
{content}

# 抽取要求

请先判断文章类型 document_type：

可选值：
- single_theme_article：单主题文章
- multi_topic_digest：多主题舆情合集
- sector_deep_dive：行业深度梳理
- company_mapping：公司映射型文章
- announcement_digest：公告整理
- mixed：混合型文章

然后抽取 units。

每个 unit 是一个可以独立参与后续方向聚合的叙事单元。

拆分规则：
1. 如果文章同时讲半导体设备、先进封装、PCB、医药、公告等多个方向，必须拆成多个 unit。
2. 如果几个段落虽然同属一个大行业，但逻辑链不同，也要拆开。
3. 如果只是同一个方向的不同表述，可以放在同一个 unit 里。
4. 如果某个方向只是顺带提及，importance 标为 mention。
5. 如果某个方向是文章核心，importance 标为 core。
6. 如果某个方向是辅助展开，importance 标为 secondary。

字段说明：

- direction：该单元的方向名称，短词组。
- sub_direction：更细分的方向。
- unit_type：方向类型。
  可选值：
  macro_event / industry_cycle / technology_chain / price_hike / bottleneck / capacity_expansion / company_mapping / policy_catalyst / announcement / other
- angle：文章对该方向的切入角度。
- logic_chain：按因果顺序拆成数组。
- catalysts：催化因素。
- industry_segments：产业链环节。
- companies：公司映射，必须说明公司为什么出现在这个方向里。
- source_quotes：原文关键短句，最多 3 条，每条尽量短。
- importance：core / secondary / mention。

# 输出 JSON 格式

{{
  "document_type": "single_theme_article | multi_topic_digest | sector_deep_dive | company_mapping | announcement_digest | mixed",
  "article_summary": "用一句话概括文章整体内容",
  "units": [
    {{
      "direction": "方向名称",
      "sub_direction": "细分方向，可为空",
      "unit_type": "macro_event | industry_cycle | technology_chain | price_hike | bottleneck | capacity_expansion | company_mapping | policy_catalyst | announcement | other",
      "angle": "切入角度",
      "logic_chain": ["原因", "变化", "影响", "受益环节"],
      "catalysts": ["催化1", "催化2"],
      "industry_segments": ["环节1", "环节2"],
      "companies": [
        {{
          "name": "公司名",
          "reason": "文章中该公司和本方向的关系",
          "related_direction": "对应方向",
          "segment": "对应产业链环节",
          "source_quote": "对应原文短句"
        }}
      ],
      "source_quotes": ["原文关键句1", "原文关键句2"],
      "importance": "core | secondary | mention"
    }}
  ]
}}

# 约束

1. 不要编造文章没有提到的公司。
2. 不要把不同方向的公司混到一起。
3. 不要把“同属半导体”但逻辑不同的方向强行合并。
4. 不要输出空泛方向，例如“科技成长”“产业升级”。
5. direction 必须具体，例如“半导体 Capex 超级周期”“功率半导体涨价”“AI PCB 上游材料涨价”。
6. 如果文章是多主题合集，units 数量可以较多。
7. 如果正文信息不足，输出空 units，并说明 article_summary 为“正文信息不足”。
8. 只输出 JSON。
"""


def build_unit_extraction_prompt(title: str, source: str = "", content: str = "") -> str:
    return UNIT_EXTRACTION_USER_TEMPLATE.format(
        title=title or "",
        source=source or "",
        content=content or "",
    )


# ============================================================
# Prompt 2: 多文方向归一与去重
# ============================================================
DIRECTION_MERGE_SYSTEM = """你是投研方向归一与去重专家。

你的任务是对多篇文章中抽取出的 NarrativeUnit 进行方向归并、同义去重、父子关系整理，并输出结构化的 MergedDirection。

重要原则：
1. 不要判断真假。
2. 不要做投资建议。
3. 不要补充外部知识。
4. 只能基于输入的 NarrativeUnit 进行归并。
5. 叫法不同但产业逻辑相同的方向，要合并。
6. 属于同一主方向下的细分环节，要归到同一个主方向，但必须保留子方向。
7. 只是同属一个大行业但逻辑链不同的方向，不要强行合并。
8. 公司名重复不等于方向相同。
9. 催化事件相同但受益环节不同，可以归为同一事件下的不同子方向。
10. 输出必须是合法 JSON，不要输出 Markdown，不要输出解释文字。
"""


DIRECTION_MERGE_USER_TEMPLATE = """下面是一组从多篇文章中抽取出的 NarrativeUnit。

请你对它们进行方向归一、同义去重、父子方向整理，输出去重后的 MergedDirection 列表。

# 输入 NarrativeUnit 列表

{narrative_units_json}

# 去重规则

## 一、应该合并的情况

1. 名称不同但讲的是同一条产业逻辑：
   例如：
   - 半导体Capex
   - 晶圆厂扩产
   - WFE景气周期
   - 前道设备超级周期
   可以合并为：半导体 Capex / 设备超级周期

2. 同一个方向的不同叫法：
   例如：
   - CoWoS-L
   - 先进封装
   - 2.5D封装
   可以归入：先进封装 / CoWoS

3. 同一个事件下的不同表述：
   例如：
   - 三星投资
   - 韩国半导体投资
   - SK海力士扩产
   可以归入：韩国半导体超大规模投资

## 二、不要强行合并的情况

1. 同属半导体，但逻辑链不同：
   - 半导体设备超级周期
   - 功率半导体涨价
   - 硅片涨价
   这些不能粗暴合并成“半导体”。

2. 同属涨价线，但产品和驱动不同：
   - PCB材料涨价
   - 电容涨价
   - 功率半导体涨价
   可以放在 related_directions，但不要合并成一个方向。

3. 公司重复但方向不同：
   同一家公司可能同时属于材料、设备、先进封装，不要仅因公司相同就合并。

# 输出字段

- direction_name：合并后的标准方向名。
- aliases：被合并进来的原始叫法。
- sub_directions：保留的细分方向。
- source_unit_ids：来源 unit ID。
- source_article_ids：来源文章 ID。
- consensus：多篇内容共同表达的共识。
- different_angles：不同文章或不同 unit 的切入角度。
- combined_logic_chain：综合后的逻辑链，按因果顺序输出数组。
- catalysts：合并后的催化因素。
- industry_segments：合并后的产业链环节。
- companies：方向下的公司映射，去重后保留 reason。
- related_directions：相关但不合并的方向。
- merge_reason：为什么这些 unit 被合并。

# 输出 JSON 格式

{{
  "merged_directions": [
    {{
      "direction_name": "标准方向名",
      "aliases": ["原始叫法1", "原始叫法2"],
      "sub_directions": ["子方向1", "子方向2"],
      "source_unit_ids": ["unit_id_1", "unit_id_2"],
      "source_article_ids": ["article_id_1", "article_id_2"],
      "consensus": "多文共识",
      "different_angles": ["角度1", "角度2"],
      "combined_logic_chain": ["原因", "变化", "影响", "受益环节"],
      "catalysts": ["催化1", "催化2"],
      "industry_segments": ["环节1", "环节2"],
      "companies": [
        {{
          "name": "公司名",
          "reasons": ["原因1", "原因2"],
          "segments": ["环节1", "环节2"],
          "source_unit_ids": ["unit_id_1"]
        }}
      ],
      "related_directions": ["相关但不合并的方向"],
      "merge_reason": "合并理由"
    }}
  ],
  "not_merged": [
    {{
      "direction_a": "方向A",
      "direction_b": "方向B",
      "reason": "为什么相关但不合并"
    }}
  ]
}}

# 约束

1. 不要遗漏输入中出现的重要方向。
2. 不要为了减少数量而过度合并。
3. 不要生成输入中不存在的新方向。
4. direction_name 要具体，不要过泛。
5. aliases 必须来自输入。
6. source_unit_ids 必须准确保留。
7. 只输出 JSON。
"""


def build_direction_merge_prompt(narrative_units: list[dict]) -> str:
    return DIRECTION_MERGE_USER_TEMPLATE.format(
        narrative_units_json=json.dumps(narrative_units, ensure_ascii=False, indent=2)
    )


# ============================================================
# Prompt 3: 综合报告生成
# ============================================================
REPORT_SYSTEM = """你是投研方向聚合报告撰写器。

你的任务是基于已经去重后的 MergedDirection 列表，生成一份结构清晰的多文章方向聚合报告。

重要原则：
1. 不要重新判断方向是否合并。
2. 不要新增输入中没有的方向。
3. 不要做投资建议。
4. 不要判断真假。
5. 不要做外部证据验证。
6. 重点展示：去重后的方向、不同文章的角度、综合逻辑链、产业链环节、反复出现公司。
7. 报告要帮助读者快速看懂：这一批文章到底共同指向哪些方向，哪些是重复共识，哪些是差异补充。
8. 输出 Markdown。
"""


REPORT_USER_TEMPLATE = """请根据下面的 MergedDirection 列表，生成一份《多文章方向聚合报告》。

# 输入

{merged_directions_json}

# 报告结构

请严格按以下结构输出：

# 多文章方向聚合报告

## 一、核心结论

用 3-5 条 bullet 总结本批文章聚合后的主要结论。

## 二、去重后的方向总览

用表格展示：

| 序号 | 聚合方向 | 子方向 | 来源文章数 | 代表公司 | 核心逻辑 |
|---|---|---|---|---|---|

要求：
- 来源文章数来自 source_article_ids 去重数量。
- 代表公司最多列 6 个。
- 核心逻辑用一句话。

## 三、核心方向详解

对每个 MergedDirection 单独成节。

每个方向按以下结构写：

### 方向 N：{{direction_name}}

#### 1. 合并后的方向描述
说明这个方向整体讲什么。

#### 2. 合并了哪些相近叫法
列出 aliases。

#### 3. 多文共识
写 consensus。

#### 4. 不同切入角度
列出 different_angles，并说明这些角度如何互补。

#### 5. 综合逻辑链
用箭头形式表达 combined_logic_chain。

#### 6. 涉及产业链环节
列出 industry_segments，并尽量按上游/中游/下游或材料/设备/制造/封装分类。

#### 7. 反复出现公司
列出 companies，并说明每家公司对应的环节或被提及原因。

#### 8. 需要保留的子方向
列出 sub_directions，说明哪些是主方向下的细分机会。

## 四、相关但不应合并的方向

根据 not_merged 或 related_directions，说明哪些方向容易混淆但应该分开展示。

## 五、文章覆盖情况

按 source_article_ids 总结每篇文章贡献了哪些方向。

# 写作要求

1. 不要写“本文认为可以买入”等投资建议。
2. 不要使用“确定受益”“必然上涨”等确定性表述。
3. 可以使用“文章共同指向”“材料中反复出现”“多篇内容均提到”。
4. 语言要像投研整理报告，不要像新闻稿。
5. 方向名称要具体。
6. 不要遗漏 MergedDirection 中的重要字段。
7. 输出 Markdown。
"""


def build_report_prompt(merged_directions: list[dict], not_merged: list[dict] | None = None) -> str:
    payload = {
        "merged_directions": merged_directions,
        "not_merged": not_merged or [],
    }
    return REPORT_USER_TEMPLATE.format(
        merged_directions_json=json.dumps(payload, ensure_ascii=False, indent=2)
    )


# ============================================================
# Prompt 4: 结果质检 / 修正
# ============================================================
MERGE_QUALITY_CHECK_SYSTEM = """你是投研方向聚合结果质检器。

你的任务是检查 NarrativeUnit 到 MergedDirection 的聚合结果是否存在问题。

只做质检和修正建议，不做外部验证，不判断真假，不给投资建议。
"""


MERGE_QUALITY_CHECK_USER_TEMPLATE = """请检查下面的方向聚合结果。

# 原始 NarrativeUnit

{narrative_units_json}

# 已生成 MergedDirection

{merged_directions_json}

# 检查任务

请检查是否存在以下问题：

1. 漏掉重要方向。
2. 把不该合并的方向强行合并。
3. 同义方向没有合并。
4. 父子方向关系处理错误。
5. 公司被放到了错误方向下。
6. 逻辑链混合了多个方向。
7. aliases 中出现了输入不存在的叫法。
8. source_unit_ids 或 source_article_ids 缺失。

# 输出 JSON

{{
  "has_issue": true,
  "issues": [
    {{
      "type": "missing_direction | over_merge | under_merge | wrong_company_mapping | wrong_logic_chain | source_id_missing | other",
      "description": "问题描述",
      "affected_direction": "相关方向",
      "suggested_fix": "修正建议"
    }}
  ],
  "corrected_merged_directions": [
    {{
      "direction_name": "修正后的方向名",
      "aliases": [],
      "sub_directions": [],
      "source_unit_ids": [],
      "source_article_ids": [],
      "consensus": "",
      "different_angles": [],
      "combined_logic_chain": [],
      "catalysts": [],
      "industry_segments": [],
      "companies": [],
      "related_directions": [],
      "merge_reason": ""
    }}
  ]
}}

# 约束

1. 如果没有明显问题，has_issue=false，issues=[]。
2. 不要新增原始 NarrativeUnit 中没有的信息。
3. 不要做外部验证。
4. 只输出 JSON。
"""


def build_merge_quality_check_prompt(narrative_units: list[dict], merged_directions: list[dict]) -> str:
    return MERGE_QUALITY_CHECK_USER_TEMPLATE.format(
        narrative_units_json=json.dumps(narrative_units, ensure_ascii=False, indent=2),
        merged_directions_json=json.dumps(merged_directions, ensure_ascii=False, indent=2),
    )


# ============================================================
# Compatibility wrappers for old node names/tests
# ============================================================
CLUSTER_SYSTEM = DIRECTION_MERGE_SYSTEM
MERGE_SYSTEM = DIRECTION_MERGE_SYSTEM
ANGLE_SYSTEM = "兼容旧节点：视角已经由 MergedDirection.different_angles 承载。"
LOGIC_SYSTEM = "兼容旧节点：逻辑链已经由 MergedDirection.combined_logic_chain 承载。"
COMPANY_SYSTEM = "兼容旧节点：公司映射已经由 MergedDirection.companies 承载。"


def build_cluster_prompt(article_themes: list[dict]) -> str:
    """兼容旧函数名；现在构建方向归一与去重 prompt。"""
    return build_direction_merge_prompt(article_themes)


def build_merge_prompt(cluster: dict) -> str:
    """兼容旧函数名；新流程不再对单个 cluster 二次调用 LLM。"""
    return json.dumps(cluster, ensure_ascii=False, indent=2)


def build_angle_prompt(theme_label: str, articles: list[dict]) -> str:
    return json.dumps({"theme_label": theme_label, "articles": articles}, ensure_ascii=False, indent=2)


def build_logic_prompt(theme_label: str, articles: list[dict]) -> str:
    return json.dumps({"theme_label": theme_label, "articles": articles}, ensure_ascii=False, indent=2)


def build_company_prompt(theme_label: str, articles: list[dict]) -> str:
    return json.dumps({"theme_label": theme_label, "articles": articles}, ensure_ascii=False, indent=2)
