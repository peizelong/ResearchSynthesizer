# Narrative Synthesizer Refactor Snapshot

## Goal

将系统收敛为“投研叙事融合器”：多篇文章输入后，提取方向、合并重合主题、保留差异视角、重建逻辑链，并输出结构化投研摘要。

## Target Workflow

```text
article_extract
  → theme_cluster
  → theme_merge
  → angle_compare
  → logic_chain
  → company_mapping
  → report
```

## Core Models

- `Article`
- `ArticleNarrative`
- `MergedTheme`
- `ResearchBatch`

## Core Nodes

- `article_extract_node`: 单文叙事提取
- `theme_cluster_node`: 多文主题聚类
- `theme_merge_node`: 统一方向融合
- `angle_compare_node`: 保留不同文章切入角度
- `logic_chain_node`: 重建综合逻辑链
- `company_mapping_node`: 产业链与公司映射
- `report_node`: 生成 Markdown 报告

## MVP Boundaries

第一版只做叙事综合，不做事实判定。输出关注：

- 共同关注方向
- 多文共识
- 差异视角
- 综合逻辑链
- 产业链环节
- 公司映射
- 催化因素

## Verification

- Backend tests: `pytest tests/ -v --tb=short`
- Frontend build: `npm run build` in `frontend/`
