import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from synthesizer.database import initialize_database
from synthesizer.api import articles_router, research_router, clusters_router, monitor_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Research Synthesizer starting...")
    initialize_database()
    logger.info("Database initialized")
    yield
    logger.info("Research Synthesizer shutting down")


app = FastAPI(
    title="Research Synthesizer",
    description="多源信息研究综合系统 - 关键方向聚类 + 交叉验证 + 多维可靠性评分",
    version="0.1.0",
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
app.include_router(clusters_router)
app.include_router(monitor_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "research-synthesizer", "version": "0.1.0"}
