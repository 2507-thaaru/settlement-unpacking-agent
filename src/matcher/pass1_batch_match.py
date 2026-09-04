"""
Pass 1 — Batch-level settlement <-> bank match.

OBJECTIVE
    For every settlement batch (a unique settlement_id in settlement_report.csv),
    find the matching bank credit row in bank_df, and confirm the credited
    amount reconciles with what the settlement + reserve data says it should be.

MATCH KEY
    bank_df["narration"] contains the last 8 characters of settlement_id
    (this mirrors how real bank narrations often embed a partial reference
    code). Extract that code and match it against settlement_id.endswith(code).
    Do not rely on row order or use the settlement_id_hint column — that
    column exists only in bank_statement_with_ground_truth.csv for testing,
    never in the real bank_statement.csv a pipeline would see.

AMOUNT RECONCILIATION
    For each matched batch, compute the expected net credit as:
        sum(gross_amount) - sum(mdr_fee) - sum(gst_on_mdr)
        - sum(refund_amount) - sum(chargeback_amount)
        - reserve_hold_amount + reserve_released_amount
    (gross/mdr/gst/refund/chargeback summed across all order rows for that
    settlement_id in settlement_df; reserve figures come from reserve_df
    for that settlement_id.)

    Compare this to bank_df["credit_amount"] for the matched row, using
    schemas.AMOUNT_TOLERANCE. If actual credit is lower than expected by
    more than the tolerance, and the gap isn't explained by mdr/gst/refund/
    chargeback/reserve (it won't be — those are already netted out above),
    raise an UNEXPLAINED_DEDUCTION exception with the gap amount.

EXCEPTIONS TO DETECT
    - MISSING_UTR: bank_df row for a matched batch has an empty/NaN "utr"
      field. Still count the batch as matched (via narration), but flag it.
    - UNEXPLAINED_DEDUCTION: see amount reconciliation above.

METRICS TO RETURN
    - "batch_match_rate": matched batches / total settlement batches
    - "total_batches": int
    - "matched_batches": int

TEST CONTRACT
    tests/test_pass1_batch_match.py checks that:
      - the batch with the known missing UTR is flagged MISSING_UTR
      - the batch with the known unexplained deduction is flagged
        UNEXPLAINED_DEDUCTION with an amount roughly matching the injected gap
      - batch_match_rate is 1.0 (every batch should still match via narration
        even when UTR is missing or amount doesn't fully reconcile)
"""

import pandas as pd
from src.schemas import DataContext, PassResult, Exception_, ExceptionCategory, AMOUNT_TOLERANCE

def run(ctx: DataContext) -> PassResult:
    settlement_df = ctx.settlement_df
    bank_df = ctx.bank_df
    reserve_df = ctx.reserve_df

    exceptions = []
    total_batches = settlement_df['settlement_id'].nunique()
    matched_batches = 0

    agg_settlement = settlement_df.groupby('settlement_id')[
        ['gross_amount', 'mdr_fee', 'gst_on_mdr', 'refund_amount', 'chargeback_amount']
    ].sum().reset_index()

    for _, row in agg_settlement.iterrows():
        s_id = row['settlement_id']
        ref_code = s_id[-8:]

        bank_matches = bank_df[bank_df['narration'].str.contains(ref_code, na=False)]

        if not bank_matches.empty:
            matched_batches += 1
            bank_row = bank_matches.iloc[0]

            utr = bank_row['utr']
            if pd.isna(utr) or str(utr).strip() == "":
                exceptions.append(Exception_(
                    settlement_id=s_id,
                    category=ExceptionCategory.MISSING_UTR,
                    description="Bank statement row missing UTR"
                ))

            reserve_row = reserve_df[reserve_df['settlement_id'] == s_id]
            reserve_hold = reserve_row.iloc[0]['reserve_hold_amount'] if not reserve_row.empty else 0.0
            reserve_released = reserve_row.iloc[0]['reserve_released_amount'] if not reserve_row.empty else 0.0

            expected_credit = (
                row['gross_amount']
                - row['mdr_fee']
                - row['gst_on_mdr']
                - row['refund_amount']
                - row['chargeback_amount']
                - reserve_hold
                + reserve_released
            )

            actual_credit = bank_row['credit_amount']

            if (expected_credit - actual_credit) > AMOUNT_TOLERANCE:
                exceptions.append(Exception_(
                    settlement_id=s_id,
                    category=ExceptionCategory.UNEXPLAINED_DEDUCTION,
                    description=f"Expected {expected_credit:.2f}, got {actual_credit:.2f}",
                    amount=expected_credit - actual_credit
                ))

    return PassResult(
        pass_name="Pass 1",
        exceptions=exceptions,
        metrics={
            "total_batches": total_batches,
            "matched_batches": matched_batches,
            "batch_match_rate": matched_batches / total_batches if total_batches > 0 else 0.0
        }
    )
