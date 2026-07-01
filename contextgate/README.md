# ContextGate

**Open-source LLM router that reduces latency and token cost using async queues, semantic cache hits, and provider-aware request routing.**

ContextGate is an LLM context router with semantic caching, async request handling, and provider-aware context reuse. It sits between your application and AI model providers, reducing repeated model calls and improving response latency for repeated or similar prompts.

> **A note on caching:** Hosted model KV-caches (OpenAI, Gemini, Claude) are internal to those providers and are not externally accessible. ContextGate does **not** try to control or offload those internal caches. Instead, it reduces repeated work *outside* the model by caching semantically similar requests and routing repeated context more efficiently.

---

## Why LLM routing and semantic caching matter

LLM applications tend to send the same or very similar prompts over and over — FAQ-style questions, repeated system prompts, retries, and common user intents. Every one of those calls costs latency and tokens.

ContextGate provides a clean router layer for LLM applications that:

- **reduces repeated model calls** by serving semantically similar prompts from a cache,
- **improves response latency for repeated/similar prompts** (cache hits return in milliseconds),
- **provides a clean router layer for LLM applications** with swappable provider adapters,
- is **designed for experimentation, benchmarking, and extension**.

---

## What V1 does

1. A client sends a prompt to `POST /v1/chat`.
2. The backend embeds the prompt with a deterministic local embedding function.
3. It checks a PostgreSQL + pgvector semantic cache.
4. If a similar prompt exists above the similarity threshold, the cached response is returned instantly.
5. On a cache miss, the request is queued in a Redis Stream.
6. A worker consumes the queued request.
7. The worker calls the configured LLM provider.
8. The response is stored back into the semantic cache.
9. The API returns the response to the client.

It ships with a mock provider (no API key required) and a Gemini adapter placeholder that activates only when `GEMINI_API_KEY` is set.

## What V1 does **not** do

- No authentication, billing, or API keys management
- No production Kubernetes / multi-region deployment
- No dashboard UI or advanced observability
- No real-time streaming responses
- No fine-tuning or local LLM hosting
- No "KV-cache offloading" of hosted models (not externally possible)

These are intentionally out of scope — see the [Roadmap](#roadmap).

---

## Architecture

```
Client App
   |
   v
FastAPI Router
   |
   v
Embedding Service
   |
   v
Postgres + pgvector Semantic Cache
   |
   |-- cache hit --> return cached response
   |
   |-- cache miss
          |
          v
      Redis Stream
          |
          v
      LLM Worker
          |
          v
      Provider Adapter
          |
          v
      Save response to cache
          |
          v
      Return response
```

---

## How to run locally

Requirements: Docker + Docker Compose.

```bash
git clone <your-fork-url>
cd contextgate

# optional: copy env defaults (compose already sets sane defaults inline)
cp .env.example .env

docker compose up --build
```

The API is then available at **http://localhost:8000**.

Services started by Compose:

| Service    | Description                              |
|------------|------------------------------------------|
| `api`      | FastAPI app (port 8000)                  |
| `worker`   | Redis Stream consumer + provider caller  |
| `postgres` | PostgreSQL with the `pgvector` extension |
| `redis`    | Redis (Streams-based job queue)          |

---

## Example API requests

Health check:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"ContextGate"}
```

Chat request:

```bash
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain what semantic caching is.",
    "model": "mock",
    "user_id": "demo-user",
    "session_id": "demo-session"
  }'
