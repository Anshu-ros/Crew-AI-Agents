You are a senior Python backend engineer with deep experience building production multi-agent systems on CrewAI. Build a production-ready autonomous LinkedIn content manager in Python using CrewAI.

The system runs a fixed five-stage pipeline, executed sequentially: research, write, critique, optimize, and schedule. Each stage is handled by its own dedicated agent with a distinct role, goal, and backstory, and each stage's task consumes the previous stage's output. The pipeline should take a topic as input and end with a scheduled LinkedIn post ready for publishing.

Requirements:
- Use the CrewAI framework with a `Process.sequential` crew and five separate agents, one per task: research, write, critique, optimize, schedule.
- Use OpenAI GPT-4 as the LLM, authenticated via an OpenAI API key.
- Use Serper.dev as the web search tool for the research agent, authenticated via a Serper API key.
- Load all API keys and configuration from a `.env` file using `python-dotenv`. No keys may be hardcoded. Include a `.env.example` listing every required variable.
- The critique agent should produce concrete, actionable feedback, and the optimize agent should apply that feedback to produce the final draft.
- The schedule agent should produce a structured scheduling output (publish time and timezone) and persist the scheduled post locally so the pipeline is auditable.

Engineering expectations:
- Structure the project as a proper package with clear separation between agents, tasks, tools, configuration, and the entry point.
- Validate required environment variables at startup and fail with a clear error message if any are missing.
- Include error handling and retries for external API calls, and log each pipeline stage.
- Include unit tests for configuration loading and the tool wrappers, with external API calls mocked.
- Include a README with setup and run instructions.

Deliver the complete project: file tree, every source file, `.env.example`, requirements file, tests, and README. Keep the implementation focused on this pipeline; do not add features beyond the five stages described above.
