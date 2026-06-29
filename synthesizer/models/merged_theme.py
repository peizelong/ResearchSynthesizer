from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from synthesizer.database import Base


class MergedTheme(Base):
    """跨文章融合后的主题。

    由 theme_merge_node 创建骨架（theme_label + sub_directions + article_ids），
    随后 angle_compare_node / logic_chain_node / company_mapping_node 逐步回填：
      - article_angles: dict[article_id -> angle 描述]
      - consensus: 多文共识
      - combined_logic_chain: 综合逻辑链
      - upstream / midstream / downstream: 产业链环节
      - companies: list[{name, direction, article_ids}]
      - divergence_points: list[str]
      - catalysts: list[str]
    """

    __tablename__ = "merged_themes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("research_batches.id"))
    # 融合主题
    theme_label: Mapped[str] = mapped_column(String(200))
    sub_directions: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    article_ids: Mapped[list] = mapped_column(JSON, default=list)     # list[str]
    # 视角比较（angle_compare_node 填充）
    article_angles: Mapped[dict] = mapped_column(JSON, default=dict)  # {article_id: angle}
    # 逻辑链（logic_chain_node 填充）
    consensus: Mapped[str | None] = mapped_column(Text, nullable=True)
    combined_logic_chain: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 产业链映射（company_mapping_node 填充）
    upstream: Mapped[list] = mapped_column(JSON, default=list)        # list[str]
    midstream: Mapped[list] = mapped_column(JSON, default=list)       # list[str]
    downstream: Mapped[list] = mapped_column(JSON, default=list)      # list[str]
    companies: Mapped[list] = mapped_column(JSON, default=list)       # list[{name, direction, article_ids}]
    # 分歧与催化
    divergence_points: Mapped[list] = mapped_column(JSON, default=list)  # list[str]
    catalysts: Mapped[list] = mapped_column(JSON, default=list)          # list[str]
    # 元数据
    member_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


Index("ix_merged_themes_batch_id", MergedTheme.batch_id)
Index("ix_merged_themes_label", MergedTheme.theme_label)
