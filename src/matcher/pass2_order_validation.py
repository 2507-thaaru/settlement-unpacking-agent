"""
Pass 2 — Order-level explosion and validation.

OBJECTIVE
    Explode each settlement batch into its individual order-level rows
    (settlement_df is already order-level — one row per order_id under a
    shared settlement_id) and validate each row against sales_ledger.csv.

VALIDATIONS
    1. Existence check: every order_id in settlement_df should have a
       matching order_id in ledger_df. If not, that's a data-integrity
       exception (not one of the six injected faults, but your logic
       should still handle it gracefully rather than crashing).
    2. Amount check: settlement_df["gross_amount"] should equal
       ledger_df["invoice_amount"] for the same order_id, within
       schemas.AMOUNT_TOLERANCE.
    3. MDR rate check: mdr_fee should equal gross_amount * schemas.MDR_RATE,
       within tolerance. If it doesn't, raise MDR_RATE_MISMATCH with the
       settlement_id, order_id, and the delta amount.

EXCEPTIONS TO DETECT
    - MDR_RATE_MISMATCH: mdr_fee doesn't match gross_amount * MDR_RATE
      within tolerance, at the order level. (One whole settlement batch in
      the synthetic data has every order overcharged by ~0.5 percentage
      points — your check should catch every order row in that batch, not
      just one.)

METRICS TO RETURN
    - "order_match_rate": orders found in both settlement_df and ledger_df,
      with amounts reconciling / total orders in settlement_df
    - "total_orders": int
    - "orders_with_mdr_mismatch": int

TEST CONTRACT
    tests/test_pass2_order_validation.py checks that:
      - every order row belonging to the known mdr_rate_mismatch_settlement_id
        is flagged MDR_RATE_MISMATCH
      - order_match_rate reflects that MDR mismatches don't affect
        existence/amount matching, only the rate check
"""

import pandas as pd
from src.schemas import DataContext, PassResult, Exception_, ExceptionCategory, MDR_RATE, AMOUNT_TOLERANCE


def run(ctx: DataContext) -> PassResult:
    settlement_df = ctx.settlement_df
    ledger_df = ctx.ledger_df
    
    exceptions = []
    
    total_orders = len(settlement_df)
    orders_with_mdr_mismatch = 0
    orders_matched = 0
    
    merged_df = settlement_df.merge(ledger_df, on="order_id", how="left")
    
    for _, row in merged_df.iterrows():
        order_id = row["order_id"]
        settlement_id = row["settlement_id"]
        gross_amount = row["gross_amount"]
        mdr_fee = row["mdr_fee"]
        invoice_amount = row["invoice_amount"]
        
        is_matched = False
        if pd.notna(invoice_amount):
            if abs(gross_amount - invoice_amount) <= AMOUNT_TOLERANCE:
                is_matched = True
                
        if is_matched:
            orders_matched += 1
            
        expected_mdr = gross_amount * MDR_RATE
        if abs(mdr_fee - expected_mdr) > AMOUNT_TOLERANCE:
            exceptions.append(
                Exception_(
                    settlement_id=settlement_id,
                    category=ExceptionCategory.MDR_RATE_MISMATCH,
                    description=f"MDR fee mismatch: expected {expected_mdr:.2f}, got {mdr_fee:.2f}",
                    order_id=order_id,
                    amount=round(mdr_fee - expected_mdr, 2)
                )
            )
            orders_with_mdr_mismatch += 1
            
    order_match_rate = orders_matched / total_orders if total_orders > 0 else 0.0
    
    metrics = {
        "order_match_rate": order_match_rate,
        "total_orders": total_orders,
        "orders_with_mdr_mismatch": orders_with_mdr_mismatch,
    }
    
    return PassResult(
        pass_name="Order validation",
        exceptions=exceptions,
        metrics=metrics
    )
