"""
Shared code for every page: CSS theme, header component, and cached
data/report loading so each page doesn't re-run the pipeline separately.
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import load_all_data
from src.orchestrator import run_all

DATA_DIR_ENV = os.getenv("DATA_DIR")
DATA_DIR = Path(DATA_DIR_ENV) if DATA_DIR_ENV else Path(__file__).parent.parent / "data"

THEME_CSS = """
<style>
:root {
    --navy: #0B2D6B;
    --accent: #3395FF;
    --ok: #16A34A;
    --warn: #D97706;
    --err: #DC2626;
    --bg-card: #FFFFFF;
}
.stApp { background-color: #F5F7FB; }
.agent-header {
    padding: 1.25rem 1.5rem;
    border-radius: 14px;
    background: linear-gradient(135deg, var(--navy) 0%, #14418F 100%);
    color: white;
    margin-bottom: 1.25rem;
}
.agent-header h1 { margin: 0; font-size: 1.9rem; }
.agent-header p { margin: 0.25rem 0 0 0; opacity: 0.85; font-size: 0.95rem; }
.metric-card {
    background: var(--bg-card);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 3px rgba(15,23,42,0.08);
    border: 1px solid #E5E9F2;
}
.metric-card .label { font-size: 0.8rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em; }
.metric-card .value { font-size: 1.9rem; font-weight: 700; color: var(--navy); margin-top: 0.15rem; }
.pass-card {
    border-radius: 10px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid var(--ok);
    background: #F0FBF4;
}
.pass-card.warn { border-left-color: var(--warn); background: #FFF8EC; }
.pass-card.err { border-left-color: var(--err); background: #FEF2F2; }
.pass-card .name { font-weight: 700; color: #0F172A; }
.pass-card .detail { font-size: 0.85rem; color: #475569; margin-top: 0.15rem; }
.info-card {
    background: var(--bg-card);
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    border: 1px solid #E5E9F2;
    box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    margin-bottom: 0.9rem;
}
.info-card h4 { margin: 0 0 0.4rem 0; color: var(--navy); }
section[data-testid="stExpander"] { border-radius: 10px; border: 1px solid #E5E9F2; }
</style>
"""


def apply_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="agent-header">
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Loading source data...")
def get_context():
    return load_all_data(DATA_DIR)


@st.cache_data(show_spinner="Running matching pipeline...")
def get_report(_ctx):
    # underscore prefix on _ctx tells Streamlit not to hash the DataContext object
    return run_all(_ctx)
