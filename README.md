# ContextGate

[![CI](https://github.com/Ejsav/V1/actions/workflows/ci.yml/badge.svg)](https://github.com/Ejsav/V1/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

**Open-source LLM router that reduces latency and token cost using async queues, semantic cache hits, and provider-aware request routing.**

ContextGate is an LLM context router with semantic caching, async request handling, and provider-aware context reuse. It sits between your application and AI model providers, serving semantically similar prompts from a PostgreSQL + pgvector cache and routing cache misses through a Redis-backed worker.

The project lives in [`contextgate/`](./contextgate). See its
[README](./contextgate/README.md) for setup, architecture, API reference, and benchmarks, and
[`docs/launch-post.md`](./docs/launch-post.md) for a plain-language explanation of what it does and why.

> **Run all commands from inside `contextgate/`** (`cd contextgate` first) —
> that's where `docker-compose.yml`, the app, tests, and benchmark live.

## Quick start

```bash
git clone https://github.com/Ejsav/V1.git
cd V1/contextgate
docker compose up --build          # API on http://localhost:8000
```

## License

[MIT](./LICENSE) © 2026 Eric Jokl
