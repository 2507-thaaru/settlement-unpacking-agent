"""
Pass 4 — GST-on-MDR ITC leakage detection.

OBJECTIVE
    Cross-check the GST-on-MDR actually charged (as recorded per-order in
    settlement_df) against what Razorpay's monthly GST tax invoice
    (invoice_df) says was charged. A mismatch means the merchant either
    over- or under-claims Input Tax Credit relative to what was actually
    paid.

LOGIC
    1. Derive each settlement's billing period from settlement_date
       (format "YYYY-MM", matching invoice_df["period"]).
    2. Group settlement_df by that period and sum gst_on_mdr ->
       "actual_gst_from_settlements".
    3. For each period present in invoice_df, compare
       invoice_df["gst_on_mdr_amount"] (what the invoice claims) against
       actual_gst_from_settlements for that period, within
       schemas.AMOUNT_TOLERANCE.
    4. If they differ by more than tolerance, raise GST_ITC_MISMATCH with
       the period and the gap amount (this is the ITC leakage figure).

EXCEPTIONS TO DETECT
    - GST_ITC_MISMATCH: invoice-reported GST-on-MDR differs from the sum
      of GST-on-MDR actually recorded across settlements for that period.

METRICS TO RETURN
    - "periods_checked": int
    - "periods_with_mismatch": int
    - "total_itc_leakage": sum of absolute gap amounts across all
      mismatched periods (the headline number for the pitch)

TEST CONTRACT
    tests/test_pass4_gst_itc.py checks that:
      - the known gst_invoice_mismatch_period is flagged GST_ITC_MISMATCH
      - the other period in the synthetic data is NOT flagged
"""

from src.schemas import DataContext, PassResult, Exception_, ExceptionCategory, AMOUNT_TOLERANCE


def run(ctx: DataContext) -> PassResult:
    settlement_df = ctx.settlement_df
    invoice_df = ctx.invoice_df

    periods = settlement_df['settlement_date'].astype(str).str[:7]
    actual_gst_from_settlements = settlement_df.groupby(periods)['gst_on_mdr'].sum()

    exceptions = []
    periods_checked = 0
    periods_with_mismatch = 0
    total_itc_leakage = 0.0

    for _, row in invoice_df.iterrows():
        period = str(row['period'])
        claimed_gst = float(row['gst_on_mdr_amount'])
        
        periods_checked += 1
        
        actual_gst = actual_gst_from_settlements.get(period, 0.0)
        diff = abs(claimed_gst - actual_gst)
        
        if diff > AMOUNT_TOLERANCE:
            periods_with_mismatch += 1
            total_itc_leakage += diff
            
            ex = Exception_(
                settlement_id=f"PERIOD-{period}",
                category=ExceptionCategory.GST_ITC_MISMATCH,
                description=f"GST ITC Mismatch for period {period}",
                amount=diff
            )
            exceptions.append(ex)

    return PassResult(
        pass_name="Pass 4 - GST-on-MDR ITC",
        exceptions=exceptions,
        metrics={
            "periods_checked": periods_checked,
            "periods_with_mismatch": periods_with_mismatch,
            "total_itc_leakage": total_itc_leakage
        }
    )
