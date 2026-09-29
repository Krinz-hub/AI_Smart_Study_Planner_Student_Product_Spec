import pytest
from app.ai.google_provider import generate_text, is_google_ai_available, is_ollama_available


@pytest.mark.asyncio
async def test_ollama_lite_fallback():
    # Verify Ollama is reachable
    ollama_ready = await is_ollama_available()
    assert ollama_ready is True, "Local Ollama runtime should be running on localhost:11434"

    # Call generate_text
    response = await generate_text(
        prompt="In 5 words or fewer, what is a binary search tree?",
        system_instruction="Be concise.",
    )
    assert response is not None
    assert len(response.strip()) > 0
