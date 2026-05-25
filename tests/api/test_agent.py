"""API tests for the agentic RAG endpoint."""

from unittest.mock import AsyncMock

from src.services.llm.base import LLMResponse


GUARDRAIL_RESPONSE = '{"in_scope": true, "reason": "tech question"}'
ROUTER_RESPONSE = '{"tags": ["python"], "mode": "hybrid", "num_chunks": 5}'
GRADER_RESPONSE = '{"relevant": true, "reason": "directly relevant"}'
GENERATE_RESPONSE = "Python uses try/except for error handling."

MOCK_SEARCH_HITS = {
    "total": 1,
    "hits": [
        {
            "chunk_id": "c1",
            "article_id": "a1",
            "source_id": "100",
            "chunk_index": 0,
            "chunk_text": "Python uses try/except for error handling.",
            "chunk_word_count": 7,
            "title": "Error Handling Guide",
            "author": "Author A",
            "tags": ["python"],
            "url": "https://dev.to/test/error-handling",
            "_score": 1.5,
            "_id": "d1",
        },
    ],
}


def test_ask_agent_returns_answer(client, mock_opensearch, mock_llm_client, base_url):
    """Test /ask/agent returns a structured response with reasoning steps."""
    mock_opensearch.search.return_value = MOCK_SEARCH_HITS
    mock_llm_client.generate = AsyncMock(
        side_effect=[
            LLMResponse(text=GUARDRAIL_RESPONSE, model="test"),
            LLMResponse(text=ROUTER_RESPONSE, model="test"),
            LLMResponse(text=GRADER_RESPONSE, model="test"),
            LLMResponse(text=GENERATE_RESPONSE, model="test-model", total_duration_ms=50.0),
        ]
    )

    response = client.post(f"{base_url}/ask/agent", json={"question": "How do I handle errors?"})

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "How do I handle errors?"
    assert data["answer"] == GENERATE_RESPONSE
    assert len(data["reasoning_steps"]) >= 3
    assert data["chunks_used"] >= 1
    assert data["sources"][0]["title"] == "Error Handling Guide"


def test_ask_agent_out_of_scope(client, mock_llm_client, base_url):
    """Test /ask/agent rejects out-of-scope questions."""
    mock_llm_client.generate = AsyncMock(
        return_value=LLMResponse(text='{"in_scope": false, "reason": "not tech"}', model="test")
    )

    response = client.post(f"{base_url}/ask/agent", json={"question": "How do I cook pasta?"})

    assert response.status_code == 200
    data = response.json()
    assert "only answer questions" in data["answer"].lower()
    assert data["chunks_used"] == 0


def test_ask_agent_empty_question_rejected(client, base_url):
    """Test empty question returns validation error."""
    response = client.post(f"{base_url}/ask/agent", json={"question": ""})
    assert response.status_code == 422
