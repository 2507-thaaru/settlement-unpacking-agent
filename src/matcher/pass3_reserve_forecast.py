"""
Pass 3 — Rolling reserve tracking and release forecast.

OBJECTIVE
    Using reserve_ledger.csv alone (settlement_id, settlement_date,
    reserve_hold_amount, reserve_released_amount, release_due_date),
    determine which batches have reserve still held, and produce a
    forward cash-availability forecast.

LOGIC
    For each row in reserve_df:
      - still_held = reserve_hold_amount - reserve_released_amount
      - if still_held > schemas.AMOUNT_TOLERANCE:
          - if release_due_date (parsed as a date) < schemas.AS_OF_DATE:
              this reserve is PAST its release window and still not
              released -> raise RESERVE_NOT_RELEASED with the still_held
              amount.
          - else:
              this reserve is legitimately still within its holding
              window -> not an exception, but include it in the forecast
              output as "pending release on <release_due_date>".

OUTPUT
    Return a forecast as part of output_df or metrics: for every batch
    with still_held > tolerance, list settlement_id, still_held amount,
    and release_due_date, sorted by release_due_date ascending. This is
    the "cash becoming available, by date" forecast the project plan
    promises — build it even for batches that aren't exceptions.

EXCEPTIONS TO DETECT
    - RESERVE_NOT_RELEASED: still_held > tolerance AND release_due_date
      has already passed relative to AS_OF_DATE.

METRICS TO RETURN
    - "total_reserve_held": sum of reserve_hold_amount across all batches
    - "total_reserve_released": sum of reserve_released_amount
    - "total_still_held": sum of (hold - released) across all batches
    - "batches_with_overdue_reserve": int

TEST CONTRACT
    tests/test_pass3_reserve_forecast.py checks that:
      - the known reserve_not_released_settlement_id is flagged
        RESERVE_NOT_RELEASED
      - no other batch is incorrectly flagged (every other batch's
        reserve_released_amount equals its reserve_hold_amount in the
        synthetic data, so they should be clean)
"""

import pandas as pd
from src.schemas import DataContext, PassResult, Exception_, ExceptionCategory, AMOUNT_TOLERANCE, AS_OF_DATE

def run(ctx: DataContext) -> PassResult:
    exceptions = []
    
    reserve_df = ctx.reserve_df.copy()
    reserve_df["release_due_date_parsed"] = pd.to_datetime(reserve_df["release_due_date"]).dt.date
    reserve_df["still_held"] = reserve_df["reserve_hold_amount"] - reserve_df["reserve_released_amount"]
    
    forecast_list = []
    total_held = reserve_df["reserve_hold_amount"].sum()
    total_released = reserve_df["reserve_released_amount"].sum()
    total_still_held = reserve_df["still_held"].sum()
    batches_overdue = 0
    
    for _, row in reserve_df.iterrows():
        still_held = row["still_held"]
        if still_held > AMOUNT_TOLERANCE:
            forecast_list.append({
                "settlement_id": row["settlement_id"],
                "still_held": still_held,
                "release_due_date": row["release_due_date"]
            })
            if row["release_due_date_parsed"] < AS_OF_DATE:
                batches_overdue += 1
                exceptions.append(Exception_(
                    settlement_id=row["settlement_id"],
                    category=ExceptionCategory.RESERVE_NOT_RELEASED,
                    description=f"Reserve not released. Still held: {still_held}, Due: {row['release_due_date']}",
                    amount=still_held
                ))
                
    # Sort forecast list by release_due_date
    forecast_list.sort(key=lambda x: pd.to_datetime(x["release_due_date"]).date())
    
    metrics = {
        "total_reserve_held": float(total_held),
        "total_reserve_released": float(total_released),
        "total_still_held": float(total_still_held),
        "batches_with_overdue_reserve": int(batches_overdue),
        "forecast": forecast_list
    }
    
    return PassResult(
        pass_name="pass3_reserve_forecast",
        exceptions=exceptions,
        metrics=metrics
    )
