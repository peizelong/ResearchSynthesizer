import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from synthesizer.config import DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def initialize_database(bind=engine) -> None:
    """初始化数据库：create_all 模式（Phase 1 不用 Alembic）。
    若为 SQLite 且数据目录不存在，则自动创建。
    """
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = DATABASE_URL.replace("sqlite:///", "", 1)
        # 仅处理相对/绝对文件路径，跳过 :memory:
        if db_path and db_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
                logger.info(f"Created data directory: {parent}")
    Base.metadata.create_all(bind=bind)
    logger.info("Database initialized with create_all")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
