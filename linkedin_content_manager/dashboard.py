"""Local web dashboard and API for the content pipeline."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from linkedin_content_manager.config import ConfigurationError, Settings, load_settings
from linkedin_content_manager.pipeline import STAGE_NAMES, run_pipeline


logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).with_name("static")

app = FastAPI(title="LinkedIn Content Desk", docs_url=None, redoc_url=None)
app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

_runs: dict[str, dict[str, Any]] = {}
_runs_lock = threading.RLock()


class RunRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Topic must contain at least 3 non-whitespace characters")
        return normalized


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execute_run(run_id: str, topic: str, settings: Settings) -> None:
    with _runs_lock:
        _runs[run_id]["status"] = "running"
        _runs[run_id]["updated_at"] = _now()

    def record_stage(stage: str) -> None:
        with _runs_lock:
            run = _runs.get(run_id)
            if run is None or stage not in STAGE_NAMES:
                return
            if stage not in run["completed_stages"]:
                run["completed_stages"].append(stage)
            run["updated_at"] = _now()

    try:
        record = run_pipeline(topic, settings, on_stage_complete=record_stage)
    except Exception as error:
        logger.exception("Dashboard pipeline run failed: run_id=%s", run_id)
        with _runs_lock:
            run = _runs[run_id]
            run["status"] = "failed"
            run["error"] = str(error)[:600]
            run["updated_at"] = _now()
        return

    with _runs_lock:
        run = _runs[run_id]
        run["status"] = "completed"
        run["completed_stages"] = list(STAGE_NAMES)
        run["scheduled_post"] = record["scheduled_post"]
        run["pipeline_run_id"] = record["run_id"]
        run["updated_at"] = _now()


@app.get("/")
def dashboard_home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        settings = load_settings()
    except ConfigurationError as error:
        return {"configured": False, "message": str(error)}
    return {
        "configured": True,
        "model": settings.openai_model,
        "timezone": settings.linkedin_timezone,
    }


@app.get("/api/posts")
def recent_posts(limit: int = Query(default=8, ge=1, le=30)) -> list[dict[str, Any]]:
    try:
        settings = load_settings()
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    path = settings.scheduled_posts_path
    if not path.is_file():
        return []

    posts: list[dict[str, Any]] = []
    for line in reversed(path.read_text(encoding="utf-8").splitlines()):
        try:
            record = json.loads(line)
            scheduled_post = record["scheduled_post"]
            posts.append(
                {
                    "run_id": record["run_id"],
                    "created_at": record["created_at"],
                    "topic": record["topic"],
                    "scheduled_post": scheduled_post,
                    "stage_count": len(record.get("stages", [])),
                }
            )
        except (KeyError, TypeError, json.JSONDecodeError):
            logger.warning("Skipping malformed scheduled-post audit row")
        if len(posts) >= limit:
            break
    return posts


@app.post("/api/runs", status_code=202)
def start_run(request: RunRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    try:
        settings = load_settings()
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    with _runs_lock:
        if any(run["status"] in {"queued", "running"} for run in _runs.values()):
            raise HTTPException(status_code=409, detail="A pipeline run is already in progress")

        run_id = str(uuid4())
        state = {
            "run_id": run_id,
            "topic": request.topic,
            "status": "queued",
            "created_at": _now(),
            "updated_at": _now(),
            "completed_stages": [],
            "scheduled_post": None,
            "pipeline_run_id": None,
            "error": None,
        }
        _runs[run_id] = state

    background_tasks.add_task(_execute_run, run_id, request.topic, settings)
    return dict(state)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return dict(run)
