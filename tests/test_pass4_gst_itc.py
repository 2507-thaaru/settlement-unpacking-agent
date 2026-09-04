from src.matcher import pass4_gst_itc
from src.schemas import ExceptionCategory


def test_gst_itc_mismatch_period_flagged(ctx, ground_truth):
    result = pass4_gst_itc.run(ctx)
    flagged_periods = [
        e.description for e in result.exceptions
        if e.category == ExceptionCategory.GST_ITC_MISMATCH
    ]
    target_period = ground_truth["gst_invoice_mismatch_period"]
    assert any(target_period in desc for desc in flagged_periods), (
        f"expected the mismatched period {target_period} to appear in an exception description"
    )


def test_only_one_period_flagged(ctx):
    result = pass4_gst_itc.run(ctx)
    flagged = [e for e in result.exceptions if e.category == ExceptionCategory.GST_ITC_MISMATCH]
    assert len(flagged) == 1, "only one of the two synthetic GST periods has an injected mismatch"
