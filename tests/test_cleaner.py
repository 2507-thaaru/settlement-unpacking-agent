import pytest
import pandas as pd
from src.cleaner import DataCleaner, clean_currency_to_float, normalize_date_string


def test_clean_currency_to_float():
    assert clean_currency_to_float("₹10,500.50") == 10500.50
    assert clean_currency_to_float("$1,200.00") == 1200.00
    assert clean_currency_to_float("500 INR") == 500.0
    assert clean_currency_to_float(250.75) == 250.75
    assert clean_currency_to_float(None) == 0.0


def test_normalize_date_string():
    assert normalize_date_string("01/03/2026") == "2026-03-01"
    assert normalize_date_string("2026-03-01") == "2026-03-01"
    assert normalize_date_string("2026-03-01T14:30:00Z") == "2026-03-01"


def test_clean_messy_settlement_report():
    # Dirty settlement data with currency symbols, custom headers, missing derivable columns
    dirty_data = pd.DataFrame([
        {
            "Settlement Batch ID": "SETTL_20260301_001",
            "Order Ref": "ORD_00001",
            "Gross Amount (INR)": "₹10,000.00",
            "MDR Fee": "₹200.00",
            "Order Date": "01/03/2026",
            "Payout Date": "02/03/2026",
        }
    ])
    result = DataCleaner.clean_and_standardize(dirty_data, filename="merchant_settlement.csv")
    assert result.is_valid is True
    assert result.status == "cleaned"
    assert result.dataset_type == "settlement_report"
    assert result.cleaned_df is not None
    assert "gst_on_mdr" in result.cleaned_df.columns
    assert result.cleaned_df["gross_amount"].iloc[0] == 10000.00
    assert result.cleaned_df["mdr_fee"].iloc[0] == 200.00
    assert result.cleaned_df["gst_on_mdr"].iloc[0] == 36.00  # 18% of 200


def test_unhandleable_missing_critical_keys():
    # Missing both settlement_id and gross_amount
    invalid_data = pd.DataFrame([{"foo": "bar", "user": "test"}])
    result = DataCleaner.clean_and_standardize(invalid_data, filename="unknown.csv")
    assert result.is_valid is False
    assert result.status == "unhandleable"
    assert len(result.missing_critical_columns) > 0
    assert result.suggested_fix is not None
