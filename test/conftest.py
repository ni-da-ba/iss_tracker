from __future__ import annotations

import pytest

import iss_tracker


@pytest.fixture
def state_vectors() -> list[dict]:
    return [
        {
            "EPOCH": "2024-067T08:28:00.000Z",
            "X": {"#text": "6800", "@units": "km"},
            "Y": {"#text": "0", "@units": "km"},
            "Z": {"#text": "0", "@units": "km"},
            "X_DOT": {"#text": "1", "@units": "km/s"},
            "Y_DOT": {"#text": "2", "@units": "km/s"},
            "Z_DOT": {"#text": "2", "@units": "km/s"},
        },
        {
            "EPOCH": "2024-067T08:29:00.000Z",
            "X": {"#text": "0", "@units": "km"},
            "Y": {"#text": "6800", "@units": "km"},
            "Z": {"#text": "0", "@units": "km"},
            "X_DOT": {"#text": "0", "@units": "km/s"},
            "Y_DOT": {"#text": "3", "@units": "km/s"},
            "Z_DOT": {"#text": "4", "@units": "km/s"},
        },
        {
            "EPOCH": "2024-067T08:30:00.000Z",
            "X": {"#text": "0", "@units": "km"},
            "Y": {"#text": "0", "@units": "km"},
            "Z": {"#text": "6800", "@units": "km"},
            "X_DOT": {"#text": "6", "@units": "km/s"},
            "Y_DOT": {"#text": "0", "@units": "km/s"},
            "Z_DOT": {"#text": "0", "@units": "km/s"},
        },
    ]


@pytest.fixture
def document(state_vectors: list[dict]) -> dict:
    return {
        "ndm": {
            "oem": {
                "header": {"CREATION_DATE": "2024-067T08:00:00.000Z"},
                "body": {
                    "segment": {
                        "metadata": {"OBJECT_NAME": "ISS"},
                        "data": {
                            "COMMENT": ["Deterministic test fixture"],
                            "stateVector": state_vectors,
                        },
                    }
                },
            }
        }
    }


@pytest.fixture
def client(document: dict, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(iss_tracker, "get_data", lambda: document)
    iss_tracker.app.config.update(TESTING=True)
    return iss_tracker.app.test_client()
