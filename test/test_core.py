from __future__ import annotations

from datetime import datetime, timezone

import pytest

from iss_tracker import (
    cartesian_velocity_to_speed,
    compute_average_speed,
    convert_iso_dis_8601,
    fetch_epoch_data,
    fetch_index_request,
    get_capping_data,
    get_comment,
    get_header,
    get_meta,
    get_state_vectors,
    get_workable_time,
    parse_iss_document,
    parse_oem_epoch,
)


def test_parse_iss_document_accepts_oem_xml() -> None:
    xml = """
    <ndm><oem><header><CREATION_DATE>2024-067</CREATION_DATE></header>
      <body><segment><metadata><OBJECT_NAME>ISS</OBJECT_NAME></metadata>
        <data><COMMENT>fixture</COMMENT><stateVector><EPOCH>2024-067T08:28:00.000Z</EPOCH></stateVector></data>
      </segment></body>
    </oem></ndm>
    """
    parsed = parse_iss_document(xml)
    assert get_state_vectors(parsed)[0]["EPOCH"] == "2024-067T08:28:00.000Z"


def test_parse_iss_document_rejects_wrong_shape() -> None:
    with pytest.raises(ValueError, match="Invalid ISS OEM document"):
        parse_iss_document("<not-oem />")


def test_document_accessors(document: dict, state_vectors: list[dict]) -> None:
    assert get_state_vectors(document) == state_vectors
    assert get_capping_data(document, "EPOCH") == [
        "2024-067T08:28:00.000Z",
        "2024-067T08:30:00.000Z",
    ]
    assert get_comment(document) == ["Deterministic test fixture"]
    assert get_header(document)["CREATION_DATE"] == "2024-067T08:00:00.000Z"
    assert get_meta(document)["OBJECT_NAME"] == "ISS"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1945-09-02T10:30:17.003Z", "1945-245T10:30:17.003Z"),
        ("2000-03-01T00:00:00+00:00", "2000-061T00:00:00.000Z"),
    ],
)
def test_convert_iso_dis_8601(source: str, expected: str) -> None:
    assert convert_iso_dis_8601(source) == expected


def test_get_workable_time_is_injectable() -> None:
    supplied = datetime(2024, 3, 7, 8, 29, tzinfo=timezone.utc)
    assert get_workable_time(supplied) == "2024-067T08:29:00.000Z"


def test_parse_oem_epoch_rejects_invalid_input() -> None:
    with pytest.raises(ValueError, match="Invalid OEM epoch"):
        parse_oem_epoch("March 7")


def test_fetch_epoch_data_uses_full_timestamp(state_vectors: list[dict]) -> None:
    nearest = fetch_epoch_data(state_vectors, "2024-067T08:29:41.000Z")
    assert nearest["EPOCH"] == "2024-067T08:30:00.000Z"


def test_fetch_epoch_data_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="empty"):
        fetch_epoch_data([], "2024-067T08:29:00.000Z")


def test_speed_calculations(state_vectors: list[dict]) -> None:
    assert cartesian_velocity_to_speed(1, 2, 2) == 3
    assert compute_average_speed(state_vectors) == pytest.approx((3 + 5 + 6) / 3)


def test_fetch_index_request_uses_offset_and_count(state_vectors: list[dict]) -> None:
    assert fetch_index_request(state_vectors, offset=1, limit=1) == [state_vectors[1]]
    assert fetch_index_request(state_vectors, offset=1) == state_vectors[1:]
    assert fetch_index_request(state_vectors, limit=0) == []


@pytest.mark.parametrize(("offset", "limit"), [("bad", 2), (-1, 2), (0, -1)])
def test_fetch_index_request_rejects_invalid_ranges(
    state_vectors: list[dict], offset: object, limit: object
) -> None:
    with pytest.raises(ValueError):
        fetch_index_request(state_vectors, offset=offset, limit=limit)
