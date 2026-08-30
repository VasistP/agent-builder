"""From-scratch observability dashboard.

Reads the portable JSON trace logs (logs/traces/*.jsonl) and eval results
(evals/results/*.json) — no external observability service required. Panels
follow references/observability-standards.md O8. Run: `streamlit run dashboard/app.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent


@st.cache_data(ttl=10)
def load_spans() -> pd.DataFrame:
    """Load all spans from logs/traces/*.jsonl into a DataFrame."""
    rows: list[dict] = []
    for path in sorted((ROOT / "logs" / "traces").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        return pd.DataFrame()
    df = pd.json_normalize(rows)
    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    df["duration_s"] = (df["end_time"] - df["start_time"]).dt.total_seconds()
    return df


@st.cache_data(ttl=10)
def load_eval_trend() -> pd.DataFrame:
    """Load eval result summaries into a trend DataFrame."""
    rows = []
    for path in sorted((ROOT / "evals" / "results").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        rows.append({"timestamp": data["timestamp"], **data.get("summary", {})})
    return pd.DataFrame(rows)


st.set_page_config(page_title="agent-pkg observability", layout="wide")
st.title("agent-pkg — observability")

spans = load_spans()
if spans.empty:
    st.info("No traces yet. Run `make smoke` or exercise the agent.")
    st.stop()

runs = spans[spans["name"] == "agent run"]
llm = spans[spans["name"].isin(["chat", "embeddings"])]
tools = spans[spans["name"] == "execute_tool"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Agent runs", len(runs))
p95 = round(runs["duration_s"].quantile(0.95), 2) if len(runs) else 0
total_cost = round(spans.get("attributes.cost.usd", pd.Series(dtype=float)).sum(), 4)
tool_err = tools["status"].eq("error").mean() * 100 if len(tools) else 0
c2.metric("p95 run latency (s)", p95)
c3.metric("Total cost (USD)", total_cost)
c4.metric("Tool error rate", f"{tool_err:.1f}%")

st.subheader("Latency over time (agent runs)")
st.line_chart(runs.set_index("start_time")["duration_s"])

st.subheader("Tokens over time")
tok = spans.set_index("start_time")[
    [
        c
        for c in spans.columns
        if c in ("attributes.gen_ai.usage.input_tokens", "attributes.gen_ai.usage.output_tokens")
    ]
]
if not tok.empty:
    st.area_chart(tok)

st.subheader("Tool calls")
if len(tools):
    st.bar_chart(tools.groupby("attributes.tool.name").size())

st.subheader("Errors")
errs = spans[spans["status"] == "error"]
st.dataframe(
    errs[["start_time", "name", "error_type"]] if len(errs) else pd.DataFrame({"none": []})
)

st.subheader("Eval score trend")
trend = load_eval_trend()
if not trend.empty and "overall" in trend:
    st.line_chart(trend.set_index("timestamp")[[c for c in trend.columns if c != "timestamp"]])
else:
    st.caption("No eval results yet — run `make eval`.")

st.subheader("Trace explorer")
trace_id = st.selectbox("trace_id", sorted(spans["trace_id"].unique()))
st.dataframe(
    spans[spans["trace_id"] == trace_id][
        ["name", "start_time", "duration_s", "status", "error_type"]
    ].sort_values("start_time")
)
