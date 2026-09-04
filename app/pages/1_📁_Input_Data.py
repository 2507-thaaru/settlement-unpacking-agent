import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from common import apply_theme, render_header, get_context

st.set_page_config(page_title="Input Data — Settlement Unpacking Agent", layout="wide")
apply_theme()
render_header("Input Data", "The five source files every pass reads from")

ctx = get_context()

datasets = [
    (
        "Settlement report", ctx.settlement_df,
        "Order-level rows from Razorpay's settlement export — one row per order, "
        "with gross amount, MDR fee, GST on that MDR, refunds, and chargebacks already broken out.",
    ),
    (
        "Bank statement", ctx.bank_df,
        "One lumped NEFT credit per settlement batch, exactly as it would appear on a bank statement — "
        "this is the 'unexploded' side of the problem.",
    ),
    (
        "GST invoice", ctx.invoice_df,
        "Razorpay's monthly GST tax invoice on MDR, by billing period — used to cross-check "
        "that the GST actually charged matches what's claimable as Input Tax Credit.",
    ),
    (
        "Sales ledger", ctx.ledger_df,
        "The merchant's own order records, used to validate that every settled order "
        "actually corresponds to a real sale at the right amount.",
    ),
    (
        "Reserve ledger", ctx.reserve_df,
        "Rolling reserve held and released per settlement batch, with the release-due date — "
        "the data the reserve forecast is built from.",
    ),
]

for name, df, description in datasets:
    st.markdown(
        f'<div class="info-card"><h4>{name}</h4>{description}</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.write("")
