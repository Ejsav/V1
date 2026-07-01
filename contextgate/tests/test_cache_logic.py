import pytest

from app.providers.mock_provider import MockProvider
from app.services.embedding_service import cosine_similarity, embed_text


def test_similar_prompts_have_high_similarity():
    a = embed_text("Explain what semantic caching is")
    b = embed_text("Explain what semantic caching means")
    assert cosine_similarity(a, b) > 0.7


def test_different_prompts_have_lower_similarity():
    base = embed_text("Explain what semantic caching is")
    similar = embed_text("Explain what semantic caching means")
    different = embed_text("What is the tallest mountain on Earth")

    # An unrelated prompt should be less similar than a near-paraphrase.
    assert cosine_similarity(base, different) < cosine_similarity(base, similar)


@pytest.mark.asyncio
async def test_mock_provider_returns_response():
    provider = MockProvider()
    result = await provider.generate("hello world", "mock")

    assert result.startswith("Mock response for:")
    assert "hello world" in result
