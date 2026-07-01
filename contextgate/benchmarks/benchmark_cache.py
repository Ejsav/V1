"""Simple cached vs uncached latency benchmark for ContextGate.

Run the stack first (`docker compose up --build`), then:

    python benchmarks/benchmark_cache.py
"""

import time

import httpx

API_URL = "http://localhost:8000/v1/chat"
PROMPT = "Explain what semantic caching is in simple terms."


def send(prompt: str) -> tuple[dict, float]:
    start = time.perf_counter()
    resp = httpx.post(
        API_URL,
        json={
            "prompt": prompt,
            "model": "mock",
            "user_id": "bench",
            "session_id": "bench",
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return resp.json(), elapsed_ms


def main() -> None:
    first, first_ms = send(PROMPT)
    print("First request:")
    print(f"  cache_hit: {str(first['cache_hit']).lower()}")
    print(f"  latency_ms: {int(first_ms)}")

    second, second_ms = send(PROMPT)
    print("Second request:")
    print(f"  cache_hit: {str(second['cache_hit']).lower()}")
    print(f"  latency_ms: {int(second_ms)}")

    improvement = int(first_ms - second_ms)
    print("Estimated improvement:")
    print(f"  {improvement}ms faster")


if __name__ == "__main__":
    main()
