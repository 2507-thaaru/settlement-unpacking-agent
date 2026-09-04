"""
Shared data contract for the Settlement Unpacking Agent.

Every pass module (src/matcher/pass*.py) reads and returns data shaped
exactly according to this file. This is the one file all Antigravity
agents must treat as fixed — do not rename columns, change types, or
add fields here without updating every pass and every test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Column contracts (must match data_generator/generate_data.py exactly)
# ---------------------------------------------------------------------------

SETTLEMENT_COLUMNS = [
    "settlement_id", "order_id", "payment_id", "order_date", "settlement_date",
    "gross_amount", "mdr_fee", "gst_on_mdr", "refund_amount", "chargeback_amount",
]

BANK_COLUMNS = ["date", "narration", "utr", "credit_amount"]

INVOICE_COLUMNS = ["invoice_number", "period", "total_mdr_amount", "gst_on_mdr_amount", "invoice_date"]

LEDGER_COLUMNS = ["order_id", "order_date", "invoice_amount", "customer_ref", "gst_period"]

RESERVE_COLUMNS = [
    "settlement_id", "settlement_date", "reserve_hold_amount",
    "reserve_released_amount", "release_due_date",
]

# ---------------------------------------------------------------------------
# Business constants (must match the generator's assumptions)
# ---------------------------------------------------------------------------

MDR_RATE = 0.02
GST_RATE = 0.18
RESERVE_RATE = 0.05
RESERVE_WINDOW_DAYS = 120

# Reference "today" for evaluating whether a reserve release is overdue.
# Set well after every batch's release_due_date in the default synthetic
# dataset so only the deliberately-stuck batch is flagged. Override this
# if you regenerate data with different dates.
AS_OF_DATE = date(2027, 6, 1)

# Rupee tolerance for float-rounding noise when comparing expected vs
# actual amounts. Differences larger than this are real exceptions;
# smaller ones are rounding noise, not findings.
AMOUNT_TOLERANCE = 1.0

# ---------------------------------------------------------------------------
# Exception taxonomy
# ---------------------------------------------------------------------------


class ExceptionCategory:
    """String constants, not an Enum, so categories serialize to JSON/CSV cleanly."""
    MISSING_UTR = "MISSING_UTR"
    UNEXPLAINED_DEDUCTION = "UNEXPLAINED_DEDUCTION"
    MDR_RATE_MISMATCH = "MDR_RATE_MISMATCH"
    RESERVE_NOT_RELEASED = "RESERVE_NOT_RELEASED"
    GST_ITC_MISMATCH = "GST_ITC_MISMATCH"
    CROSS_PERIOD_SETTLEMENT = "CROSS_PERIOD_SETTLEMENT"

    ALL = [
        MISSING_UTR, UNEXPLAINED_DEDUCTION, MDR_RATE_MISMATCH,
        RESERVE_NOT_RELEASED, GST_ITC_MISMATCH, CROSS_PERIOD_SETTLEMENT,
    ]


@dataclass
class Exception_:
    """One flagged exception. settlement_id is always required; order_id
    only when the exception is order-level rather than batch-level."""
    settlement_id: str
    category: str
    description: str
    order_id: Optional[str] = None
    amount: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "settlement_id": self.settlement_id,
            "order_id": self.order_id,
            "category": self.category,
            "description": self.description,
            "amount": self.amount,
        }


@dataclass
class PassResult:
    """Every pass module's run() function returns exactly this shape."""
    pass_name: str
    exceptions: list = field(default_factory=list)   # list[Exception_]
    metrics: dict = field(default_factory=dict)       # e.g. {"match_rate": 0.94}
    output_df: Optional[pd.DataFrame] = None          # pass-specific enriched data, optional


@dataclass
class DataContext:
    """Bundles the four (five, with reserve) source dataframes."""
    settlement_df: pd.DataFrame
    bank_df: pd.DataFrame
    invoice_df: pd.DataFrame
    ledger_df: pd.DataFrame
    reserve_df: pd.DataFrame


def load_all_data(data_dir: str | Path) -> DataContext:
    """Load the four/five CSVs into a DataContext. Raises if a required
    column is missing, so a schema drift fails loudly instead of quietly
    producing wrong matches downstream."""
    data_dir = Path(data_dir)

    def _load(name: str, columns: list[str]) -> pd.DataFrame:
        df = pd.read_csv(data_dir / name)
        missing = set(columns) - set(df.columns)
        if missing:
            raise ValueError(f"{name} is missing expected columns: {missing}")
        return df

    return DataContext(
        settlement_df=_load("settlement_report.csv", SETTLEMENT_COLUMNS),
        bank_df=_load("bank_statement.csv", BANK_COLUMNS),
        invoice_df=_load("gst_invoice.csv", INVOICE_COLUMNS),
        ledger_df=_load("sales_ledger.csv", LEDGER_COLUMNS),
        reserve_df=_load("reserve_ledger.csv", RESERVE_COLUMNS),
    )
