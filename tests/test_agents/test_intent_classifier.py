"""
tests/test_agents/test_intent_classifier.py

Unit tests for IntentClassifierAgent.
LLM is mocked — never calls real API in tests (TR3).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from backend.agents.intent_classifier import IntentClassifierAgent


@pytest.fixture
def agent():
    return IntentClassifierAgent()


@pytest.fixture
def base_state():
    return {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "session_id": "sess_abc123",
        "channel": "webchat",
        "messages": [],
    }


@pytest.mark.asyncio
@patch("backend.agents.intent_classifier.ChatAnthropic")
async def test_classifies_book_intent(MockLLM, agent, base_state):
    """Should classify booking intent correctly."""
    mock_llm_instance = AsyncMock()
    MockLLM.return_value = mock_llm_instance
    mock_llm_instance.ainvoke.return_value = AIMessage(
        content='{"intent": "book", "confidence": 0.97, "reasoning": "user wants to book"}'
    )
    agent._llm = mock_llm_instance

    state = {**base_state, "user_input": "I want to book an appointment for tomorrow"}
    result = await agent.run(state)

    assert result["intent"] == "book"
    assert result["next_node"] == "book"


@pytest.mark.asyncio
@patch("backend.agents.intent_classifier.ChatAnthropic")
async def test_classifies_cancel_intent(MockLLM, agent, base_state):
    mock_llm_instance = AsyncMock()
    MockLLM.return_value = mock_llm_instance
    mock_llm_instance.ainvoke.return_value = AIMessage(
        content='{"intent": "cancel", "confidence": 0.95, "reasoning": "user wants to cancel"}'
    )
    agent._llm = mock_llm_instance

    state = {**base_state, "user_input": "Please cancel my appointment"}
    result = await agent.run(state)

    assert result["intent"] == "cancel"


@pytest.mark.asyncio
@patch("backend.agents.intent_classifier.ChatAnthropic")
async def test_falls_back_to_other_on_unknown_intent(MockLLM, agent, base_state):
    """Unknown intents returned by LLM should be normalised to 'other'."""
    mock_llm_instance = AsyncMock()
    mock_llm_instance.ainvoke.return_value = AIMessage(
        content='{"intent": "something_weird", "confidence": 0.5}'
    )
    agent._llm = mock_llm_instance

    state = {**base_state, "user_input": "hello there"}
    result = await agent.run(state)

    assert result["intent"] == "other"
    assert result["next_node"] == "escalation_agent"


@pytest.mark.asyncio
@patch("backend.agents.intent_classifier.ChatAnthropic")
async def test_handles_empty_input(MockLLM, agent, base_state):
    """Empty user input should return 'other' without calling LLM."""
    mock_llm_instance = AsyncMock()
    agent._llm = mock_llm_instance

    state = {**base_state, "user_input": "   "}
    result = await agent.run(state)

    assert result["intent"] == "other"
    mock_llm_instance.ainvoke.assert_not_called()


@pytest.mark.asyncio
@patch("backend.agents.intent_classifier.ChatAnthropic")
async def test_handles_json_parse_error_gracefully(MockLLM, agent, base_state):
    """Malformed LLM response should not crash — route to escalation."""
    mock_llm_instance = AsyncMock()
    mock_llm_instance.ainvoke.return_value = AIMessage(content="not valid json at all")
    agent._llm = mock_llm_instance

    state = {**base_state, "user_input": "I need help"}
    result = await agent.run(state)

    assert result["intent"] == "other"
    assert result["next_node"] == "escalation_agent"


@pytest.mark.asyncio
@patch("backend.agents.intent_classifier.ChatAnthropic")
async def test_handles_llm_exception_gracefully(MockLLM, agent, base_state):
    """LLM API error should not crash the graph — escalate gracefully."""
    mock_llm_instance = AsyncMock()
    mock_llm_instance.ainvoke.side_effect = Exception("LLM API timeout")
    agent._llm = mock_llm_instance

    state = {**base_state, "user_input": "book appointment"}
    result = await agent.run(state)

    assert result["next_node"] == "escalation_agent"
    assert result["error"] != ""
