import asyncio

from app.providers.base import BaseLLMProvider


class MockProvider(BaseLLMProvider):
    """Provider that needs no API key and always returns a useful fake response.

    A small artificial delay simulates real model latency so that cached vs
    uncached benchmarks show a meaningful difference.
    """

    async def generate(self, prompt: str, model: str) -> str:
        await asyncio.sleep(1.0)
        return f"Mock response for: {prompt}"
