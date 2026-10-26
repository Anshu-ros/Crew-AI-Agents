"""Factories for the five dedicated pipeline agents."""

from crewai import Agent, LLM

from linkedin_content_manager.config import Settings
from linkedin_content_manager.tools.serper_search import SerperClient, SerperSearchTool


def build_agents(settings: Settings) -> dict[str, Agent]:
    llm = LLM(model=settings.openai_model, api_key=settings.openai_api_key)
    search_tool = SerperSearchTool(
        client=SerperClient(
            api_key=settings.serper_api_key,
            endpoint=settings.serper_api_url,
            max_attempts=settings.external_api_max_attempts,
            timeout_seconds=settings.external_api_timeout_seconds,
        )
    )

    return {
        "research": Agent(
            role="LinkedIn Research Analyst",
            goal="Find timely, reliable evidence and useful angles for the requested topic.",
            backstory=(
                "You are a meticulous B2B research analyst. You distinguish sourced facts "
                "from interpretation and return concise findings with source links."
            ),
            tools=[search_tool],
            llm=llm,
            allow_delegation=False,
            verbose=False,
        ),
        "write": Agent(
            role="LinkedIn Content Writer",
            goal="Turn the research into a clear, engaging first-draft LinkedIn post.",
            backstory=(
                "You write credible, human LinkedIn posts for professional audiences. "
                "You use specific evidence, a strong opening, and a useful takeaway."
            ),
            llm=llm,
            allow_delegation=False,
            verbose=False,
        ),
        "critique": Agent(
            role="LinkedIn Editorial Critic",
            goal="Identify concrete, high-impact improvements to the draft.",
            backstory=(
                "You are a rigorous editor focused on accuracy, clarity, originality, "
                "audience value, tone, structure, and unsupported claims."
            ),
            llm=llm,
            allow_delegation=False,
            verbose=False,
        ),
        "optimize": Agent(
            role="LinkedIn Content Optimizer",
            goal="Apply the critique and produce a polished, publish-ready post.",
            backstory=(
                "You are a senior social editor. You implement actionable feedback while "
                "preserving factual accuracy and the writer's strongest ideas."
            ),
            llm=llm,
            allow_delegation=False,
            verbose=False,
        ),
        "schedule": Agent(
            role="LinkedIn Publishing Coordinator",
            goal="Return the final post with an explicit publication time and timezone.",
            backstory=(
                "You prepare content for a publishing queue. You preserve the final copy "
                "exactly and return only a valid structured schedule."
            ),
            llm=llm,
            allow_delegation=False,
            verbose=False,
        ),
    }
