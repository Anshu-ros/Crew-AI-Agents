from pathlib import Path

import pytest

from linkedin_content_manager.config import ConfigurationError, load_settings


def _write_env(path, values):
    path.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()),
        encoding="utf-8",
    )


def test_load_settings_reads_and_validates_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    _write_env(
        env_file,
        {
            "OPENAI_API_KEY": "openai-test",
            "OPENAI_MODEL": "gpt-4.1",
            "SERPER_API_KEY": "serper-test",
            "LINKEDIN_TIMEZONE": "America/Chicago",
            "SCHEDULED_POSTS_PATH": "data/posts.jsonl",
            "SERPER_API_URL": "https://example.test/search",
            "EXTERNAL_API_MAX_ATTEMPTS": "4",
            "EXTERNAL_API_TIMEOUT_SECONDS": "12.5",
        },
    )
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "SERPER_API_KEY",
        "LINKEDIN_TIMEZONE",
        "SCHEDULED_POSTS_PATH",
        "SERPER_API_URL",
        "EXTERNAL_API_MAX_ATTEMPTS",
        "EXTERNAL_API_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = load_settings(env_file)

    assert settings.openai_api_key == "openai-test"
    assert settings.openai_model == "gpt-4.1"
    assert settings.serper_api_key == "serper-test"
    assert settings.linkedin_timezone == "America/Chicago"
    assert settings.scheduled_posts_path == Path("data/posts.jsonl")
    assert settings.external_api_max_attempts == 4
    assert settings.external_api_timeout_seconds == 12.5


def test_load_settings_reports_all_missing_required_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "SERPER_API_KEY",
        "LINKEDIN_TIMEZONE",
        "SCHEDULED_POSTS_PATH",
        "SERPER_API_URL",
        "EXTERNAL_API_MAX_ATTEMPTS",
        "EXTERNAL_API_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY.*SERPER_API_KEY"):
        load_settings(env_file)


def test_load_settings_rejects_invalid_timezone(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    _write_env(
        env_file,
        {
            "OPENAI_API_KEY": "openai-test",
            "OPENAI_MODEL": "gpt-4.1",
            "SERPER_API_KEY": "serper-test",
            "LINKEDIN_TIMEZONE": "Mars/Olympus",
            "SCHEDULED_POSTS_PATH": "data/posts.jsonl",
            "SERPER_API_URL": "https://example.test/search",
            "EXTERNAL_API_MAX_ATTEMPTS": "3",
            "EXTERNAL_API_TIMEOUT_SECONDS": "20",
        },
    )
    for name in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "SERPER_API_KEY",
        "LINKEDIN_TIMEZONE",
        "SCHEDULED_POSTS_PATH",
        "SERPER_API_URL",
        "EXTERNAL_API_MAX_ATTEMPTS",
        "EXTERNAL_API_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigurationError, match="IANA timezone"):
        load_settings(env_file)
