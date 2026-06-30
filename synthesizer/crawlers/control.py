"""爬虫控制器：管理 JiuyanWebCrawler 的启停与状态。"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# 支持的爬虫源与模式
CRAWLER_SOURCES = {"jiuyan_web"}
JIUYAN_WEB_MODES = {"incremental", "full"}

# 状态枚举
STATUS_STOPPED = "stopped"
STATUS_RUNNING = "running"
STATUS_STOPPING = "stopping"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class CrawlerAlreadyRunningError(RuntimeError):
    """爬虫已在运行时再次启动抛出。"""
    pass


class CrawlerController:
    """管理 JiuyanWebCrawler 的启停、状态查询与日志收集。

    单例实例 crawler_controller 可被外部直接使用。
    爬虫在独立 daemon 线程中运行，结果通过 last_result 保存。
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._crawler: Any | None = None
        self._status: str = STATUS_STOPPED
        self._started_at: str | None = None
        self._finished_at: str | None = None
        self._stop_requested_at: str | None = None
        self._last_config: dict[str, Any] = {}
        self._last_error: str | None = None
        self._last_result: dict[str, Any] | None = None
        self._logs: list[str] = []
        self._max_logs = 200

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def start(self, config: dict) -> dict:
        """启动爬虫线程。

        config 可含: source/mode/pages/sections/sorts/fetch_details。
        返回当前状态字典。
        """
        normalized = self._normalize_config(config)
        with self._lock:
            if self._is_running_locked():
                raise CrawlerAlreadyRunningError(
                    f"{normalized['source']} crawler is already running"
                )

            self._stop_event = threading.Event()
            self._crawler = None
            self._status = STATUS_RUNNING
            self._started_at = self._now()
            self._finished_at = None
            self._stop_requested_at = None
            self._last_config = normalized
            self._last_error = None
            self._last_result = None
            self._logs = []

            self._thread = threading.Thread(
                target=self._run_wrapper,
                args=(normalized,),
                name=f"{normalized['source']}-crawler",
                daemon=True,
            )
            self._thread.start()

        self.add_log(
            f"Crawler started: source={normalized['source']}, "
            f"mode={normalized['mode']}, pages={normalized['pages']}"
        )
        return self.get_status(normalized["source"])

    def stop(self, source: str | None = None, timeout_seconds: float = 5) -> dict:
        """请求停止爬虫线程并等待其退出。"""
        with self._lock:
            if not self._is_running_locked():
                return self._status_locked()

            self._status = STATUS_STOPPING
            self._stop_requested_at = self._stop_requested_at or self._now()
            self._stop_event.set()
            if self._crawler is not None and hasattr(self._crawler, "_stop_event"):
                self._crawler._stop_event.set()
            thread = self._thread
            self.add_log("Stop requested")

        if thread is not None:
            thread.join(timeout=timeout_seconds)

        with self._lock:
            return self._status_locked()

    def get_status(self, source: str | None = None) -> dict:
        """返回指定爬虫的状态字典。"""
        with self._lock:
            return self._status_locked()

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    def add_log(self, message: str) -> None:
        """追加一条日志到环形缓冲（最多 _max_logs 条）。"""
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self._lock:
            self._logs.append(line)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]

    # ------------------------------------------------------------------
    # 线程执行
    # ------------------------------------------------------------------

    def _run_wrapper(self, config: dict[str, Any]) -> None:
        final_status = STATUS_COMPLETED
        result: dict[str, Any] = {}
        try:
            result = self._run_crawler(config)
            if self._stop_event.is_set():
                final_status = STATUS_STOPPED
        except Exception as exc:
            final_status = STATUS_FAILED
            with self._lock:
                self._last_error = str(exc)
            self.add_log(f"Error: {exc}")
            logger.exception("Crawler run failed")
        finally:
            with self._lock:
                self._status = final_status
                self._finished_at = self._now()
                self._crawler = None
                self._last_result = result or None

    def _run_crawler(self, config: dict[str, Any]) -> dict[str, Any]:
        """执行爬虫：爬取列表 → 入库。"""
        from synthesizer.crawlers.jiuyan_web import JiuyanWebCrawler
        from synthesizer.database import SessionLocal, initialize_database
        from synthesizer.models import Article

        source = config["source"]
        if source != "jiuyan_web":
            raise ValueError(f"Unsupported crawler source: {source}")

        # 确保表已创建
        initialize_database()

        crawler = JiuyanWebCrawler()
        crawler._stop_event = self._stop_event
        with self._lock:
            self._crawler = crawler

        mode = config["mode"]
        self.add_log(f"JiuyanWeb crawler running: mode={mode}")

        saved = 0
        db = SessionLocal()
        try:
            existing_ids = set()
            if mode == "incremental":
                rows = (
                    db.query(Article.source_article_id)
                    .filter(Article.source == source)
                    .filter(Article.source_article_id.isnot(None))
                    .all()
                )
                existing_ids = {row[0] for row in rows if row[0]}

            metas = crawler.crawl_incremental(
                sections=config["sections"],
                sorts=config["sorts"],
                fetch_details=config["fetch_details"],
                max_pages=config["pages"],
                existing_article_ids=existing_ids,
            )
            self.add_log(f"Crawled {len(metas)} new articles")

            if metas and not self._stop_event.is_set():
                saved = crawler.save_articles(metas, db)
        finally:
            db.close()
        self.add_log(f"Saved {saved} new articles to DB")

        return {
            "source": source,
            "mode": mode,
            "total": len(metas),
            "saved": saved,
            "stopped": self._stop_event.is_set(),
        }

    # ------------------------------------------------------------------
    # 配置归一化
    # ------------------------------------------------------------------

    def _normalize_config(self, config: dict) -> dict[str, Any]:
        source = str(config.get("source") or "jiuyan_web")
        if source not in CRAWLER_SOURCES:
            raise ValueError(f"Unsupported crawler source: {source}")

        mode = str(config.get("mode") or "incremental")
        valid_modes = JIUYAN_WEB_MODES if source == "jiuyan_web" else set()
        if mode not in valid_modes:
            raise ValueError(f"Unsupported {source} crawler mode: {mode}")

        pages = int(config.get("pages") or 2)
        if pages < 1 or pages > 50:
            raise ValueError("Crawler pages must be between 1 and 50")

        sections = self._normalize_list(config.get("sections")) or ["study", "square"]
        for s in sections:
            if s not in {"study", "square"}:
                raise ValueError(f"Invalid section: {s}")

        sorts = self._normalize_list(config.get("sorts")) or ["publish"]
        for s in sorts:
            if s not in {"publish", "hot"}:
                raise ValueError(f"Invalid sort: {s}")

        return {
            "source": source,
            "mode": mode,
            "pages": pages,
            "sections": sections,
            "sorts": sorts,
            "fetch_details": bool(config.get("fetch_details", True)),
        }

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise ValueError("sections/sorts must be a list or comma-separated string")

    # ------------------------------------------------------------------
    # 内部状态
    # ------------------------------------------------------------------

    def _is_running_locked(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _status_locked(self) -> dict[str, Any]:
        is_running = self._is_running_locked()
        status = self._status
        if not is_running and status in (STATUS_RUNNING, STATUS_STOPPING):
            status = STATUS_STOPPED
        return {
            "source": self._last_config.get("source", "jiuyan_web"),
            "status": status,
            "is_running": is_running,
            "started_at": self._started_at,
            "finished_at": self._finished_at,
            "stop_requested_at": self._stop_requested_at,
            "last_error": self._last_error,
            "last_result": self._last_result,
            "mode": self._last_config.get("mode"),
            "pages": self._last_config.get("pages"),
            "sections": self._last_config.get("sections"),
            "sorts": self._last_config.get("sorts"),
            "fetch_details": self._last_config.get("fetch_details"),
            "logs": list(self._logs),
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


# 单例实例
crawler_controller = CrawlerController()
