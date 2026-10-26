from unittest.mock import Mock

import pytest
import requests

from linkedin_content_manager.tools.serper_search import (
    SerperClient,
    SerperSearchError,
    SerperSearchTool,
)


def test_serper_search_sends_authenticated_request():
    session = Mock()
    response = Mock(status_code=200)
    response.json.return_value = {"organic": [{"title": "Example"}]}
    session.post.return_value = response
    client = SerperClient(
        "test-key", "https://example.test/search", session=session
    )

    result = client.search("crewAI workflows")

    assert result == {"organic": [{"title": "Example"}]}
    session.post.assert_called_once_with(
        "https://example.test/search",
        headers={"X-API-KEY": "test-key", "Content-Type": "application/json"},
        json={"q": "crewAI workflows"},
        timeout=20,
    )


def test_serper_search_retries_transient_http_error(monkeypatch):
    session = Mock()
    unavailable = Mock(status_code=503)
    unavailable.raise_for_status.side_effect = requests.HTTPError(
        "service unavailable", response=Mock(status_code=503)
    )
    success = Mock(status_code=200)
    success.json.return_value = {"organic": []}
    session.post.side_effect = [unavailable, success]
    monkeypatch.setattr("linkedin_content_manager.tools.serper_search.time.sleep", Mock())
    client = SerperClient(
        "test-key", "https://example.test/search", max_attempts=2, session=session
    )

    assert client.search("topic") == {"organic": []}
    assert session.post.call_count == 2


def test_serper_search_does_not_retry_client_error():
    session = Mock()
    response = Mock(status_code=401)
    response.raise_for_status.side_effect = requests.HTTPError(
        "unauthorized", response=Mock(status_code=401)
    )
    session.post.return_value = response
    client = SerperClient(
        "bad-key", "https://example.test/search", max_attempts=3, session=session
    )

    with pytest.raises(SerperSearchError, match="HTTP 401"):
        client.search("topic")

    session.post.assert_called_once()


def test_crewai_tool_serializes_search_result():
    session = Mock()
    response = Mock(status_code=200)
    response.json.return_value = {"organic": []}
    session.post.return_value = response
    client = SerperClient(
        "test-key", "https://example.test/search", session=session
    )
    tool = SerperSearchTool(client=client)

    assert tool._run("topic") == '{"organic": []}'
    session.post.assert_called_once()
