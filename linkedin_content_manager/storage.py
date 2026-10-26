"""Append-only local persistence for scheduled posts and stage outputs."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from linkedin_content_manager.models import ScheduledPost


_write_lock = threading.Lock()


class JsonlScheduleStore:
    """Persist each complete pipeline run as one append-only JSONL record."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def save(
        self,
        topic: str,
        scheduled_post: ScheduledPost,
        stage_outputs: list[dict[str, str]],
    ) -> dict[str, Any]:
        record: dict[str, Any] = {
            "run_id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "topic": topic,
            "scheduled_post": scheduled_post.model_dump(mode="json"),
            "stages": stage_outputs,
        }
        encoded = (json.dumps(record, ensure_ascii=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _write_lock:
            descriptor = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return record
