import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from common import apply_theme, render_header, get_context, get_report

st.set_page_config(
    page_title="Settlement Unpacking Agent",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()
render_header(
    "Settlement Unpacking Agent",
    "Razorpay AI Buildathon 2026 — Track 4: AI Finance Controller",
)

st.markdown(
    """
    <div class="info-card">
    <h4>The problem</h4>
    A Razorpay T+2 settlement lands as a single lumped NEFT credit covering
    hundreds of orders — netted against MDR, GST on that MDR, refunds,
    chargebacks, and rolling reserve movements. Without exploding that
    lump sum back into its parts, a finance team can't post accurate
    ledger entries, claim the GST Input Tax Credit they're owed, know how
    much cash is actually locked in reserve, or catch a revenue booked in
    the wrong GST filing period.
    </div>

    <div class="info-card">
    <h4>Why it's underserved</h4>
    Generic reconciliation tools (HighRadius, Puzzle, ChatFin) solve
    bank-to-ledger matching at enterprise scale. Almost none of them treat
    <b>rolling-reserve release forecasting</b> and
    <b>GST-on-MDR ITC leakage detection</b> as first-class outputs of the
    same settlement-batch explosion — and none are built around India's
    MDR / GST / TDS / reserve stack specifically.
    </div>

    <div class="info-card">
    <h4>What this agent does</h4>
    One pipeline, five passes, each closing a different finance-ops loop
    on the same exploded batch data:
    <ol>
      <li><b>Batch match</b> — settlement ↔ bank credit, full amount reconciliation</li>
      <li><b>Order validation</b> — explode to order level, catch MDR rate errors</li>
      <li><b>Reserve forecast</b> — track held vs released reserve, project release dates</li>
      <li><b>GST ITC check</b> — catch tax-invoice mismatches that would kill an ITC claim</li>
      <li><b>Cross-period flag</b> — catch settlements straddling a GST filing period</li>
    </ol>
    Every finding is measured against a known, honest exception list — not
    a cherry-picked demo match.
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

# --- live snapshot, so the intro page isn't just static text ---
ctx = get_context()
report = get_report(ctx)
summary = report["summary"]

st.subheader("Current run, at a glance")
c1, c2, c3 = st.columns(3)
c1.markdown(
    f'<div class="metric-card"><div class="label">Passes implemented</div>'
    f'<div class="value">{summary["passes_implemented"]} / {summary["passes_total"]}</div></div>',
    unsafe_allow_html=True,
)
c2.markdown(
    f'<div class="metric-card"><div class="label">Exceptions found</div>'
    f'<div class="value">{summary["total_exceptions_found"]}</div></div>',
    unsafe_allow_html=True,
)
c3.markdown(
    f'<div class="metric-card"><div class="label">Settlement batches</div>'
    f'<div class="value">{ctx.settlement_df["settlement_id"].nunique()}</div></div>',
    unsafe_allow_html=True,
)

st.caption("Use the sidebar to explore the input data, how the pipeline works, and the full results dashboard.")
