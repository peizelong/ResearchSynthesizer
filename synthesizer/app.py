import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from synthesizer.database import initialize_database
from synthesizer.api import articles_router, research_router, themes_router, monitor_router, radar_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Narrative Synthesizer starting...")
    initialize_database()
    logger.info("Database initialized")
    yield
    logger.info("Narrative Synthesizer shutting down")


app = FastAPI(
    title="Narrative Synthesizer",
    description="投研叙事融合系统 - 多文章方向提取 + 主题融合 + 视角比较 + 逻辑链重建 + 产业链映射",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(articles_router)
app.include_router(research_router)
app.include_router(themes_router)
app.include_router(monitor_router)
app.include_router(radar_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "narrative-synthesizer", "version": "0.2.0"}
