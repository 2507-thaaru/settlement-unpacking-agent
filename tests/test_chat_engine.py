import asyncio
import pytest
from src.schemas import load_all_data
from src.orchestrator import run_all
from src.chat_engine import SettlementChatEngine
from api.main import DATA_DIR


def test_chat_engine_summary():
    ctx = load_all_data(DATA_DIR)
    report = run_all(ctx)

    res = asyncio.run(SettlementChatEngine.chat("Give me an executive overview of the reconciliation", ctx, report))
    assert res is not None
    assert "reply" in res
    assert "Total Gross Settled" in res["reply"]
    assert "exceptions" in res["reply"].lower()


def test_chat_engine_specific_pass():
    ctx = load_all_data(DATA_DIR)
    report = run_all(ctx)

    res = asyncio.run(SettlementChatEngine.chat("Explain pass 4 and what is our GST ITC leakage?", ctx, report))
    assert res is not None
    assert "reply" in res
    assert "GST" in res["reply"]
    assert "ITC" in res["reply"]


def test_chat_engine_reserve_forecast():
    ctx = load_all_data(DATA_DIR)
    report = run_all(ctx)

    res = asyncio.run(SettlementChatEngine.chat("When will overdue rolling reserves be released?", ctx, report))
    assert res is not None
    assert "reply" in res
    assert "Rolling Reserve" in res["reply"]
