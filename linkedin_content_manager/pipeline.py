"""Crew construction and end-to-end pipeline execution."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from crewai import Crew, Process
from pydantic import ValidationError

from linkedin_content_manager.agents import build_agents
from linkedin_content_manager.config import Settings
from linkedin_content_manager.models import ScheduledPost
from linkedin_content_manager.storage import JsonlScheduleStore
from linkedin_content_manager.tasks import build_tasks


logger = logging.getLogger(__name__)

STAGE_NAMES = ("research", "write", "critique", "optimize", "schedule")


def build_crew(
    settings: Settings,
    on_stage_complete: Callable[[str], None] | None = None,
) -> Crew:
    agents = build_agents(settings)
    tasks = build_tasks(agents, settings, on_stage_complete=on_stage_complete)
    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
    )


def _scheduled_post_from_result(result: Any) -> ScheduledPost:
    task_outputs = getattr(result, "tasks_output", None) or []
    if not task_outputs:
        raise RuntimeError("CrewAI returned no task outputs; nothing can be scheduled")

    final_output = task_outputs[-1]
    parsed = getattr(final_output, "pydantic", None)
    try:
        if isinstance(parsed, ScheduledPost):
            scheduled_post = parsed
        elif parsed is not None:
            scheduled_post = ScheduledPost.model_validate(parsed)
        else:
            scheduled_post = ScheduledPost.model_validate_json(final_output.raw)
    except (ValidationError, AttributeError, TypeError) as error:
        raise RuntimeError(
            "The schedule stage did not return valid structured output"
        ) from error

    try:
        expected_zone = ZoneInfo(scheduled_post.timezone)
    except ZoneInfoNotFoundError as error:
        raise RuntimeError(
            f"The schedule stage returned an invalid timezone: {scheduled_post.timezone}"
        ) from error
    if scheduled_post.timezone != expected_zone.key:
        raise RuntimeError("The schedule stage must return an IANA timezone name")
    if scheduled_post.publish_at.tzinfo is None:
        raise RuntimeError("The schedule stage must return a timezone-aware publish_at")
    if scheduled_post.publish_at.utcoffset() != scheduled_post.publish_at.astimezone(
        expected_zone
    ).utcoffset():
        raise RuntimeError("The publish_at offset does not match the schedule timezone")
    return scheduled_post


def run_pipeline(
    topic: str,
    settings: Settings,
    on_stage_complete: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    normalized_topic = topic.strip()
    if not normalized_topic:
        raise ValueError("Topic must not be empty")

    crew = build_crew(settings, on_stage_complete=on_stage_complete)
    logger.info("Starting LinkedIn content pipeline for topic: %s", normalized_topic)
    for stage in STAGE_NAMES:
        logger.info("Pipeline stage queued: %s", stage)

    result = crew.kickoff(
        inputs={
            "topic": normalized_topic,
            "timezone": settings.linkedin_timezone,
            "current_time": datetime.now(ZoneInfo(settings.linkedin_timezone)).isoformat(),
        }
    )
    scheduled_post = _scheduled_post_from_result(result)
    if scheduled_post.timezone != settings.linkedin_timezone:
        raise RuntimeError(
            "The schedule stage returned timezone "
            f"{scheduled_post.timezone!r}; expected {settings.linkedin_timezone!r}"
        )

    task_outputs = result.tasks_output
    stage_outputs = [
        {"stage": stage, "output": str(task_outputs[index].raw)}
        for index, stage in enumerate(STAGE_NAMES)
        if index < len(task_outputs)
    ]
    record = JsonlScheduleStore(settings.scheduled_posts_path).save(
        normalized_topic,
        scheduled_post,
        stage_outputs,
    )
    logger.info("Scheduled post persisted with run_id=%s", record["run_id"])
    return record
