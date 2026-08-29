# Observability tool options (open-source only)

All options below self-host, need no paid subscription, and can consume or be
migrated from the portable `logs/traces/*.jsonl` export. Whatever you pick, the
JSON export stays on (`references/observability-standards.md` O7).

| Tool | Best for | Setup | Notes |
|------|----------|-------|-------|
| **Langfuse** (self-host) | tool/workflow, RAG, multi-agent; teams wanting prompt versioning + eval-score UI | `docker compose` (Postgres + clickhouse + web) | OTel ingest; attach eval scores; good trace tree; MIT-ish OSS core |
| **Arize Phoenix** | OTel-native shops; local dev; RAG debugging | single container / `pip install arize-phoenix` | OpenInference/OTel spans; strong retrieval eval views; runs fully local |
| **OpenLLMetry + Grafana/Tempo/Prometheus** | teams already on Grafana; want vendor-neutral OTel end-to-end | compose: otel-collector + Tempo + Prometheus + Grafana | most "build-it-yourself"; dashboards as code |
| **From-scratch dashboard** (this template) | single-shot Q&A agents; user has no preference; minimal-dependency requirement | one compose service (Streamlit or FastAPI) reading `logs/traces/` | ships in `templates/`; panels per O8; easy to hand off and maintain |

## Decision guide

1. User has a preference / company standard → use it (as long as it's OSS and
   self-hostable). Wire OTel GenAI export to it + keep JSON export.
2. Agent is tool-using / RAG / multi-agent and user is open → **Langfuse** or
   **Phoenix**.
3. Agent is simple, or user says "I don't know" → **from-scratch dashboard**.
4. Team lives in Grafana → **OpenLLMetry + Grafana**.

## Migration

Because every span is in `logs/traces/*.jsonl` (schema in
`observability-standards.md`), moving tools is: point a new OTel exporter/importer
at that file (or re-emit historical spans). No agent code changes. Document the
chosen importer in the project README.
