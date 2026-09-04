"""
Results dashboard — identical logic and layout to the original single-page
dashboard.py, just relocated into the multipage app and pointed at the
shared theme/data loaders in common.py instead of duplicating them.
"""

import sys
from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from common import apply_theme, render_header, get_context, get_report

st.set_page_config(page_title="Results — Settlement Unpacking Agent", layout="wide")
apply_theme()
render_header("Results Dashboard", "Pass status, exceptions, and reserve forecast")

ctx = get_context()
report = get_report(ctx)
summary = report["summary"]

# ---------------------------------------------------------------------------
# Top metric cards
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
metric_defs = [
    (c1, "Passes implemented", f"{summary['passes_implemented']} / {summary['passes_total']}"),
    (c2, "Total exceptions found", summary["total_exceptions_found"]),
    (c3, "Settlement batches", ctx.settlement_df["settlement_id"].nunique()),
    (c4, "Orders processed", len(ctx.settlement_df)),
]
for col, label, value in metric_defs:
    col.markdown(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ---------------------------------------------------------------------------
# Pass status cards
# ---------------------------------------------------------------------------
st.subheader("Pass status")
status_cols = st.columns(len(report["passes"]) or 1)
for col, (name, info) in zip(status_cols, report["passes"].items()):
    status = info["status"]
    css_class = "" if status == "ok" else ("warn" if status == "not_implemented" else "err")
    icon = "✅" if status == "ok" else ("⏳" if status == "not_implemented" else "❌")
    detail = (
        f"{info['exception_count']} exceptions"
        if status == "ok"
        else info.get("detail", "")[:60]
    )
    col.markdown(
        f'<div class="pass-card {css_class}"><div class="name">{icon} {name}</div>'
        f'<div class="detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
exceptions_df = pd.DataFrame(report["all_exceptions"])

chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Exceptions by category")
    if not exceptions_df.empty:
        cat_counts = (
            exceptions_df.groupby("category").size().reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        chart = (
            alt.Chart(cat_counts)
            .mark_bar(color="#3395FF", cornerRadiusEnd=4)
            .encode(
                x=alt.X("count:Q", title="Exceptions"),
                y=alt.Y("category:N", sort="-x", title=None),
                tooltip=["category", "count"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No exceptions yet — implement a pass to populate this chart.")

with chart_col2:
    st.subheader("Reserve release forecast")
    forecast = None
    pass3_metrics = report["combined_metrics"].get("pass3_reserve_forecast", {})
    if pass3_metrics.get("forecast"):
        forecast = pd.DataFrame(pass3_metrics["forecast"])
    if forecast is not None and not forecast.empty:
        forecast["release_due_date"] = pd.to_datetime(forecast["release_due_date"])
        chart = (
            alt.Chart(forecast)
            .mark_bar(color="#0B2D6B", cornerRadiusEnd=4)
            .encode(
                x=alt.X("release_due_date:T", title="Release due"),
                y=alt.Y("still_held:Q", title="Amount still held (₹)"),
                tooltip=["settlement_id", "still_held", "release_due_date"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No reserve still held — nothing to forecast, or Pass 3 not implemented yet.")

st.divider()

# ---------------------------------------------------------------------------
# Exception list with category filter
# ---------------------------------------------------------------------------
st.subheader("Exception list")
if not exceptions_df.empty:
    categories = sorted(exceptions_df["category"].unique())
    selected = st.multiselect("Filter by category", categories, default=categories)
    filtered = exceptions_df[exceptions_df["category"].isin(selected)].copy()
    if "amount" in filtered.columns:
        filtered["amount"] = filtered["amount"].apply(
            lambda v: f"₹{v:,.2f}" if pd.notna(v) else "—"
        )
    st.dataframe(filtered, use_container_width=True, hide_index=True)
else:
    st.info("No exceptions to show yet — implement at least one pass to see results here.")

# ---------------------------------------------------------------------------
# Raw source data (debugging)
# ---------------------------------------------------------------------------
with st.expander("Raw source data"):
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Settlement report", "Bank statement", "GST invoice", "Sales ledger", "Reserve ledger"]
    )
    with tab1:
        st.dataframe(ctx.settlement_df, use_container_width=True)
    with tab2:
        st.dataframe(ctx.bank_df, use_container_width=True)
    with tab3:
        st.dataframe(ctx.invoice_df, use_container_width=True)
    with tab4:
        st.dataframe(ctx.ledger_df, use_container_width=True)
    with tab5:
        st.dataframe(ctx.reserve_df, use_container_width=True)
