"""
Orchestrator — chains all matching passes and produces the final report.

This file is fully implemented, not a stub. It should not need agent
changes unless a pass's function signature changes.

Run it directly:
    python -m src.orchestrator --data-dir data
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.schemas import DataContext, load_all_data
from src.matcher import (
    pass1_batch_match,
    pass2_order_validation,
    pass3_reserve_forecast,
    pass4_gst_itc,
    pass5_cross_period,
)

PASSES = [
    ("pass1_batch_match", pass1_batch_match),
    ("pass2_order_validation", pass2_order_validation),
    ("pass3_reserve_forecast", pass3_reserve_forecast),
    ("pass4_gst_itc", pass4_gst_itc),
    ("pass5_cross_period", pass5_cross_period),  # stretch; fine if still NotImplementedError
]


def run_all(ctx: DataContext) -> dict:
    """Run every pass. A pass that raises NotImplementedError is recorded
    as 'not_implemented' rather than crashing the whole report, so the
    dashboard and CLI stay usable while the pipeline is still being built."""
    report = {"passes": {}, "all_exceptions": [], "combined_metrics": {}}

    for name, module in PASSES:
        try:
            result = module.run(ctx)
            report["passes"][name] = {
                "status": "ok",
                "metrics": result.metrics,
                "exception_count": len(result.exceptions),
            }
            report["all_exceptions"].extend(e.to_dict() for e in result.exceptions)
            report["combined_metrics"][name] = result.metrics
        except NotImplementedError as e:
            report["passes"][name] = {"status": "not_implemented", "detail": str(e)}
        except Exception as e:  # noqa: BLE001 - surface any real bug, don't hide it
            report["passes"][name] = {"status": "error", "detail": f"{type(e).__name__}: {e}"}

    implemented = [p for p in report["passes"].values() if p["status"] == "ok"]
    report["summary"] = {
        "passes_implemented": len(implemented),
        "passes_total": len(PASSES),
        "total_exceptions_found": len(report["all_exceptions"]),
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=str, default="data")
    parser.add_argument("--out", type=str, default=None, help="optional path to write the JSON report")
    args = parser.parse_args()

    ctx = load_all_data(args.data_dir)
    report = run_all(ctx)

    print(json.dumps(report, indent=2, default=str))

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, default=str))
        print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()
