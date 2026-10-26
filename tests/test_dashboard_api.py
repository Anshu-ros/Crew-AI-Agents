from pathlib import Path

from fastapi.testclient import TestClient

from linkedin_content_manager import dashboard
from linkedin_content_manager.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        openai_api_key="test-openai-key",
        openai_model="gpt-4.1",
        serper_api_key="test-serper-key",
        linkedin_timezone="America/New_York",
        scheduled_posts_path=tmp_path / "scheduled.jsonl",
        serper_api_url="https://example.test/search",
        external_api_max_attempts=2,
        external_api_timeout_seconds=5,
    )


def test_dashboard_serves_local_ui():
    with TestClient(dashboard.app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Publishing desk" in response.text


def test_run_endpoint_tracks_mocked_pipeline(monkeypatch, tmp_path):
    settings = _settings(tmp_path)

    def fake_run_pipeline(topic, _settings, on_stage_complete=None):
        for stage in dashboard.STAGE_NAMES:
            if on_stage_complete:
                on_stage_complete(stage)
        return {
            "run_id": "audit-run-1",
            "scheduled_post": {
                "post_text": "A test post.",
                "publish_at": "2026-10-20T09:00:00-04:00",
                "timezone": "America/New_York",
            },
            "stages": [{"stage": stage} for stage in dashboard.STAGE_NAMES],
        }

    monkeypatch.setattr(dashboard, "load_settings", lambda: settings)
    monkeypatch.setattr(dashboard, "run_pipeline", fake_run_pipeline)

    with TestClient(dashboard.app) as client:
        response = client.post("/api/runs", json={"topic": "Flying cars"})
        assert response.status_code == 202
        run_id = response.json()["run_id"]

        completed = client.get(f"/api/runs/{run_id}")

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["completed_stages"] == list(dashboard.STAGE_NAMES)
    assert completed.json()["scheduled_post"]["post_text"] == "A test post."


def test_run_endpoint_rejects_whitespace_topic(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, "load_settings", lambda: _settings(tmp_path))

    with TestClient(dashboard.app) as client:
        response = client.post("/api/runs", json={"topic": "   "})

    assert response.status_code == 422
