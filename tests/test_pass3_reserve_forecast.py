from src.matcher import pass3_reserve_forecast
from src.schemas import ExceptionCategory


def test_reserve_not_released_flagged(ctx, ground_truth):
    result = pass3_reserve_forecast.run(ctx)
    flagged = [
        e.settlement_id for e in result.exceptions
        if e.category == ExceptionCategory.RESERVE_NOT_RELEASED
    ]
    assert ground_truth["reserve_not_released_settlement_id"] in flagged


def test_no_false_positive_reserve_flags(ctx, ground_truth):
    result = pass3_reserve_forecast.run(ctx)
    flagged = [
        e.settlement_id for e in result.exceptions
        if e.category == ExceptionCategory.RESERVE_NOT_RELEASED
    ]
    # every other batch's reserve was fully released in the synthetic data
    assert flagged == [ground_truth["reserve_not_released_settlement_id"]]
