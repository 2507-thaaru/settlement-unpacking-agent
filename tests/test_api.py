import io
import pytest
from fastapi.testclient import TestClient
from api.main import app, DATA_DIR, DEFAULT_DATA_DIR


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Settlement Unpacking Agent API"
    assert "/api/upload" in data["endpoints"]
    assert "/api/data/reset" in data["endpoints"]


def test_summary_and_report(client):
    res_sum = client.get("/api/summary")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert sum_data["passes_implemented"] == 5
    assert sum_data["total_exceptions_found"] > 0

    res_rep = client.get("/api/report")
    assert res_rep.status_code == 200
    rep_data = res_rep.json()
    assert "passes" in rep_data
    assert "all_exceptions" in rep_data


def test_knowledge_graph_endpoints(client):
    res_graph = client.get("/api/graph")
    assert res_graph.status_code == 200
    graph = res_graph.json()
    assert "nodes" in graph
    assert "edges" in graph
    assert graph["total_nodes"] > 0

    # Ensure source data nodes are present with row counts
    source_nodes = [n for n in graph["nodes"] if n.get("category") == "source_data"]
    assert len(source_nodes) == 5

    res_dot = client.get("/api/graph/dot")
    assert res_dot.status_code == 200
    assert "digraph G" in res_dot.json()["dot"]

    res_pipe = client.get("/api/pipeline")
    assert res_pipe.status_code == 200
    assert "graph" in res_pipe.json()


def test_upload_and_reset(client, tmp_path):
    # 1. Reset first to ensure clean state
    res_reset = client.get("/api/data/reset")
    assert res_reset.status_code == 200
    assert res_reset.json()["status"] == "success"

    # 2. Test uploading a valid bank statement file with auto-detection
    csv_content = (
        "date,narration,utr,credit_amount\n"
        "2026-03-05,SETTLEMENT_TEST_12345678,UTR123456789,95000.00\n"
    )
    files = [
        ("files", ("custom_bank_statement.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv"))
    ]
    res_upload = client.post("/api/upload", files=files)
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data["status"] == "success"
    assert upload_data["uploaded_files"][0]["dataset_type"] == "bank_statement"
    assert upload_data["uploaded_files"][0]["rows"] == 1

    # 3. Verify knowledge graph reflects the new bank statement row count (1 row)
    res_graph = client.get("/api/graph")
    assert res_graph.status_code == 200
    bank_node = next(n for n in res_graph.json()["nodes"] if n["id"] == "bank")
    assert bank_node["rows"] == 1

    # 4. Reset back to demo data
    res_reset_post = client.post("/api/data/reset")
    assert res_reset_post.status_code == 200
    assert res_reset_post.json()["status"] == "success"

    # 5. Verify graph restored original demo row count (> 1 row)
    res_graph_restored = client.get("/api/graph")
    bank_node_restored = next(n for n in res_graph_restored.json()["nodes"] if n["id"] == "bank")
    assert bank_node_restored["rows"] > 1


def test_upload_excel_and_multiple_files(client):
    # Reset first
    client.post("/api/data/reset")

    import pandas as pd

    # Create an in-memory Excel file for reserve ledger
    reserve_df = pd.DataFrame([
        {
            "settlement_id": "SETTL_20260301_001",
            "settlement_date": "2026-03-01",
            "reserve_hold_amount": 5000.0,
            "reserve_released_amount": 0.0,
            "release_due_date": "2026-07-01",
        }
    ])
    excel_buf = io.BytesIO()
    reserve_df.to_excel(excel_buf, index=False)
    excel_buf.seek(0)

    # Create CSV for bank statement
    bank_csv = (
        "date,narration,utr,credit_amount\n"
        "2026-03-01,SETTLEMENT_TEST_001,UTR999999999,100000.00\n"
    )

    files = [
        ("files", ("reserve_data.xlsx", excel_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("files", ("bank_data.csv", io.BytesIO(bank_csv.encode("utf-8")), "text/csv")),
    ]

    res = client.post("/api/upload", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert len(data["uploaded_files"]) == 2
    types = {f["dataset_type"] for f in data["uploaded_files"]}
    assert "reserve_ledger" in types
    assert "bank_statement" in types

    # Verify graph reflects the new counts
    graph = client.get("/api/graph").json()
    reserve_node = next(n for n in graph["nodes"] if n["id"] == "reserve")
    assert reserve_node["rows"] == 1

    # Clean up by resetting
    client.post("/api/data/reset")


def test_upload_invalid_file(client):
    invalid_csv = "random_col1,random_col2\nfoo,bar\n"
    files = [
        ("files", ("random_file.csv", io.BytesIO(invalid_csv.encode("utf-8")), "text/csv"))
    ]
    res = client.post("/api/upload", files=files)
    assert res.status_code == 400
    assert "Could not automatically identify dataset type" in res.json()["detail"]
