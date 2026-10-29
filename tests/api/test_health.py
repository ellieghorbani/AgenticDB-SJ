def test_live_health(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_health(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "agenticdb_sj"
