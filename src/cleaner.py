"""
Smart Data Cleaner & Validator for Settlement Unpacking Agent.

Handles messy, real-world user inputs:
- Strips currency symbols (₹, $, commas, text like INR) and coerces numeric fields.
- Normalizes diverse date formats (DD/MM/YYYY, YYYY-MM-DD, DD-Mon-YYYY, ISO timestamps).
- Fuzzy matches column headers to canonical schema names.
- Auto-derives missing handleable columns (e.g. gst_on_mdr = mdr_fee * 0.18, refund/chargeback defaults = 0.0, gst_period).
- Flags unhandleable files missing critical unrecoverable keys with structured intimations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

import pandas as pd

from src.schemas import (
    SETTLEMENT_COLUMNS,
    BANK_COLUMNS,
    INVOICE_COLUMNS,
    LEDGER_COLUMNS,
    RESERVE_COLUMNS,
    MDR_RATE,
    GST_RATE,
)

# Canonical schema definitions with critical keys and aliases
DATASET_SPECS = {
    "settlement_report": {
        "filename": "settlement_report.csv",
        "canonical_columns": SETTLEMENT_COLUMNS,
        "critical_columns": ["settlement_id", "gross_amount"],
        "aliases": {
            "settlement_id": ["settlement_id", "settlement_ref", "settle_id", "payout_id", "batch_id", "batch_no", "settlement_no"],
            "order_id": ["order_id", "order_no", "order_ref", "invoice_id", "merchant_order_id"],
            "payment_id": ["payment_id", "pay_id", "transaction_id", "txn_id", "razorpay_payment_id"],
            "order_date": ["order_date", "txn_date", "transaction_date", "created_at", "order_timestamp"],
            "settlement_date": ["settlement_date", "settled_at", "payout_date", "value_date"],
            "gross_amount": ["gross_amount", "gross_amt", "order_amount", "gross_amount_inr", "amount", "total_amount"],
            "mdr_fee": ["mdr_fee", "mdr_amount", "fee", "fees", "commission", "pg_fee"],
            "gst_on_mdr": ["gst_on_mdr", "gst_amount", "tax_on_fee", "fee_gst", "gst_fee"],
            "refund_amount": ["refund_amount", "refunds", "refund_amt", "total_refund"],
            "chargeback_amount": ["chargeback_amount", "chargebacks", "dispute_amount", "cb_amount"],
        },
        "numeric_columns": ["gross_amount", "mdr_fee", "gst_on_mdr", "refund_amount", "chargeback_amount"],
        "date_columns": ["order_date", "settlement_date"],
    },
    "bank_statement": {
        "filename": "bank_statement.csv",
        "canonical_columns": BANK_COLUMNS,
        "critical_columns": ["credit_amount", "narration"],
        "aliases": {
            "date": ["date", "txn_date", "transaction_date", "value_date", "booking_date", "post_date"],
            "narration": ["narration", "description", "particulars", "remarks", "transaction_details", "memo"],
            "utr": ["utr", "utr_number", "utr_no", "bank_reference", "ref_no", "rrn", "cheque_no"],
            "credit_amount": ["credit_amount", "credit", "cr_amount", "amount_credited", "net_credit", "deposit_amount"],
        },
        "numeric_columns": ["credit_amount"],
        "date_columns": ["date"],
    },
    "gst_invoice": {
        "filename": "gst_invoice.csv",
        "canonical_columns": INVOICE_COLUMNS,
        "critical_columns": ["invoice_number", "gst_on_mdr_amount"],
        "aliases": {
            "invoice_number": ["invoice_number", "invoice_no", "inv_num", "bill_no", "tax_invoice_no"],
            "period": ["period", "gst_period", "month", "billing_month", "tax_period"],
            "total_mdr_amount": ["total_mdr_amount", "total_mdr", "total_fee", "taxable_amount", "taxable_value"],
            "gst_on_mdr_amount": ["gst_on_mdr_amount", "gst_amount", "tax_amount", "total_tax", "igst_amount", "cgst_sgst_amount"],
            "invoice_date": ["invoice_date", "inv_date", "date_of_invoice", "created_date"],
        },
        "numeric_columns": ["total_mdr_amount", "gst_on_mdr_amount"],
        "date_columns": ["invoice_date"],
    },
    "sales_ledger": {
        "filename": "sales_ledger.csv",
        "canonical_columns": LEDGER_COLUMNS,
        "critical_columns": ["order_id", "invoice_amount"],
        "aliases": {
            "order_id": ["order_id", "order_no", "order_number", "invoice_id", "ref_order_id"],
            "order_date": ["order_date", "date", "sales_date", "created_date"],
            "invoice_amount": ["invoice_amount", "sales_amount", "gross_amount", "total_amount", "billed_amount", "net_sales"],
            "customer_ref": ["customer_ref", "customer_id", "customer_name", "cust_ref", "client_ref", "user_id"],
            "gst_period": ["gst_period", "period", "billing_period", "tax_period", "month"],
        },
        "numeric_columns": ["invoice_amount"],
        "date_columns": ["order_date"],
    },
    "reserve_ledger": {
        "filename": "reserve_ledger.csv",
        "canonical_columns": RESERVE_COLUMNS,
        "critical_columns": ["settlement_id", "reserve_hold_amount"],
        "aliases": {
            "settlement_id": ["settlement_id", "batch_id", "settle_id", "payout_id"],
            "settlement_date": ["settlement_date", "hold_date", "date", "created_at"],
            "reserve_hold_amount": ["reserve_hold_amount", "hold_amount", "reserve_amount", "reserve_held", "withheld_amount"],
            "reserve_released_amount": ["reserve_released_amount", "released_amount", "reserve_released", "released_amt"],
            "release_due_date": ["release_due_date", "due_date", "expected_release_date", "maturity_date"],
        },
        "numeric_columns": ["reserve_hold_amount", "reserve_released_amount"],
        "date_columns": ["settlement_date", "release_due_date"],
    },
}


@dataclass
class DataCleaningResult:
    status: str  # "cleaned" | "unhandleable"
    dataset_type: str
    target_filename: str
    is_valid: bool
    actions_taken: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_critical_columns: List[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None
    cleaned_df: Optional[pd.DataFrame] = None
    row_count: int = 0


def clean_currency_to_float(val: Any) -> float:
    """Strip currency symbols (₹, $, €, INR, commas, whitespace) and coerce to float."""
    if pd.isna(val) or val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    # Remove currency symbols and common currency codes
    val_str = re.sub(r'[₹$€£,]|INR|USD|EUR', '', val_str, flags=re.IGNORECASE).strip()
    
    # Extract numeric with optional decimal
    match = re.search(r'[-+]?\d*\.?\d+', val_str)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return 0.0
    return 0.0


def normalize_date_string(val: Any) -> str:
    """Normalize various date formats into YYYY-MM-DD."""
    if pd.isna(val) or val is None or str(val).strip() == "":
        return ""
    val_str = str(val).strip()
    
    # Common formats to attempt
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(val_str[:19] if "T" in val_str or len(val_str) > 19 else val_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
            
    # Fallback to pandas date parser
    try:
        dt = pd.to_datetime(val_str, errors="coerce")
        if not pd.isna(dt):
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
        
    return val_str


def normalize_column_name(col: str) -> str:
    """Lowercase, strip, and convert non-alphanumeric chars to underscore."""
    col = str(col).strip().lower()
    col = re.sub(r'[^a-z0-9]+', '_', col)
    return col.strip('_')


class DataCleaner:
    """Cleans and standardizes raw user DataFrames for reconciliation."""

    @classmethod
    def identify_dataset(cls, df: pd.DataFrame, filename: str = "", explicit_type: Optional[str] = None) -> Tuple[str, float]:
        """Identifies which dataset schema best matches the given DataFrame."""
        if explicit_type and explicit_type.strip().lower() in DATASET_SPECS:
            return explicit_type.strip().lower(), 1.0

        raw_cols = list(df.columns)
        norm_cols = {normalize_column_name(c) for c in raw_cols}
        fn_lower = filename.lower()

        best_type = "settlement_report"
        best_score = -1.0

        for ds_name, spec in DATASET_SPECS.items():
            score = 0.0
            aliases = spec["aliases"]
            
            matched_aliases = 0
            for canonical, alias_list in aliases.items():
                if any(normalize_column_name(a) in norm_cols for a in alias_list):
                    matched_aliases += 1
            
            score += (matched_aliases / len(aliases)) * 0.7
            
            # Critical columns match
            crit_matched = sum(1 for c in spec["critical_columns"] if any(normalize_column_name(a) in norm_cols for a in aliases.get(c, [c])))
            if crit_matched == len(spec["critical_columns"]):
                score += 0.3

            # Filename heuristic
            if ds_name in fn_lower or any(k in fn_lower for k in aliases.get("settlement_id", []) + ["report", "statement", "invoice", "ledger"]):
                if ds_name.split("_")[0] in fn_lower:
                    score += 0.2

            if score > best_score:
                best_score = score
                best_type = ds_name

        return best_type, best_score

    @classmethod
    def clean_and_standardize(
        cls,
        df: pd.DataFrame,
        filename: str = "uploaded_file.csv",
        explicit_type: Optional[str] = None
    ) -> DataCleaningResult:
        """
        Cleans, standardizes, derives missing handleable columns,
        and validates required columns on raw uploaded DataFrames.
        """
        if df.empty:
            return DataCleaningResult(
                status="unhandleable",
                dataset_type="unknown",
                target_filename=filename,
                is_valid=False,
                missing_critical_columns=["all"],
                suggested_fix="The uploaded file contains no data rows.",
            )

        # Drop entirely empty rows and columns
        df = df.dropna(how="all").dropna(how="all", axis=1)

        # Detect dataset type
        dataset_type, match_score = cls.identify_dataset(df, filename, explicit_type)
        spec = DATASET_SPECS[dataset_type]
        target_filename = spec["filename"]

        actions: List[str] = []
        warnings: List[str] = []

        # 1. Map columns using intelligent alias and substring matching
        raw_cols = list(df.columns)
        norm_to_raw = {normalize_column_name(c): c for c in raw_cols}

        column_mapping: Dict[str, str] = {}
        used_raw_cols = set()

        for canonical, alias_list in spec["aliases"].items():
            matched_raw = None
            # 1. Exact normalized match
            for alias in alias_list:
                norm_a = normalize_column_name(alias)
                if norm_a in norm_to_raw and norm_to_raw[norm_a] not in used_raw_cols:
                    matched_raw = norm_to_raw[norm_a]
                    break

            # 2. Substring containment match
            if not matched_raw:
                for alias in alias_list:
                    norm_a = normalize_column_name(alias)
                    if len(norm_a) >= 4:
                        for norm_c, raw_c in norm_to_raw.items():
                            if raw_c not in used_raw_cols and (norm_a in norm_c or norm_c in norm_a):
                                matched_raw = raw_c
                                break
                    if matched_raw:
                        break

            if matched_raw:
                column_mapping[matched_raw] = canonical
                used_raw_cols.add(matched_raw)

        clean_df = df.rename(columns=column_mapping)
        if len(column_mapping) > 0:
            actions.append(f"Mapped {len(column_mapping)} column headers to canonical schema names: {column_mapping}")

        # 2. Check for missing critical columns
        missing_critical = []
        for crit in spec["critical_columns"]:
            if crit not in clean_df.columns:
                missing_critical.append(crit)

        if missing_critical:
            suggested = f"Please include required column(s): {', '.join(missing_critical)} in your file."
            return DataCleaningResult(
                status="unhandleable",
                dataset_type=dataset_type,
                target_filename=target_filename,
                is_valid=False,
                actions_taken=actions,
                warnings=[f"Missing critical columns: {missing_critical}"],
                missing_critical_columns=missing_critical,
                suggested_fix=suggested,
            )

        # 3. Smart Imputation / Derivation for Handleable Gaps
        if dataset_type == "settlement_report":
            if "order_id" not in clean_df.columns:
                clean_df["order_id"] = [f"ORD_{i+1:05d}" for i in range(len(clean_df))]
                actions.append("Synthesized missing order_id values.")
            if "payment_id" not in clean_df.columns:
                clean_df["payment_id"] = [f"PAY_{clean_df['order_id'].iloc[i]}" for i in range(len(clean_df))]
                actions.append("Generated missing payment_id values from order_id.")
            if "order_date" not in clean_df.columns and "settlement_date" in clean_df.columns:
                clean_df["order_date"] = clean_df["settlement_date"]
                actions.append("Derived missing order_date from settlement_date.")
            elif "settlement_date" not in clean_df.columns and "order_date" in clean_df.columns:
                clean_df["settlement_date"] = clean_df["order_date"]
                actions.append("Derived missing settlement_date from order_date.")
            elif "order_date" not in clean_df.columns:
                clean_df["order_date"] = datetime.now().strftime("%Y-%m-%d")
                clean_df["settlement_date"] = datetime.now().strftime("%Y-%m-%d")
                actions.append("Defaulted missing dates to current date.")

            # Coerce gross amount
            clean_df["gross_amount"] = clean_df["gross_amount"].apply(clean_currency_to_float)

            # Derive mdr_fee if missing
            if "mdr_fee" not in clean_df.columns:
                clean_df["mdr_fee"] = (clean_df["gross_amount"] * MDR_RATE).round(2)
                actions.append(f"Auto-calculated missing mdr_fee using standard MDR rate ({MDR_RATE*100}%).")
            else:
                clean_df["mdr_fee"] = clean_df["mdr_fee"].apply(clean_currency_to_float)

            # Derive gst_on_mdr if missing
            if "gst_on_mdr" not in clean_df.columns:
                clean_df["gst_on_mdr"] = (clean_df["mdr_fee"] * GST_RATE).round(2)
                actions.append(f"Auto-calculated missing gst_on_mdr using GST rate ({GST_RATE*100}%).")
            else:
                clean_df["gst_on_mdr"] = clean_df["gst_on_mdr"].apply(clean_currency_to_float)

            # Default refund & chargeback
            if "refund_amount" not in clean_df.columns:
                clean_df["refund_amount"] = 0.0
                actions.append("Defaulted missing refund_amount to 0.0.")
            else:
                clean_df["refund_amount"] = clean_df["refund_amount"].apply(clean_currency_to_float)

            if "chargeback_amount" not in clean_df.columns:
                clean_df["chargeback_amount"] = 0.0
                actions.append("Defaulted missing chargeback_amount to 0.0.")
            else:
                clean_df["chargeback_amount"] = clean_df["chargeback_amount"].apply(clean_currency_to_float)

        elif dataset_type == "bank_statement":
            if "date" not in clean_df.columns:
                clean_df["date"] = datetime.now().strftime("%Y-%m-%d")
                actions.append("Defaulted missing bank credit date to current date.")
            if "utr" not in clean_df.columns:
                clean_df["utr"] = ""
                actions.append("Initialized missing utr column with empty values (to allow Pass 1 UTR validation).")
            else:
                clean_df["utr"] = clean_df["utr"].fillna("").astype(str)

            clean_df["credit_amount"] = clean_df["credit_amount"].apply(clean_currency_to_float)
            clean_df["narration"] = clean_df["narration"].fillna("").astype(str)

        elif dataset_type == "gst_invoice":
            clean_df["gst_on_mdr_amount"] = clean_df["gst_on_mdr_amount"].apply(clean_currency_to_float)
            if "total_mdr_amount" not in clean_df.columns:
                clean_df["total_mdr_amount"] = (clean_df["gst_on_mdr_amount"] / GST_RATE).round(2)
                actions.append(f"Derived missing total_mdr_amount from GST amount ({GST_RATE*100}% rate).")
            else:
                clean_df["total_mdr_amount"] = clean_df["total_mdr_amount"].apply(clean_currency_to_float)

            if "invoice_date" not in clean_df.columns:
                clean_df["invoice_date"] = datetime.now().strftime("%Y-%m-%d")
                actions.append("Defaulted missing invoice_date.")
            if "period" not in clean_df.columns:
                clean_df["period"] = clean_df["invoice_date"].astype(str).str[:7]
                actions.append("Derived invoice billing period (YYYY-MM) from invoice_date.")

        elif dataset_type == "sales_ledger":
            clean_df["invoice_amount"] = clean_df["invoice_amount"].apply(clean_currency_to_float)
            if "order_date" not in clean_df.columns:
                clean_df["order_date"] = datetime.now().strftime("%Y-%m-%d")
                actions.append("Defaulted missing order_date in sales ledger.")
            if "customer_ref" not in clean_df.columns:
                clean_df["customer_ref"] = "CUST_DEFAULT"
                actions.append("Assigned default customer_ref.")
            if "gst_period" not in clean_df.columns:
                clean_df["gst_period"] = clean_df["order_date"].astype(str).str[:7]
                actions.append("Derived gst_period from order_date.")

        elif dataset_type == "reserve_ledger":
            clean_df["reserve_hold_amount"] = clean_df["reserve_hold_amount"].apply(clean_currency_to_float)
            if "reserve_released_amount" not in clean_df.columns:
                clean_df["reserve_released_amount"] = 0.0
                actions.append("Defaulted reserve_released_amount to 0.0.")
            else:
                clean_df["reserve_released_amount"] = clean_df["reserve_released_amount"].apply(clean_currency_to_float)

            if "settlement_date" not in clean_df.columns:
                clean_df["settlement_date"] = datetime.now().strftime("%Y-%m-%d")
                actions.append("Defaulted reserve settlement_date.")
            if "release_due_date" not in clean_df.columns:
                # Default to 120 days after settlement date
                clean_df["release_due_date"] = pd.to_datetime(clean_df["settlement_date"]).apply(
                    lambda d: (d + pd.Timedelta(days=120)).strftime("%Y-%m-%d")
                )
                actions.append("Calculated 120-day release_due_date from settlement_date.")

        # 4. Standardize Date Formats
        for dcol in spec["date_columns"]:
            if dcol in clean_df.columns:
                clean_df[dcol] = clean_df[dcol].apply(normalize_date_string)
        actions.append(f"Normalized date formats for columns: {spec['date_columns']}")

        # 5. Filter to exact canonical columns
        final_df = clean_df[spec["canonical_columns"]].copy()

        return DataCleaningResult(
            status="cleaned",
            dataset_type=dataset_type,
            target_filename=target_filename,
            is_valid=True,
            actions_taken=actions,
            warnings=warnings,
            cleaned_df=final_df,
            row_count=len(final_df),
        )
