from datetime import datetime
from sqlalchemy import String, Text, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from synthesizer.database import Base


class ArticleNarrative(Base):
    """单篇文章的叙事提取结果。

    由 article_extract_node 调用 NarrativeExtractor 产出，是后续主题融合/
    视角比较/逻辑链重建的输入单元。
    """

    __tablename__ = "article_narratives"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id"))
    # 核心叙事字段
    main_themes: Mapped[list] = mapped_column(JSON, default=list)        # 核心方向 list[str]
    background: Mapped[str | None] = mapped_column(Text, nullable=True)  # 产业背景
    catalysts: Mapped[list] = mapped_column(JSON, default=list)          # 催化因素 list[str]
    industry_segments: Mapped[list] = mapped_column(JSON, default=list)  # 产业链环节 list[str]
    companies: Mapped[list] = mapped_column(JSON, default=list)          # 相关公司 list[str]
    logic_chains: Mapped[list] = mapped_column(JSON, default=list)       # 作者推演逻辑 list[str]
    angle: Mapped[str | None] = mapped_column(String(200), nullable=True)     # 切入角度
    sentiment: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 乐观|中性|谨慎
    time_window: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 时间窗口
    # 元数据
    extractor_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    article: Mapped["Article"] = relationship(back_populates="narratives")


Index("ix_narratives_article_id", ArticleNarrative.article_id)
