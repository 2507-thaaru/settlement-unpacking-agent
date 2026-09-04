# Settlement Unpacking Agent


An agent that explodes lumped Razorpay settlement credits back into their
components, tracks rolling reserve release, and catches GST-on-MDR ITC
leakage — three finance-ops loops most reconciliation tools treat separately,
closed here in one batch-explosion pipeline.

Full problem statement: [`docs/project-plan.md`](docs/project-plan.md)
Full architecture: [`docs/architecture.md`](docs/architecture.md)


## Repo structure

```
settlement-unpacking-agent/
├── data_generator/
│   └── generate_data.py        # synthetic dataset generator with injected noise
├── data/                        # generated CSVs + ground truth (regeneratable)
├── src/
│   ├── schemas.py               # the fixed data contract every pass builds against
│   ├── orchestrator.py          # fully implemented — chains passes, aggregates report
│   └── matcher/
│       ├── pass1_batch_match.py       # stub + full spec in docstring
│       ├── pass2_order_validation.py  # stub + full spec in docstring
│       ├── pass3_reserve_forecast.py  # stub + full spec in docstring
│       ├── pass4_gst_itc.py           # stub + full spec in docstring
│       └── pass5_cross_period.py      # stub + full spec in docstring (stretch)
├── app/
│   └── dashboard.py             # fully implemented Streamlit dashboard
├── tests/                        # executable spec — one file per pass, checked against ground truth
├── docs/
│   ├── project-plan.md          # problem statement & scope
│   ├── architecture.md          # module map, data flow, assumptions
│   └── agent-briefs/            # ready-to-paste Antigravity task briefs, one per pass
└── WHAT_BROKE.md                 # running log of build issues + fixes (submission requirement)

```


## System architecture

<img width="2172" height="724" alt="image" src="https://github.com/user-attachments/assets/34eed8b9-4d89-49a1-abcf-87980ee0cb77" />


## Running things

```bash
pip install -r requirements.txt

# regenerate synthetic data (optional, already generated)
cd data_generator && python generate_data.py --seed 42 --batches 18

# run the test suite (currently all fail with NotImplementedError — expected until passes are built)
pytest tests/ -v

# run the orchestrator directly
python -m src.orchestrator --data-dir data

# launch the dashboard
streamlit run app/dashboard.py
```



## Tech Stack
    Backend & AI Agent
    
    Python — Core backend and reconciliation logic
    FastAPI — REST API layer exposing the settlement agent
    Uvicorn — ASGI server used to run the FastAPI application
    Pandas — Processing and analysis of settlement, sales, bank, GST and reserve data
    Pydantic — Data validation and structured schemas
    Pytest — Automated testing of reconciliation passes
    Knowledge Graph — Dynamically generated in-memory graph representing relationships between settlements, orders, transactions, exceptions and reconciliation results
    Antigravity — Used to develop and orchestrate the backend settlement-unpacking agent
    Reconciliation Engine
    
    The backend uses a 5-pass reconciliation pipeline:
    
    Batch Matching — Matches settlement batches against expected amounts
    Order Validation — Validates individual orders and transaction relationships
    Reserve Forecasting — Analyzes reserve movements and forecasts expected values
    GST / ITC Validation — Reconciles GST and input-tax-credit related data
    Cross-Period Reconciliation — Identifies discrepancies spanning multiple settlement periods
    
    Frontend
    
    React 19 — UI framework
    TanStack Start — Full-stack React framework with SSR
    TanStack Router — File-based routing
    TanStack Query — API state management and data fetching
    Vite — Frontend build tooling
    Tailwind CSS — Styling
    shadcn/ui — UI component system
    Recharts — Data visualization and dashboards
    Lovable — Used to build and iterate on the frontend
    API & System Architecture
    REST APIs — Communication between frontend and backend
    Server-side API Proxy — Frontend requests are routed through /api/proxy/* before reaching the backend
    Environment-based Configuration — Backend URL and CORS configuration are managed through environment variables
    Dynamic Knowledge Graph — Rebuilt from the current reconciliation data rather than relying on a static graph
    
    Deployment
    
    Backend: Render
    FastAPI deployed as a Web Service
    Uvicorn production server
    Public HTTPS endpoint
    Frontend: Lovable
    Production frontend hosted on Lovable
    SSR application deployed with TanStack Start/Nitro
    Version Control: GitHub
    Data Layer
    CSV-based synthetic financial datasets
    Settlement reports
    Sales ledger
    
    Bank statements
    
    GST invoices
    Reserve ledger
    Injected exceptions / ground-truth data
    In-memory processing — No external database is required for the current prototype.


                    ┌─────────────────────────┐
                    │      Razorpay User      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ React + TanStack Start. │
                    │       Frontend          │
                    └────────────┬────────────┘
                                 │
                            /api/proxy/*
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI Backend    │
                    │       on Render         │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Settlement Agent      │
                    │     Python + Pandas     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
          ┌──────────────────┐      ┌──────────────────┐
          │ 5 Reconciliation │      │ Dynamic Knowledge│
          │     Passes       │─────▶│      Graph       │
          └──────────────────┘      └──────────────────┘
                    │
                    ▼
          ┌──────────────────────┐
          │ Synthetic Financial  │
          │       Data           │
          └──────────────────────┘


### Injected exceptions (ground truth)

The generator always injects exactly six known faults so the matching
pipeline's recall can be measured objectively:

1. A settlement batch with a **missing UTR** in the bank statement → Pass 1
2. A batch with an **unexplained deduction** not attributable to any known field → Pass 1
3. A batch charged **MDR at the wrong rate** → Pass 2
4. A batch whose **rolling reserve is never released**, even past the liability window → Pass 3
5. A monthly **GST invoice that under-reports** the GST-on-MDR actually charged → Pass 4
6. A **cross-period settlement** (order placed in one GST month, settled in the next) → Pass 5 (stretch)

`bank_statement_with_ground_truth.csv` includes a `settlement_id_hint`
column for pipeline self-checks during development only — this column
does not exist in real bank data and must never be used by the actual
matching logic, only by the test suite.
