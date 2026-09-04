# Agent brief — Pass 3: Rolling reserve tracking and release forecast

## Paste this into Antigravity's Manager surface as the task:

> Implement `src/matcher/pass3_reserve_forecast.py` in this repo. Full
> spec is in that file's module docstring. Work only from
> `reserve_ledger.csv` (settlement_id, settlement_date,
> reserve_hold_amount, reserve_released_amount, release_due_date). For
> each batch, compute still_held = hold - released. If still_held is
> above `schemas.AMOUNT_TOLERANCE` and `release_due_date` is before
> `schemas.AS_OF_DATE`, flag `RESERVE_NOT_RELEASED`. Also build a
> forward release forecast — every batch with reserve still held,
> sorted by release_due_date, whether or not it's an exception yet
> (that forecast is a headline feature of the pitch, not just an
> exception list). Return a `PassResult` per `src/schemas.py`, with the
> forecast in `metrics` or `output_df`. When done, run
> `pytest tests/test_pass3_reserve_forecast.py -v` and confirm both
> tests pass — including the no-false-positives test, since every other
> batch in the synthetic data has its reserve fully released. Log
> anything that breaks in `WHAT_BROKE.md`.

## Context files to give the agent
- `src/matcher/pass3_reserve_forecast.py` (the stub with full spec)
- `src/schemas.py`
- `tests/test_pass3_reserve_forecast.py`
- `data/reserve_ledger.csv`

## Definition of done
- `pytest tests/test_pass3_reserve_forecast.py -v` — all tests pass
- `python -m src.orchestrator --data-dir data` shows `pass3_reserve_forecast` as `"status": "ok"`
- The forecast output actually appears (not just the exception flag) — this is what makes the pitch's "forward cash forecaster" claim true
