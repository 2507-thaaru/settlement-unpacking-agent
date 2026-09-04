from src.matcher import pass2_order_validation
from src.schemas import ExceptionCategory


def test_mdr_rate_mismatch_flagged_for_every_order_in_batch(ctx, ground_truth):
    result = pass2_order_validation.run(ctx)
    target_settlement = ground_truth["mdr_rate_mismatch_settlement_id"]

    flagged_settlements = {
        e.settlement_id for e in result.exceptions
        if e.category == ExceptionCategory.MDR_RATE_MISMATCH
    }
    assert target_settlement in flagged_settlements

    expected_order_count = (ctx.settlement_df["settlement_id"] == target_settlement).sum()
    flagged_order_count = sum(
        1 for e in result.exceptions
        if e.category == ExceptionCategory.MDR_RATE_MISMATCH and e.settlement_id == target_settlement
    )
    assert flagged_order_count == expected_order_count, (
        "every order row in the mismatched batch should be flagged, not just one"
    )
