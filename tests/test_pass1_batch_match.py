from src.matcher import pass1_batch_match
from src.schemas import ExceptionCategory


def test_missing_utr_flagged(ctx, ground_truth):
    result = pass1_batch_match.run(ctx)
    flagged = [e.settlement_id for e in result.exceptions if e.category == ExceptionCategory.MISSING_UTR]
    assert ground_truth["missing_utr_settlement_id"] in flagged


def test_unexplained_deduction_flagged(ctx, ground_truth):
    result = pass1_batch_match.run(ctx)
    flagged = {
        e.settlement_id: e.amount
        for e in result.exceptions
        if e.category == ExceptionCategory.UNEXPLAINED_DEDUCTION
    }
    target = ground_truth["unexplained_deduction_settlement_id"]
    assert target in flagged
    assert flagged[target] is not None and flagged[target] > 0


def test_batch_match_rate_is_complete(ctx):
    result = pass1_batch_match.run(ctx)
    assert result.metrics.get("batch_match_rate") == 1.0