```

**Cache miss response:**

```json
{
  "response": "Mock response for: Explain what semantic caching is.",
  "cache_hit": false,
  "similarity": null,
  "provider": "mock",
  "request_id": "generated-id"
}
```

**Cache hit response** (send the same or a very similar prompt again):

```json
{
  "response": "Mock response for: Explain what semantic caching is.",
  "cache_hit": true,
  "similarity": 0.91,
  "provider": "cache",
  "request_id": "generated-id"
}
```

### Example cache hit flow

1. First call for a prompt → **cache miss** → queued → worker calls the provider → response saved → returned (`cache_hit: false`).
2. Second call for the same or a paraphrased prompt → embedding is close to the stored one → **cache hit** → returned instantly from Postgres (`cache_hit: true`, `provider: "cache"`).

---

## Semantic cache

Cached rows live in the `semantic_cache` table (`id`, `prompt`, `response`, `embedding`, `provider`, `model`, `user_id`, `session_id`, `created_at`).

V1 uses a **deterministic local embedding** (the hashing trick) so the app runs without any paid embedding API:

- normalize text into word tokens,
- hash each token into a fixed-size (default **384**) vector using a signed bucket,
- L2-normalize the vector,
- compare with cosine similarity via pgvector.

The similarity threshold is configurable via `CACHE_SIMILARITY_THRESHOLD` (default `0.88`).

---

## Providers

Provider adapters implement a small interface:

```python
class BaseLLMProvider:
    async def generate(self, prompt: str, model: str) -> str:
        ...
```

- **MockProvider** — always returns `Mock response for: {prompt}`. No API key needed.
- **GeminiProvider** — reads `GEMINI_API_KEY`; raises a clear configuration error if it's missing. Gemini is never required for local development.

Select a provider with the `model` field in the request body (`"mock"` or `"gemini"`), or set `DEFAULT_PROVIDER`.

---

## Environment variables

See `.env.example`:

| Variable                      | Default                              | Description                          |
|-------------------------------|--------------------------------------|--------------------------------------|
| `APP_NAME`                    | `ContextGate`                        | Service name                         |
| `ENV`                         | `development`                        | Environment label                    |
| `DATABASE_URL`                | `postgresql+asyncpg://...`           | Async Postgres connection string     |
| `REDIS_URL`                   | `redis://redis:6379/0`               | Redis connection string              |
| `CACHE_SIMILARITY_THRESHOLD`  | `0.88`                               | Minimum cosine similarity for a hit  |
| `EMBEDDING_DIMENSIONS`        | `384`                                | Embedding vector size                |
| `DEFAULT_PROVIDER`            | `mock`                               | Provider used when none is specified |
| `GEMINI_API_KEY`              | *(empty)*                            | Enables the Gemini adapter           |
| `WORKER_TIMEOUT_SECONDS`      | `15`                                 | How long the API waits for a result  |

---

## Running the tests

```bash
pip install -r requirements.txt
pytest
```

Tests cover the health endpoint, embedding similarity behavior (similar prompts score high, unrelated prompts score lower), and the mock provider.

---

## Benchmark

With the stack running:

```bash
python benchmarks/benchmark_cache.py
```

It sends a prompt, records the uncached latency, sends the same prompt again, records the cached latency, and prints the improvement. Because the mock provider simulates real model latency, the second (cached) request is dramatically faster:

```
First request:
  cache_hit: false
  latency_ms: 1240
Second request:
  cache_hit: true
  latency_ms: 80
Estimated improvement:
  1160ms faster
```

The cached path skips the queue and the provider entirely — it's a single vector lookup in Postgres.

---

## Roadmap

**V1**
- FastAPI router
- Redis queue
- PostgreSQL + pgvector semantic cache
- Mock provider
- Gemini adapter placeholder
- Benchmark script

**V2**
- OpenAI and Anthropic adapters
- Streaming responses
- Better embeddings
- Cache invalidation rules
- Admin metrics endpoint
- Request deduplication

**V3**
- Dashboard
- Prometheus/Grafana metrics
- Provider fallback routing
- Cost tracking
- Team/project API keys
- Deployment templates

---

## Project structure

```
contextgate/
  app/
    main.py              # FastAPI app + lifespan
    config.py            # Settings (pydantic-settings)
    routes/              # health + chat endpoints
    services/            # embedding, cache, queue, provider
    providers/           # base, mock, gemini adapters
    workers/             # Redis Stream consumer
    db/                  # async engine + SQLAlchemy models
    schemas/             # request/response models
  benchmarks/
    benchmark_cache.py
  tests/
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env.example
  README.md
```

---

## License

Open source. Designed for experimentation, benchmarking, and extension.
