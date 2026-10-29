def test_snapshot(client):
    response = client.get("/api/v1/snapshot")
    assert response.status_code == 200
    assert response.json()["schools_in_scope"] == 220


def test_list_neighborhoods(client):
    response = client.get("/api/v1/neighborhoods?min_schools=3&limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["neighborhood_name"] == "Mayfair"


def test_neighborhood_not_found(client):
    response = client.get("/api/v1/neighborhoods/missing")
    assert response.status_code == 404


def test_school_spatial_query(client):
    response = client.get(
        "/api/v1/schools/near-open-parks",
        params={
            "distance_miles": 1,
            "education_level_code": "elem",
            "limit": 5,
        },
    )
    assert response.status_code == 200
    assert response.json()["education_level_code"] == "ELEM"


def test_invalid_distance_is_rejected(client):
    response = client.get(
        "/api/v1/schools/near-open-parks",
        params={"distance_miles": 0},
    )
    assert response.status_code == 422


def test_park_not_found(client):
    response = client.get("/api/v1/parks/missing/nearby-schools")
    assert response.status_code == 404
