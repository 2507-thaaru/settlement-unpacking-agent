from src.matcher import pass5_cross_period
from src.schemas import ExceptionCategory


def test_cross_period_orders_flagged(ctx, ground_truth):
    result = pass5_cross_period.run(ctx)
    target_settlement = ground_truth["cross_period_settlement_id"]

    flagged_settlements = {
        e.settlement_id for e in result.exceptions
        if e.category == ExceptionCategory.CROSS_PERIOD_SETTLEMENT
    }
    assert target_settlement in flagged_settlements
