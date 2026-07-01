class BaseLLMProvider:
    """Interface implemented by every provider adapter."""

    async def generate(self, prompt: str, model: str) -> str:
        raise NotImplementedError
