import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure repo root is on sys.path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.schemas import load_all_data, ExceptionCategory
from src.orchestrator import run_all

DATA_DIR_ENV = os.getenv("DATA_DIR")
DATA_DIR = Path(DATA_DIR_ENV) if DATA_DIR_ENV else BASE_DIR / "data"

app = FastAPI(
    title="Settlement Unpacking Agent API",
    description="REST API backend for Razorpay settlement unpacking, multi-pass reconciliation, exception detection, rolling reserve forecasting, and dynamic knowledge graph generation.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS (environment-driven with fallback to permissive default for local development)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env and allowed_origins_env.strip():
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PASS_TO_EXCEPTIONS = {
    "pass1_batch_match": ["MISSING_UTR", "UNEXPLAINED_DEDUCTION"],
    "pass2_order_validation": ["MDR_RATE_MISMATCH"],
    "pass3_reserve_forecast": ["RESERVE_NOT_RELEASED"],
    "pass4_gst_itc": ["GST_ITC_MISMATCH"],
    "pass5_cross_period": ["CROSS_PERIOD_SETTLEMENT"],
}

PASS_LABELS = {
    "pass1_batch_match": "Pass 1: Batch Match",
    "pass2_order_validation": "Pass 2: Order Validation",
    "pass3_reserve_forecast": "Pass 3: Reserve Forecast",
    "pass4_gst_itc": "Pass 4: GST ITC Check",
    "pass5_cross_period": "Pass 5: Cross-Period",
}


def get_current_context():
    try:
        return load_all_data(DATA_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load datasets: {str(e)}")


def get_current_report():
    ctx = get_current_context()
    return run_all(ctx), ctx


def build_knowledge_graph_data(ctx, report):
    exceptions_by_category = {}
    for e in report.get("all_exceptions", []):
        cat = e.get("category", "")
        exceptions_by_category[cat] = exceptions_by_category.get(cat, 0) + 1

    nodes = []
    edges = []

    # 1. Source Data Nodes
    data_sources = [
        {"id": "settlement", "label": "settlement_report.csv", "rows": len(ctx.settlement_df), "type": "data_source"},
        {"id": "bank", "label": "bank_statement.csv", "rows": len(ctx.bank_df), "type": "data_source"},
        {"id": "invoice", "label": "gst_invoice.csv", "rows": len(ctx.invoice_df), "type": "data_source"},
        {"id": "ledger", "label": "sales_ledger.csv", "rows": len(ctx.ledger_df), "type": "data_source"},
        {"id": "reserve", "label": "reserve_ledger.csv", "rows": len(ctx.reserve_df), "type": "data_source"},
    ]
    for ds in data_sources:
        nodes.append({
            "id": ds["id"],
            "label": f"{ds['label']}\n({ds['rows']} rows)",
            "category": "source_data",
            "rows": ds["rows"],
            "color": "#DCE8FF",
            "borderColor": "#3395FF",
            "fontColor": "#0F172A",
            "shape": "ellipse"
        })

    # 2. Matching Pass Nodes
    for pass_key, label in PASS_LABELS.items():
        info = report.get("passes", {}).get(pass_key, {})
        status = info.get("status", "not_implemented")
        count = info.get("exception_count", 0)

        if status == "ok" and count == 0:
            color = "#16A34A"  # clean
            status_text = "clean"
        elif status == "ok":
            color = "#D97706"  # found exceptions
            status_text = f"{count} exceptions"
        elif status == "not_implemented":
            color = "#94A3B8"
            status_text = "not implemented"
        else:
            color = "#DC2626"
            status_text = "error"

        nodes.append({
            "id": pass_key,
            "label": f"{label}\n({status_text})",
            "category": "pass",
            "status": status,
            "exception_count": count,
            "color": color,
            "fontColor": "#FFFFFF",
            "shape": "box"
        })

    # 3. Exception Category Nodes
    for pass_key, cats in PASS_TO_EXCEPTIONS.items():
        for cat in cats:
            count = exceptions_by_category.get(cat, 0)
            color = "#FCD34D" if count > 0 else "#E5E9F2"
            fontColor = "#0F172A" if count > 0 else "#94A3B8"
            nodes.append({
                "id": cat,
                "label": f"{cat}\n({count})",
                "category": "exception_type",
                "count": count,
                "color": color,
                "fontColor": fontColor,
                "shape": "note"
            })

    # 4. Aggregator Nodes
    total_exceptions = len(report.get("all_exceptions", []))
    nodes.append({
        "id": "orchestrator",
        "label": "Orchestrator",
        "category": "orchestration",
        "color": "#0B2D6B",
        "fontColor": "#FFFFFF",
        "shape": "box"
    })
    nodes.append({
        "id": "report",
        "label": f"Report\n({total_exceptions} total exceptions)",
        "category": "report",
        "color": "#16A34A" if total_exceptions or report.get("summary", {}).get("passes_implemented") else "#94A3B8",
        "fontColor": "#FFFFFF",
        "shape": "box"
    })

    # Edges: Data -> Passes
    edges.append({"from": "settlement", "to": "pass1_batch_match"})
    edges.append({"from": "bank", "to": "pass1_batch_match"})
    edges.append({"from": "reserve", "to": "pass1_batch_match"})
    edges.append({"from": "settlement", "to": "pass2_order_validation"})
    edges.append({"from": "ledger", "to": "pass2_order_validation"})
    edges.append({"from": "reserve", "to": "pass3_reserve_forecast"})
    edges.append({"from": "settlement", "to": "pass4_gst_itc"})
    edges.append({"from": "invoice", "to": "pass4_gst_itc"})
    edges.append({"from": "settlement", "to": "pass5_cross_period"})

    # Edges: Passes -> Exceptions
    edges.append({"from": "pass1_batch_match", "to": "MISSING_UTR"})
    edges.append({"from": "pass1_batch_match", "to": "UNEXPLAINED_DEDUCTION"})
    edges.append({"from": "pass2_order_validation", "to": "MDR_RATE_MISMATCH"})
    edges.append({"from": "pass3_reserve_forecast", "to": "RESERVE_NOT_RELEASED"})
    edges.append({"from": "pass4_gst_itc", "to": "GST_ITC_MISMATCH"})
    edges.append({"from": "pass5_cross_period", "to": "CROSS_PERIOD_SETTLEMENT"})

    # Edges: Exceptions -> Orchestrator -> Report
    for cat in ["MISSING_UTR", "UNEXPLAINED_DEDUCTION", "MDR_RATE_MISMATCH", "RESERVE_NOT_RELEASED", "GST_ITC_MISMATCH", "CROSS_PERIOD_SETTLEMENT"]:
        edges.append({"from": cat, "to": "orchestrator"})
    edges.append({"from": "orchestrator", "to": "report"})

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


def generate_dot_graph(ctx, report):
    graph_data = build_knowledge_graph_data(ctx, report)
    node_lines = []
    for n in graph_data["nodes"]:
        shape = n.get("shape", "box")
        style = "filled,rounded" if shape == "box" else "filled"
        color = n.get("color", "#FFFFFF")
        fontColor = n.get("fontColor", "#000000")
        label = n.get("label", "").replace("\n", "\\n")
        node_lines.append(f'    {n["id"]} [label="{label}", shape={shape}, style="{style}", fillcolor="{color}", fontcolor="{fontColor}"];')

    edge_lines = []
    for e in graph_data["edges"]:
        edge_lines.append(f'    {e["from"]} -> {e["to"]};')

    dot = "digraph G {\n    rankdir=LR;\n    bgcolor=\"transparent\";\n    node [fontname=\"Helvetica\", fontsize=11];\n    edge [color=\"#94A3B8\"];\n"
    dot += "\n".join(node_lines) + "\n"
    dot += "\n".join(edge_lines) + "\n}"
    return dot


@app.get("/", tags=["General"])
def root():
    return {
        "service": "Settlement Unpacking Agent API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "online",
        "endpoints": [
            "/health",
            "/api/summary",
            "/api/report",
            "/api/passes",
            "/api/exceptions",
            "/api/exceptions/grouped",
            "/api/forecast",
            "/api/graph",
            "/api/graph/dot",
            "/api/pipeline",
            "/api/data",
            "/api/data/{dataset_name}",
            "/api/run",
        ],
    }


@app.get("/health", tags=["General"])
def health():
    return {"status": "ok", "service": "settlement-unpacking-api"}


@app.get("/api/summary", tags=["Reconciliation"])
def get_summary():
    report, ctx = get_current_report()
    summary = report.get("summary", {})
    return {
        "passes_implemented": summary.get("passes_implemented", 0),
        "passes_total": summary.get("passes_total", 5),
        "total_exceptions_found": summary.get("total_exceptions_found", 0),
        "total_batches": ctx.settlement_df["settlement_id"].nunique(),
        "total_orders": len(ctx.settlement_df),
        "total_bank_credits": len(ctx.bank_df),
    }


@app.get("/api/report", tags=["Reconciliation"])
def get_full_report():
    report, _ = get_current_report()
    return report


@app.get("/api/passes", tags=["Reconciliation"])
def get_passes():
    report, _ = get_current_report()
    passes_data = []
    for pass_name, info in report.get("passes", {}).items():
        passes_data.append({
            "pass_name": pass_name,
            "status": info.get("status"),
            "exception_count": info.get("exception_count", 0),
            "metrics": info.get("metrics", {}),
            "detail": info.get("detail"),
        })
    return passes_data


@app.get("/api/graph", tags=["Knowledge Graph"])
@app.get("/api/knowledge-graph", tags=["Knowledge Graph"])
def get_knowledge_graph():
    report, ctx = get_current_report()
    return build_knowledge_graph_data(ctx, report)


@app.get("/api/graph/dot", tags=["Knowledge Graph"])
def get_graphviz_dot():
    report, ctx = get_current_report()
    return {
        "dot": generate_dot_graph(ctx, report)
    }


@app.get("/api/pipeline", tags=["Knowledge Graph"])
def get_pipeline_overview():
    report, ctx = get_current_report()
    return {
        "summary": report.get("summary", {}),
        "passes": report.get("passes", {}),
        "graph": build_knowledge_graph_data(ctx, report),
    }


@app.get("/api/exceptions", tags=["Exceptions"])
def get_exceptions(category: Optional[str] = Query(None, description="Filter by exception category")):
    report, _ = get_current_report()
    exceptions = report.get("all_exceptions", [])
    if category:
        category_clean = category.strip().upper()
        exceptions = [e for e in exceptions if e.get("category", "").upper() == category_clean]
    return {
        "count": len(exceptions),
        "exceptions": exceptions,
    }


@app.get("/api/exceptions/grouped", tags=["Exceptions"])
def get_grouped_exceptions():
    report, _ = get_current_report()
    exceptions = report.get("all_exceptions", [])
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for e in exceptions:
        cat = e.get("category", "UNKNOWN")
        grouped.setdefault(cat, []).append(e)

    summary_by_cat = {cat: len(items) for cat, items in grouped.items()}
    return {
        "total_exceptions": len(exceptions),
        "category_counts": summary_by_cat,
        "grouped": grouped,
    }


@app.get("/api/forecast", tags=["Reserve Forecast"])
def get_forecast():
    report, _ = get_current_report()
    pass3_metrics = report.get("combined_metrics", {}).get("pass3_reserve_forecast", {})
    return {
        "total_reserve_held": pass3_metrics.get("total_reserve_held", 0.0),
        "total_reserve_released": pass3_metrics.get("total_reserve_released", 0.0),
        "total_still_held": pass3_metrics.get("total_still_held", 0.0),
        "batches_with_overdue_reserve": pass3_metrics.get("batches_with_overdue_reserve", 0),
        "forecast_schedule": pass3_metrics.get("forecast", []),
    }


@app.get("/api/data", tags=["Datasets"])
def list_datasets():
    ctx = get_current_context()
    return {
        "datasets": [
            {"name": "settlement_report", "description": "Order-level settlement export rows", "rows": len(ctx.settlement_df)},
            {"name": "bank_statement", "description": "Bank NEFT statement credits", "rows": len(ctx.bank_df)},
            {"name": "gst_invoice", "description": "Monthly GST tax invoices on MDR", "rows": len(ctx.invoice_df)},
            {"name": "sales_ledger", "description": "Merchant sales ledger records", "rows": len(ctx.ledger_df)},
            {"name": "reserve_ledger", "description": "Rolling reserve tracking per batch", "rows": len(ctx.reserve_df)},
        ]
    }


@app.get("/api/data/{dataset_name}", tags=["Datasets"])
def get_dataset(dataset_name: str, limit: Optional[int] = Query(100, ge=1, le=5000), offset: Optional[int] = Query(0, ge=0)):
    ctx = get_current_context()
    name_clean = dataset_name.lower().strip()

    df_map = {
        "settlement_report": ctx.settlement_df,
        "bank_statement": ctx.bank_df,
        "gst_invoice": ctx.invoice_df,
        "sales_ledger": ctx.ledger_df,
        "reserve_ledger": ctx.reserve_df,
    }

    if name_clean not in df_map:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_name}' not found. Valid choices: {list(df_map.keys())}")

    target_df = df_map[name_clean]
    total_rows = len(target_df)
    sliced_df = target_df.iloc[offset : offset + limit]

    return {
        "dataset": name_clean,
        "total_rows": total_rows,
        "offset": offset,
        "limit": limit,
        "records": sliced_df.to_dict(orient="records"),
    }


@app.post("/api/run", tags=["Reconciliation"])
def trigger_run():
    report, ctx = get_current_report()
    return {
        "status": "success",
        "message": "Reconciliation pipeline executed successfully",
        "report": report,
        "graph": build_knowledge_graph_data(ctx, report),
    }
