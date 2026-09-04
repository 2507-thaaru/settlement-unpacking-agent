import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from common import apply_theme, render_header, get_context, get_report

st.set_page_config(page_title="How It Works — Settlement Unpacking Agent", layout="wide")
apply_theme()
render_header("How It Works", "Data flow, and exactly how each number is calculated — from the current run")

ctx = get_context()
report = get_report(ctx)

PASS_TO_EXCEPTIONS = {
    "pass1_batch_match": ["MISSING_UTR", "UNEXPLAINED_DEDUCTION"],
    "pass2_order_validation": ["MDR_RATE_MISMATCH"],
    "pass3_reserve_forecast": ["RESERVE_NOT_RELEASED"],
    "pass4_gst_itc": ["GST_ITC_MISMATCH"],
    "pass5_cross_period": ["CROSS_PERIOD_SETTLEMENT"],
}
PASS_LABELS = {
    "pass1_batch_match": "Pass 1\\nBatch Match",
    "pass2_order_validation": "Pass 2\\nOrder Validation",
    "pass3_reserve_forecast": "Pass 3\\nReserve Forecast",
    "pass4_gst_itc": "Pass 4\\nGST ITC Check",
    "pass5_cross_period": "Pass 5\\nCross-Period",
}

exceptions_by_category = {}
for e in report["all_exceptions"]:
    exceptions_by_category[e["category"]] = exceptions_by_category.get(e["category"], 0) + 1


def pass_node(pass_name: str) -> str:
    info = report["passes"].get(pass_name, {})
    status = info.get("status", "not_implemented")
    count = info.get("exception_count", 0)
    label = PASS_LABELS[pass_name]
    if status == "ok" and count == 0:
        color = "#16A34A"  # clean run
    elif status == "ok":
        color = "#D97706"  # found exceptions
    elif status == "not_implemented":
        color = "#94A3B8"  # not built yet
    else:
        color = "#DC2626"  # error
    detail = f"{count} found" if status == "ok" else status.replace("_", " ")
    return f'{pass_name} [label="{label}\\n({detail})", shape=box, style="filled,rounded", fillcolor="{color}", fontcolor=white];'


def exception_node(category: str) -> str:
    count = exceptions_by_category.get(category, 0)
    color = "#FCD34D" if count > 0 else "#E5E9F2"
    fontcolor = "#0F172A" if count > 0 else "#94A3B8"
    return f'{category} [label="{category}\\n({count})", shape=note, style=filled, fillcolor="{color}", fontcolor="{fontcolor}"];'


def data_node(var_name: str, filename: str, df) -> str:
    return f'{var_name} [label="{filename}\\n({len(df)} rows)", shape=ellipse, style=filled, fillcolor="#DCE8FF", color="#3395FF"];'


nodes = [
    data_node("settlement", "settlement_report.csv", ctx.settlement_df),
    data_node("bank", "bank_statement.csv", ctx.bank_df),
    data_node("invoice", "gst_invoice.csv", ctx.invoice_df),
    data_node("ledger", "sales_ledger.csv", ctx.ledger_df),
    data_node("reserve", "reserve_ledger.csv", ctx.reserve_df),
]
nodes += [pass_node(p) for p in PASS_LABELS]
nodes += [exception_node(cat) for cats in PASS_TO_EXCEPTIONS.values() for cat in cats]

total_exceptions = len(report["all_exceptions"])
report_color = "#16A34A" if total_exceptions or report["summary"]["passes_implemented"] else "#94A3B8"

nl = chr(10)
data_nodes_str = nl.join(nodes[:5])
pass_nodes_str = nl.join(nodes[5:10])
exc_nodes_str = nl.join(nodes[10:])

