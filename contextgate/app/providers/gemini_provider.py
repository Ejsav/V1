import httpx

from app.config import settings
from app.providers.base import BaseLLMProvider

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiProvider(BaseLLMProvider):
    """Thin adapter for Google Gemini.

    Disabled unless GEMINI_API_KEY is set, so local development never depends
    on a real key. Kept small and isolated on purpose.
    """

    async def generate(self, prompt: str, model: str) -> str:
        api_key = settings.gemini_api_key
        if not api_key:
            raise RuntimeError(
                "GeminiProvider requires GEMINI_API_KEY. Set it in your environment, "
                "or use the 'mock' provider for local development."
            )

        # Allow "gemini" as a friendly alias for a concrete default model name.
        model_name = model if model and model != "gemini" else "gemini-1.5-flash"
        url = _GEMINI_URL.format(model=model_name)
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, params={"key": api_key}, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]
