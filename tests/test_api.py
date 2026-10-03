from fastapi.testclient import TestClient
from app.alchemy_client import OracleDataError
from app.main import app, oracle
from app.models import WalletFeatures

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_invalid_address_returns_400():
    response = client.get("/score/not-an-address")
    assert response.status_code == 400
    assert "Invalid Ethereum address" in response.json()["detail"]

def test_new_wallet_returns_minimum_score(monkeypatch):
    monkeypatch.setattr(oracle, "fetch_asset_transfers", lambda _address: [])
    address = "0x0000000000000000000000000000000000000001"
    response = client.get(f"/score/{address}")
    
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 300
    assert body["new_wallet"] is True
    assert body["features"]["unique_transaction_count"] == 0
    assert body["explanations"][0]["factor"] == "No History"

def test_scored_wallet_json_shape(monkeypatch):
    transfers = [
        {"hash": "0xabc", "asset": "ETH", "value": 1.5, "metadata": {"blockTimestamp": "2026-01-01T10:00:00Z"}},
    ]
    monkeypatch.setattr(oracle, "fetch_asset_transfers", lambda _address: transfers)
    monkeypatch.setattr(oracle, "fetch_transaction_receipt", lambda _hash: None)
    
    response = client.post(
        "/score",
        json={"address": "0x0000000000000000000000000000000000000001"},
    )
    assert response.status_code == 200
    body = response.json()
    assert 300 < body["score"] <= 850
    assert body["new_wallet"] is False
    assert "features" in body
    assert "explanations" in body
    assert len(body["explanations"]) > 0

def test_alchemy_failure_returns_502(monkeypatch):
    def _raise(_address: str):
        raise OracleDataError("upstream timeout")

    monkeypatch.setattr(oracle, "fetch_asset_transfers", _raise)
    response = client.get("/score/0x0000000000000000000000000000000000000001")
    assert response.status_code == 502
    assert response.json()["detail"] == "upstream timeout"

def test_features_endpoint(monkeypatch):
    transfers = [
        {"hash": "0xabc", "asset": "ETH", "value": 1.5, "metadata": {"blockTimestamp": "2026-01-01T10:00:00Z"}},
    ]
    monkeypatch.setattr(oracle, "fetch_asset_transfers", lambda _address: transfers)
    address = "0x0000000000000000000000000000000000000001"
    
    response = client.get(f"/wallet/{address}/features")
    assert response.status_code == 200
    body = response.json()
    assert body["unique_transaction_count"] == 1
    assert body["asset_transfer_event_count"] == 1

def test_features_endpoint_invalid_address():
    response = client.get("/wallet/not-a-real-address/features")
    assert response.status_code == 400