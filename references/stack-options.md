# Stack options

Default recommendation: **Python 3.12 + LangGraph**. But enterprises often mandate
a framework — always ask, and adapt. Everything downstream (observability, evals,
tests, function index) is framework-agnostic and only needs a callable entrypoint
`run_once(request) -> Response` plus a `chat()` loop.

| Option | Pick it when | Trade-offs |
|--------|--------------|-----------|
| **LangGraph** (default) | you want explicit graph state, checkpointing, human-in-the-loop pauses, and a big ecosystem | more concepts; LangChain dependency surface |
| **Raw Anthropic / OpenAI SDK + thin loop** | you want maximum control, minimal deps, easiest to reason about and test | you build routing, retries, state yourself |
| **PydanticAI** | you want typed tools/outputs and clean testing ergonomics, lighter than LangGraph | younger ecosystem |
| **CrewAI / AutoGen** | multi-agent orchestration is the core problem | heavier abstractions; harder to trace precisely |
| **Enterprise-mandated (Bedrock Agents, Vertex, Semantic Kernel, custom)** | the company requires it | adapt the skeleton; keep the entrypoint contract so evals/obs still work |
| **TypeScript (LangGraph.js, Vercel AI SDK, Mastra)** | the team is JS-first or the agent lives in a Node service | port `tools/fn_search`, index, and `run_evals` to TS; OTel GenAI conventions still apply |

## Model provider

- Default to the latest, most capable Claude models for the agent itself unless
  the spec mandates otherwise or requires a local/on-prem model.
- Eval **judge** defaults to a local Ollama model regardless of the agent's
  provider (cost + offline CI). See `skills/3-evalset`.

## Data layer

Deferred to discovery. The skeleton ships a storage abstraction
(`src/<pkg>/data/`); the discovery spec picks concrete stores (e.g. Postgres +
pgvector, Postgres + Qdrant, warehouse connector). Each store gets an adapter, an
integration test, and an observability `data_source` attribute.
