from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from synthesizer.database import SessionLocal, initialize_database
from synthesizer.models import Article
from synthesizer.repositories import BatchRepository, ThemeRepository
from synthesizer.workflow import run_workflow

logger = logging.getLogger(__name__)


DEFAULT_CONFIG: dict[str, Any] = {
    "interval_seconds": 900,
    "window_hours": 24,
    "article_limit": 120,
    "crawl_enabled": True,
    "crawl_pages": 1,
    "crawl_sections": ["study", "square"],
    "crawl_sorts": ["publish"],
    "fetch_details": True,
}


class RadarController:
    """进程内自动叙事雷达。

    MVP 版使用后台线程持续执行：
    crawl articles -> build rolling article window -> run existing workflow -> store latest report.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._run_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._loop_thread: threading.Thread | None = None
        self._refresh_thread: threading.Thread | None = None

        self._config = dict(DEFAULT_CONFIG)
        self._status = "stopped"
        self._current_stage = "idle"
        self._started_at: str | None = None
        self._stopped_at: str | None = None
        self._last_run_started_at: str | None = None
        self._last_run_finished_at: str | None = None
        self._last_error: str | None = None
        self._last_batch_id: str | None = None
        self._last_report: str = ""
        self._last_result: dict[str, Any] | None = None
        self._logs: list[str] = []
        self._max_logs = 300

    def start(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = self._normalize_config(config or {})
        with self._lock:
            self._config.update(normalized)
            if self._loop_thread is not None and self._loop_thread.is_alive():
                self._wake_event.set()
                return self.status()

            self._stop_event = threading.Event()
            self._wake_event = threading.Event()
            self._status = "running"
            self._current_stage = "starting"
            self._started_at = self._now()
            self._stopped_at = None
            self._last_error = None

            self._loop_thread = threading.Thread(
                target=self._loop,
                name="radar-auto-pipeline",
                daemon=True,
            )
            self._loop_thread.start()

        self._add_log("自动叙事流已启动")
        return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._status = "stopping"
            self._current_stage = "stopping"
            self._stop_event.set()
            self._wake_event.set()
        self._add_log("自动叙事流停止请求已发送")
        return self.status()

    def refresh(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = self._normalize_config(config or {})
        with self._lock:
            self._config.update(normalized)
            if self._loop_thread is not None and self._loop_thread.is_alive():
                self._wake_event.set()
                self._add_log("已请求自动流立即刷新")
                return self.status()

            if self._refresh_thread is not None and self._refresh_thread.is_alive():
                return self.status()

            self._status = "refreshing"
            self._current_stage = "queued"
            self._last_error = None
            self._refresh_thread = threading.Thread(
                target=self._run_once_guarded,
                name="radar-manual-refresh",
                daemon=True,
            )
            self._refresh_thread.start()

        self._add_log("已启动一次性刷新")
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            auto_running = self._loop_thread is not None and self._loop_thread.is_alive()
            refresh_running = self._refresh_thread is not None and self._refresh_thread.is_alive()
            status = self._status
            if status == "stopping" and not auto_running:
                status = "stopped"
            return {
                "status": status,
                "auto_running": auto_running,
                "refresh_running": refresh_running,
                "current_stage": self._current_stage,
                "started_at": self._started_at,
                "stopped_at": self._stopped_at,
                "last_run_started_at": self._last_run_started_at,
                "last_run_finished_at": self._last_run_finished_at,
                "last_error": self._last_error,
                "last_batch_id": self._last_batch_id,
                "last_result": self._last_result,
                "config": dict(self._config),
                "logs": list(self._logs),
            }

    def latest(self) -> dict[str, Any]:
        status = self.status()
        themes = []
        batch = None
        if status.get("last_batch_id"):
            db = SessionLocal()
            try:
                batch = BatchRepository(db).get(status["last_batch_id"])
                themes = ThemeRepository(db).list_by_batch(status["last_batch_id"])
            finally:
                db.close()

        return {
            **status,
            "batch": batch,
            "themes": themes,
            "report": self._last_report,
        }

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._run_once_guarded()
            interval = int(self._config.get("interval_seconds") or DEFAULT_CONFIG["interval_seconds"])
            self._current_stage = "waiting"
            self._wake_event.wait(timeout=max(interval, 1))
            self._wake_event.clear()

        with self._lock:
            self._status = "stopped"
            self._current_stage = "idle"
            self._stopped_at = self._now()
        self._add_log("自动叙事流已停止")

    def _run_once_guarded(self) -> None:
        if not self._run_lock.acquire(blocking=False):
            self._add_log("已有刷新任务在运行，跳过本次触发")
            return

        with self._lock:
            if self._status == "stopped":
                self._status = "refreshing"
            self._last_run_started_at = self._now()
            self._last_error = None

        try:
            result = self._run_once()
            with self._lock:
                if self._loop_thread is not None and self._loop_thread.is_alive() and not self._stop_event.is_set():
                    self._status = "running"
                else:
                    self._status = "stopped"
                    self._stopped_at = self._now()
                self._current_stage = "idle"
                self._last_run_finished_at = self._now()
                self._last_result = result
        except Exception as exc:
            logger.exception("Radar refresh failed")
            with self._lock:
                self._status = "failed" if not self._stop_event.is_set() else "stopped"
                self._current_stage = "failed"
                self._last_error = str(exc)
                self._last_run_finished_at = self._now()
            self._add_log(f"刷新失败：{exc}")
        finally:
            self._run_lock.release()

    def _run_once(self) -> dict[str, Any]:
        initialize_database()
        config = dict(self._config)
        result: dict[str, Any] = {
            "crawled": 0,
            "saved": 0,
            "articles_in_window": 0,
            "themes": 0,
            "narratives": 0,
        }

        db = SessionLocal()
        try:
            if config.get("crawl_enabled", True):
                self._set_stage("crawl", "开始采集文章")
                crawled, saved = self._crawl(db, config)
                result["crawled"] = crawled
                result["saved"] = saved

            self._set_stage("build_window", "构建滚动观察窗口")
            articles = self._select_window_articles(db, config)
            article_ids = [article.id for article in articles]
            result["articles_in_window"] = len(article_ids)
            if not article_ids:
                self._add_log("滚动窗口内没有文章，跳过融合")
                return result

            self._set_stage("fusion", f"运行叙事融合：{len(article_ids)} 篇文章")
            batch = BatchRepository(db).create(
                name=self._batch_name(config),
                description="自动叙事雷达滚动生成",
                article_ids=article_ids,
                source_filter=["jiuyan_web"],
                config={
                    "radar": True,
                    "window_hours": config["window_hours"],
                    "article_limit": config["article_limit"],
                },
                status="pending",
            )
            final_state = run_workflow(
                db=db,
                batch_id=batch.id,
                article_ids=article_ids,
            )
            if article_ids and not final_state.get("narratives") and final_state.get("errors"):
                first_error = str(final_state["errors"][0])
                raise RuntimeError(f"叙事抽取全部失败，未生成有效报告。首个错误：{first_error}")
            themes = final_state.get("merged_themes", [])
            report = final_state.get("report", "")
            with self._lock:
                self._last_batch_id = batch.id
                self._last_report = report

            result["batch_id"] = batch.id
            result["themes"] = len(themes)
            result["narratives"] = len(final_state.get("narratives", []))
            result["errors"] = final_state.get("errors", [])
            self._add_log(f"融合完成：{len(themes)} 个主题，报告 {len(report)} 字符")
            return result
        finally:
            db.close()

    def _crawl(self, db, config: dict[str, Any]) -> tuple[int, int]:
        from synthesizer.crawlers.jiuyan_web import JiuyanWebCrawler

        crawler = JiuyanWebCrawler()
        crawler._stop_event = self._stop_event
        existing_ids = self._existing_source_article_ids(db)
        metas = crawler.crawl_incremental(
            sections=config["crawl_sections"],
            sorts=config["crawl_sorts"],
            fetch_details=config["fetch_details"],
            max_pages=config["crawl_pages"],
            existing_article_ids=existing_ids,
        )
        saved = 0
        if metas and not self._stop_event.is_set():
            saved = crawler.save_articles(metas, db)
        self._add_log(f"采集完成：抓取 {len(metas)} 篇，新增 {saved} 篇")
        return len(metas), saved

    def _existing_source_article_ids(self, db) -> set[str]:
        rows = (
            db.query(Article.source_article_id)
            .filter(Article.source == "jiuyan_web")
            .filter(Article.source_article_id.isnot(None))
            .all()
        )
        return {row[0] for row in rows if row[0]}

    def _select_window_articles(self, db, config: dict[str, Any]) -> list[Article]:
        limit = int(config.get("article_limit") or DEFAULT_CONFIG["article_limit"])
        window_hours = int(config.get("window_hours") or DEFAULT_CONFIG["window_hours"])
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        candidates = (
            db.query(Article)
            .filter(Article.source == "jiuyan_web")
            .order_by(Article.created_at.desc())
            .limit(max(limit * 3, limit))
            .all()
        )
        in_window = [
            article for article in candidates
            if (article.published_at or article.created_at) >= cutoff
        ]
        selected = (in_window or candidates)[:limit]
        self._add_log(f"观察窗口：选入 {len(selected)} 篇文章（近 {window_hours} 小时，最多 {limit} 篇）")
        return selected

    def _batch_name(self, config: dict[str, Any]) -> str:
        window_hours = config.get("window_hours") or DEFAULT_CONFIG["window_hours"]
        return f"自动叙事流 · 近 {window_hours} 小时 · {datetime.now().strftime('%m-%d %H:%M')}"

    def _normalize_config(self, config: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, default in DEFAULT_CONFIG.items():
            value = config.get(key, self._config.get(key, default))
            if key in {"interval_seconds", "window_hours", "article_limit", "crawl_pages"}:
                value = int(value)
            if key in {"crawl_enabled", "fetch_details"}:
                value = bool(value)
            normalized[key] = value

        normalized["interval_seconds"] = max(normalized["interval_seconds"], 60)
        normalized["window_hours"] = max(normalized["window_hours"], 1)
        normalized["article_limit"] = min(max(normalized["article_limit"], 1), 500)
        normalized["crawl_pages"] = min(max(normalized["crawl_pages"], 1), 50)
        normalized["crawl_sections"] = self._normalize_list(normalized["crawl_sections"]) or ["study", "square"]
        normalized["crawl_sorts"] = self._normalize_list(normalized["crawl_sorts"]) or ["publish"]
        return normalized

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    def _set_stage(self, stage: str, message: str) -> None:
        with self._lock:
            self._current_stage = stage
        self._add_log(message)

    def _add_log(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        with self._lock:
            self._logs.append(line)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


radar_controller = RadarController()
