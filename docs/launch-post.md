# ContextGate: an honest LLM router with semantic caching

LLM applications repeat themselves. FAQ-style questions, shared system prompts,
retries, and common user intents mean the same or nearly-identical prompts get
sent to a model over and over. Every one of those calls costs latency and
tokens, even when the answer hasn't meaningfully changed.

**ContextGate** is a small, open-source router that sits between your
application and AI model providers. It cuts repeated work by serving
semantically similar prompts from a cache and routing the rest through an async
queue. V1 is intentionally minimal, fully runnable from a fresh clone, and
honest about what it does.

## What it actually does

A request to `POST /v1/chat` flows through five steps:

1. **Embed.** The prompt is turned into a vector using a deterministic local
   embedding (a hashing trick, 384 dimensions). No paid embedding API is
   required, and the same text always produces the same vector.
2. **Look up.** ContextGate queries a PostgreSQL + `pgvector` semantic cache for
   the nearest stored prompt, **scoped to the requested model**, using cosine
   similarity. If the best match clears a configurable threshold (default
   `0.88`), the cached response is returned immediately — no model call.
3. **Queue on a miss.** If nothing is similar enough, the request is pushed onto
   a Redis Stream.
4. **Work.** A worker consumes the stream, calls the configured provider
   adapter, stores the response (with its embedding) back in the cache, and
   publishes the result.
5. **Return.** The API, which was waiting on the result with a timeout, returns
   the response to the client.

Cache hits skip the queue and the provider entirely — they're a single vector
lookup in Postgres, so they return in milliseconds instead of seconds.

## The honest part: no KV-cache magic

There's a popular but misleading framing that tools like this "offload" a hosted
model's KV-cache. They don't, and they can't. The KV-cache inside OpenAI,
Gemini, or Claude is internal to those providers and is **not externally
accessible**. ContextGate makes no such claim.

What ContextGate does is reduce repeated work *outside* the model: it caches
semantically similar requests and routes repeated context more efficiently. That
is a real, measurable win — and it's the only kind of win available at this
layer.

## Why a queue at all?

For V1 the queue is deliberately simple: enqueue on a cache miss, let a worker
process it, wait for the result. It proves the routing concept and gives a clean
seam for future work (batching, deduplication, provider fallback) without
turning V1 into a production distributed system. The one reliability feature it
does include is **basic pending-entry recovery**: if a worker crashes
mid-request, the next one reclaims the orphaned queue entry on startup
(`XAUTOCLAIM`) and re-processes it, repopulating the cache for a client retry.
Advanced retry policies — backoff, dead-letter queues, multi-worker fairness —
are explicitly deferred to V2.

## Providers

Provider adapters implement a tiny interface (`async def generate(prompt,
model)`). V1 ships two:

- **MockProvider** — needs no API key and always returns a useful fake response,
  so the whole system runs and benchmarks locally out of the box.
- **GeminiProvider** — an isolated placeholder that activates only when
  `GEMINI_API_KEY` is set, and raises a clear error otherwise.

Adding OpenAI or Anthropic is a matter of writing another small adapter.

## What V1 is (and isn't)

V1 is a clean router layer for LLM applications, designed for experimentation,
benchmarking, and extension. It is **not** an auth system, a billing platform, a
streaming gateway, a dashboard, or a KV-cache offloader. Those are either on the
roadmap (V2/V3) or out of scope on purpose.

## Try it

```bash
git clone https://github.com/Ejsav/V1.git
cd V1/contextgate
docker compose up --build
```

Then send the same prompt twice and watch the second one come back as a cache
hit — or run `python benchmarks/benchmark_cache.py` to see cached vs uncached
latency side by side.

The full project, architecture diagram, and roadmap live in the
[repository README](../contextgate/README.md). Contributions and adapters
welcome.
