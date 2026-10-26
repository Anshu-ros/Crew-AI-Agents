# LinkedIn Content Manager

A sequential CrewAI pipeline that researches a topic, writes a LinkedIn draft, critiques it, applies the critique, and records a scheduled post. The schedule is a local publishing-queue record; this project does not connect to LinkedIn or publish posts.

## Requirements

- Python 3.10 or newer
- An OpenAI API key with access to GPT-4
- A Serper.dev API key

## Setup

From the project root, create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set the credentials and runtime configuration:

```powershell
Copy-Item .env.example .env
```

Required variables:

- `OPENAI_API_KEY`: OpenAI API credential.
- `OPENAI_MODEL`: GPT-4-family model available to the API key, such as `gpt-4.1` or `gpt-4o`.
- `SERPER_API_KEY`: Serper.dev API credential.
- `LINKEDIN_TIMEZONE`: IANA timezone used for the scheduled publication time, such as `America/New_York`.
- `SCHEDULED_POSTS_PATH`: Local JSONL file where completed schedules and pipeline outputs are appended.
- `SERPER_API_URL`: Serper search endpoint, normally `https://google.serper.dev/search`.
- `EXTERNAL_API_MAX_ATTEMPTS`: Total Serper request attempts, including the first request.
- `EXTERNAL_API_TIMEOUT_SECONDS`: Per-request timeout in seconds.

The configuration loader validates all required values before creating the CrewAI agents. Never commit `.env` or place real credentials in source control.

## Run

Pass the desired topic as a quoted command-line argument:

```powershell
python -m linkedin_content_manager "How AI is changing product discovery"
```

The five CrewAI tasks run sequentially. The schedule stage selects the next weekday at 09:00 in `LINKEDIN_TIMEZONE` (or today if that time has not passed), and returns a structured post, ISO 8601 publication time, and timezone. A successful run prints its audit record and appends the same record to the configured JSONL file. Each record includes all five stage outputs and the final scheduled post.

To load a dotenv file at another location:

```powershell
python -m linkedin_content_manager --env-file .env "Your topic"
```

## Dashboard

Start the local dashboard from the project root:

```powershell
python -m uvicorn linkedin_content_manager.dashboard:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in a browser. Enter a topic to start the five-stage pipeline, follow stage progress, and review the saved schedule queue. Runs use the configured OpenAI and Serper APIs and require valid credentials and available API credits. The server binds to loopback so the dashboard is not exposed to your network.

## Tests

The unit tests mock all Serper HTTP interactions and do not require API credentials:

```powershell
python -m pip install pytest
python -m pytest
```
