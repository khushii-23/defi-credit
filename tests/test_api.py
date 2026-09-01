from fastapi.testclient import TestClient

from app.alchemy_client import NewWalletError, OracleDataError
from app.main import app, oracle
from app.scoring import WalletMetrics


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_invalid_address_returns_400(monkeypatch):
    response = client.get("/score/not-an-address")
    assert response.status_code == 400
    assert "Invalid Ethereum address" in response.json()["detail"]


def test_new_wallet_returns_minimum_score(monkeypatch):
    def _raise(_address: str):
        raise NewWalletError("0x0000000000000000000000000000000000000001")

    monkeypatch.setattr(oracle, "fetch_metrics", _raise)
    address = "0x0000000000000000000000000000000000000001"
    response = client.get(f"/score/{address}")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 300
    assert body["new_wallet"] is True
    assert body["metrics"]["transaction_count"] == 0
    assert "no on-chain history" in body["message"]


def test_scored_wallet_json_shape(monkeypatch):
    metrics = WalletMetrics(
        account_age_days=400,
        transaction_count=80,
        defi_interaction_count=12,
        protocols_used=("aave", "uniswap"),
    )
    monkeypatch.setattr(oracle, "fetch_metrics", lambda _addr: metrics)
    response = client.post(
        "/score",
        json={"address": "0x0000000000000000000000000000000000000001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert 300 < body["score"] <= 850
    assert body["new_wallet"] is False
    assert body["metrics"]["protocols_used"] == ["aave", "uniswap"]
    assert set(body["normalized"]) == {
        "account_age",
        "transaction_count",
        "defi_interactions",
    }


def test_alchemy_failure_returns_502(monkeypatch):
    def _raise(_address: str):
        raise OracleDataError("upstream timeout")

    monkeypatch.setattr(oracle, "fetch_metrics", _raise)
    response = client.get("/score/0x0000000000000000000000000000000000000001")
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream timeout"
