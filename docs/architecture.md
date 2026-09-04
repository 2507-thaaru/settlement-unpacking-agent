# Architecture

## Data flow

```
data_generator/generate_data.py
        |
        v
   data/*.csv  (settlement_report, bank_statement, gst_invoice,
                sales_ledger, reserve_ledger, injected_exceptions.json)
        |
        v
src/schemas.py  --  load_all_data()  -->  DataContext
        |
        v
   ---------------------------------------------------------
   |         |          |          |          |            |
Pass 1    Pass 2     Pass 3     Pass 4     Pass 5           |
(batch    (order     (reserve   (GST       (cross-period,   |
 match)   validate)  forecast)  ITC)        stretch)        |
   |         |          |          |          |             |
   ---------------------------------------------------------
        |
        v
src/orchestrator.py  --  run_all()  -->  aggregated report
        |
        v
   app/Home.py + app/pages/*  (Streamlit, multi-page)   tests/  (pytest, ground-truth checks)
```

## Why this shape

Each pass reads from the shared `DataContext` (loaded once) and returns a
`PassResult` — a fixed shape of exceptions + metrics + optional enriched
data. No pass writes to another pass's output, and no pass depends on
another pass having already run. That's deliberate: it means Passes 1–4
(and 5, stretch) can be built independently and in parallel, then wired
together by `orchestrator.py`, which is the only file that imposes an
order.

## Module contracts

- **`src/schemas.py`** — the fixed contract. Column names, business
  constants (MDR rate, GST rate, reserve rate, release window), the
  exception taxonomy, and the `PassResult`/`DataContext` dataclasses.
  Nothing outside this file should hardcode a column name or a rate.
- **`src/matcher/pass{1..5}_*.py`** — one exception-detection concern
  each. Every file currently raises `NotImplementedError` with a full
  spec in its docstring — that spec is deliberately detailed enough that
  each pass can be built without reading any other pass's code.
- **`src/orchestrator.py`** — fully implemented. Runs every pass, catches
  `NotImplementedError` so a partially-built pipeline still produces a
  valid (partial) report instead of crashing, and aggregates exceptions
  and metrics into one JSON-serializable report.
- **`app/Home.py` + `app/pages/`** — fully implemented, multi-page. Home
  introduces the problem, Input Data shows the source files, How It Works
  is a graphviz diagram of the pipeline with the exact formulas, and
  Results Dashboard (unchanged from the original single-page version)
  renders pass status, exception charts, and the reserve forecast.
  `app/common.py` holds the shared theme and cached data/report loaders.
  Safe to run from Day 1 onward.
- **`tests/test_pass*.py`** — the executable spec. Each test asserts that
  a pass catches its assigned injected exception from
  `injected_exceptions.json`, using the real ground truth rather than a
  hand-picked example. A pass is "done" when its test file is green.

## Exception -> pass mapping

| Exception category | Pass | Data it needs |
|---|---|---|
| `MISSING_UTR` | 1 | settlement_report, bank_statement |
| `UNEXPLAINED_DEDUCTION` | 1 | settlement_report, bank_statement, reserve_ledger |
| `MDR_RATE_MISMATCH` | 2 | settlement_report, sales_ledger |
| `RESERVE_NOT_RELEASED` | 3 | reserve_ledger |
| `GST_ITC_MISMATCH` | 4 | settlement_report, gst_invoice |
| `CROSS_PERIOD_SETTLEMENT` | 5 (stretch) | settlement_report |

## Assumptions baked into the data and code (state these in the pitch)

- Reserve is held at 5% of batch gross and released after a 120-day
  chargeback-liability window — a commonly cited industry figure, not
  Razorpay's actual disclosed policy (no public source confirms
  Razorpay's specific rate or window). Documented in `schemas.py` and
  the project plan as an explicit assumption.
- `AS_OF_DATE` in `schemas.py` is a fixed reference "today" for judging
  whether a reserve release is overdue. It's hardcoded for the default
  synthetic dataset — regenerate data or move this date if you change
  the batch date range.
- Amount comparisons use a ₹1 tolerance (`AMOUNT_TOLERANCE`) to absorb
  floating-point rounding noise without masking real discrepancies.

## Build order

1. `src/schemas.py` and `data/` — already done.
2. Passes 1–4, in any order or in parallel — each is self-contained.
3. `src/orchestrator.py` — already done, shouldn't need changes.
4. `app/dashboard.py` — already done, but re-run it after each pass to
   sanity-check the output looks right.
5. Pass 5 — only after 1–4 are green.
6. Polish: better dashboard styling, README status table kept honest,
   `WHAT_BROKE.md` kept current.
