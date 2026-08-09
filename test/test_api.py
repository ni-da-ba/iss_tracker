from __future__ import annotations

import pytest

import iss_tracker


def test_index_and_health_do_not_require_upstream_data(client) -> None:
    index = client.get("/")
    health = client.get("/health")
    assert index.status_code == 200
    assert index.get_json()["service"] == "ISS Orbital Data Tracker API"
    assert health.get_json() == {"status": "ok"}


def test_document_routes(client) -> None:
    assert client.get("/header").get_json()["CREATION_DATE"].startswith("2024-")
    assert client.get("/metadata").get_json() == {"OBJECT_NAME": "ISS"}
    assert client.get("/comment").get_json() == ["Deterministic test fixture"]


def test_epochs_route_applies_offset_and_limit(client) -> None:
    response = client.get("/epochs?offset=1&limit=1")
    assert response.status_code == 200
    assert [item["EPOCH"] for item in response.get_json()] == ["2024-067T08:29:00.000Z"]


def test_epochs_route_reports_bad_query(client) -> None:
    response = client.get("/epochs?offset=not-a-number")
    assert response.status_code == 400
    assert response.get_json() == {"error": "offset must be an integer"}


def test_epoch_and_speed_routes(client) -> None:
    epoch = "2024-067T08:29:31.000Z"
    state_response = client.get(f"/epochs/{epoch}")
    speed_response = client.get(f"/epochs/{epoch}/speed")
    assert state_response.get_json()["EPOCH"] == "2024-067T08:30:00.000Z"
    assert speed_response.get_json() == {
        "epoch": "2024-067T08:30:00.000Z",
        "speed": {"units": "km/s", "value": 6.0},
    }


def test_location_route_isolated_from_external_services(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        iss_tracker, "compute_location_astropy", lambda vector: (30.0, -97.0, 420.0)
    )
    monkeypatch.setattr(
        iss_tracker,
        "reverse_geocode",
        lambda latitude, longitude: {"state": "Texas", "country": "United States"},
    )
    response = client.get("/epochs/2024-067T08:29:00.000Z/location")
    assert response.status_code == 200
    assert response.get_json()["altitude"] == {"units": "km", "value": 420.0}
    assert response.get_json()["geolocation"]["state"] == "Texas"


def test_now_combines_vector_speed_and_location(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        iss_tracker, "get_workable_time", lambda: "2024-067T08:29:00.000Z"
    )
    monkeypatch.setattr(
        iss_tracker,
        "_location_payload",
        lambda vector: {"epoch": vector["EPOCH"], "geolocation": None},
    )
    response = client.get("/now")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["EPOCH"] == "2024-067T08:29:00.000Z"
    assert payload["speed"] == {"units": "km/s", "value": 5.0}
    assert payload["location"]["geolocation"] is None


def test_upstream_failure_returns_502(client, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail():
        raise iss_tracker.UpstreamDataError("NASA ephemeris request failed")

    monkeypatch.setattr(iss_tracker, "get_data", fail)
    response = client.get("/metadata")
    assert response.status_code == 502
    assert response.get_json() == {"error": "NASA ephemeris request failed"}