GRAPH = f"""
digraph G {{
    rankdir=LR;
    bgcolor="transparent";
    node [fontname="Helvetica", fontsize=11];
    edge [color="#94A3B8"];

    subgraph cluster_data {{ label="Source data (this run)"; style=dashed; color="#94A3B8"; fontcolor="#475569";
        {data_nodes_str}
    }}
    subgraph cluster_passes {{ label="Matching passes (live status)"; style=dashed; color="#94A3B8"; fontcolor="#475569";
        {pass_nodes_str}
    }}
    subgraph cluster_exceptions {{ label="Exceptions raised (live counts)"; style=dashed; color="#94A3B8"; fontcolor="#475569";
        {exc_nodes_str}
    }}

    orchestrator [label="Orchestrator", shape=box, style="filled,rounded", fillcolor="#0B2D6B", fontcolor=white];
    report [label="Report\\n{total_exceptions} total exceptions", shape=box, style="filled,rounded", fillcolor="{report_color}", fontcolor=white];

    settlement -> pass1_batch_match; bank -> pass1_batch_match; reserve -> pass1_batch_match;
    settlement -> pass2_order_validation; ledger -> pass2_order_validation;
    reserve -> pass3_reserve_forecast;
    settlement -> pass4_gst_itc; invoice -> pass4_gst_itc;
    settlement -> pass5_cross_period;

    pass1_batch_match -> MISSING_UTR; pass1_batch_match -> UNEXPLAINED_DEDUCTION;
    pass2_order_validation -> MDR_RATE_MISMATCH;
    pass3_reserve_forecast -> RESERVE_NOT_RELEASED;
    pass4_gst_itc -> GST_ITC_MISMATCH;
    pass5_cross_period -> CROSS_PERIOD_SETTLEMENT;

    MISSING_UTR -> orchestrator; UNEXPLAINED_DEDUCTION -> orchestrator; MDR_RATE_MISMATCH -> orchestrator;
    RESERVE_NOT_RELEASED -> orchestrator; GST_ITC_MISMATCH -> orchestrator; CROSS_PERIOD_SETTLEMENT -> orchestrator;
    orchestrator -> report;
}}
"""

st.graphviz_chart(GRAPH, use_container_width=True)
st.caption(
    "This graph is generated live from the current run — node colors, exception counts, and row "
    "counts all reflect app/data actually loaded, not a static diagram. Grey pass nodes mean that "
    "pass isn't implemented yet; amber means it found something to flag."
)

st.divider()
st.subheader("The exact math behind each pass")

with st.expander("Pass 1 — Batch match & amount reconciliation", expanded=True):
    st.markdown(
        """
        **Match key:** the last 8 characters of `settlement_id`, embedded in the bank narration.

        **Expected net credit:**
        ```
        expected_net = sum(gross_amount) - sum(mdr_fee) - sum(gst_on_mdr)
                       - sum(refund_amount) - sum(chargeback_amount)
                       - reserve_hold_amount + reserve_released_amount
        ```
        A shortfall beyond ₹1 tolerance → **UNEXPLAINED_DEDUCTION**. Empty `utr` → **MISSING_UTR**.
        """
    )

with st.expander("Pass 2 — Order-level validation & MDR rate check"):
    st.markdown(
        """
        ```
        expected_mdr = gross_amount * 0.02
        ```
        A gap beyond ₹1 → **MDR_RATE_MISMATCH**, flagged per order, not per batch.
        """
    )

with st.expander("Pass 3 — Reserve tracking & release forecast"):
    st.markdown(
        """
        ```
        still_held = reserve_hold_amount - reserve_released_amount
        ```
        `still_held > ₹1` **and** past `release_due_date` → **RESERVE_NOT_RELEASED**.
        """
    )

with st.expander("Pass 4 — GST-on-MDR ITC leakage"):
    st.markdown(
        """
        ```
        actual_gst_for_period = sum(gst_on_mdr) grouped by settlement month
        ```
        Compared against the invoice's `gst_on_mdr_amount` for that period → **GST_ITC_MISMATCH**.
        """
    )

with st.expander("Pass 5 — Cross-period settlement (stretch)"):
    st.markdown(
        """
        ```
        flag if order_date.month != settlement_date.month
        ```
        """
    )
