"""Five sequential CrewAI tasks, each consuming the previous stage."""

import logging
from collections.abc import Callable

from crewai import Agent, Task

from linkedin_content_manager.config import Settings
from linkedin_content_manager.models import ScheduledPost


logger = logging.getLogger(__name__)


def _stage_callback(
    stage: str,
    on_stage_complete: Callable[[str], None] | None,
) -> Callable[..., None]:
    def log_completion(task_output: object) -> None:
        logger.info("Pipeline stage completed: %s", stage)
        if on_stage_complete is not None:
            on_stage_complete(stage)

    return log_completion


def build_tasks(
    agents: dict[str, Agent],
    settings: Settings,
    on_stage_complete: Callable[[str], None] | None = None,
) -> list[Task]:
    research = Task(
        description=(
            "Research the topic: {topic}. Use web search for recent, relevant evidence. "
            "Summarize key facts, source URLs, audience-relevant insights, and any uncertainty. "
            "Do not invent sources or unsupported statistics."
        ),
        expected_output="A concise research brief with key findings and source URLs.",
        agent=agents["research"],
        callback=_stage_callback("research", on_stage_complete),
    )
    write = Task(
        description=(
            "Write a LinkedIn post about {topic}, using the research brief supplied by the "
            "previous stage. Create a strong opening, a coherent body, and a useful ending. "
            "Keep claims grounded in the research and do not add invented facts."
        ),
        expected_output="One complete first-draft LinkedIn post, without editorial notes.",
        agent=agents["write"],
        context=[research],
        callback=_stage_callback("write", on_stage_complete),
    )
    critique = Task(
        description=(
            "Critique the draft using the preceding research and draft. Give specific, "
            "actionable feedback: quote or identify the issue, explain why it matters, and "
            "recommend an exact improvement. Address factual support, clarity, structure, "
            "audience value, tone, and unnecessary wording. Do not rewrite the full post."
        ),
        expected_output="Prioritized, concrete revision instructions tied to the draft.",
        agent=agents["critique"],
        context=[research, write],
        callback=_stage_callback("critique", on_stage_complete),
    )
    optimize = Task(
        description=(
            "Produce the final LinkedIn post by applying the critique to the first draft. "
            "Use the research as the factual source of truth. Resolve unsupported claims, "
            "improve clarity and flow, and return only the optimized post text."
        ),
        expected_output="A polished, publish-ready LinkedIn post with no surrounding commentary.",
        agent=agents["optimize"],
        context=[research, write, critique],
        callback=_stage_callback("optimize", on_stage_complete),
    )
    schedule = Task(
        description=(
            "Schedule the optimized post below. Preserve its wording exactly. Choose the "
            "next weekday at 09:00 in the configured timezone ({timezone}); the current "
            "local date and time is {current_time}. If today is a weekday and 09:00 has "
            "not passed there, use today. Return publish_at as an "
            "ISO 8601 datetime with the correct UTC offset, timezone as the configured "
            "IANA name, and post_text. Do not claim that LinkedIn was contacted or that "
            "the post was actually published.\n\n"
            "Topic: {topic}"
        ),
        expected_output=(
            "A structured object with post_text, publish_at (ISO 8601 with offset), "
            "and timezone."
        ),
        agent=agents["schedule"],
        context=[optimize],
        output_pydantic=ScheduledPost,
        callback=_stage_callback("schedule", on_stage_complete),
    )
    logger.info("Prepared sequential pipeline stages: research, write, critique, optimize, schedule")
    return [research, write, critique, optimize, schedule]
