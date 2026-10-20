from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_evaluate_warnings_returns_eight_checks(client: TestClient) -> None:
    payload = {
        "total_debt": 500,
        "equity": 1000,
        "receivable_days": 45,
        "inventory_days": 60,
        "payable_days": 50,
        "cumulative_ocf": 900,
        "cumulative_net_profit": 1000,
        "pledged_pct_of_promoter": 0.0,
        "promoter_holding_change_pp": 0.5,
        "rpt_value": 20,
        "revenue": 5000,
        "shares_start": 100,
        "shares_end": 101,
        "effective_tax_rate": 0.25,
        "payout_ratio": 0.3,
        "roce": 0.18,
    }
    body = client.post("/api/v1/warnings/evaluate", json=payload).json()
    assert len(body["results"]) == 8
    assert {r["status"] for r in body["results"]} == {"clear"}
