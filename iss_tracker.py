"""Flask API for querying and transforming NASA ISS ephemeris data."""

from __future__ import annotations

import argparse
import logging
import math
import os
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from xml.parsers.expat import ExpatError

import requests
import xmltodict
from astropy import coordinates, units
from astropy.time import Time
from flask import Flask, jsonify, request
from geopy.exc import GeocoderServiceError
from geopy.geocoders import Nominatim

ISS_DATA_URL = (
    "https://nasa-public-data.s3.amazonaws.com/iss-coords/current/"
    "ISS_OEM/ISS.OEM_J2K_EPH.xml"
)
REQUEST_TIMEOUT_SECONDS = 15

Document = Mapping[str, Any]
StateVector = Mapping[str, Any]

app = Flask(__name__)


class UpstreamDataError(RuntimeError):
    """Raised when the NASA ephemeris cannot be retrieved or parsed."""


def parse_iss_document(xml_content: bytes | str) -> dict[str, Any]:
    """Parse and minimally validate an OEM XML document."""
    try:
        document = xmltodict.parse(xml_content)
        get_state_vectors(document)
    except (ExpatError, KeyError, TypeError) as exc:
        raise ValueError("Invalid ISS OEM document") from exc
    return document


def get_data() -> dict[str, Any]:
    """Download and parse the current NASA ISS OEM ephemeris."""
    try:
        response = requests.get(ISS_DATA_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return parse_iss_document(response.content)
    except requests.RequestException as exc:
        raise UpstreamDataError("NASA ephemeris request failed") from exc
    except ValueError as exc:
        raise UpstreamDataError("NASA ephemeris response was invalid") from exc


def get_state_vectors(document: Document) -> list[dict[str, Any]]:
    """Return the state-vector sequence from a parsed OEM document."""
    vectors = document["ndm"]["oem"]["body"]["segment"]["data"]["stateVector"]
    if isinstance(vectors, Mapping):
        return [dict(vectors)]
    if not isinstance(vectors, list) or not vectors:
        raise ValueError("OEM document contains no state vectors")
    return vectors


def get_capping_data(document: Document, key: str) -> list[Any]:
    """Return the first and last values for *key* in an OEM document."""
    vectors = get_state_vectors(document)
    return [vectors[0][key], vectors[-1][key]]


def _parse_standard_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized[-1:].lower() == "z":
        normalized = f"{normalized[:-1]}+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def convert_iso_dis_8601(standard_time: str) -> str:
    """Convert a calendar-date timestamp to NASA's year/day-of-year format."""
    parsed = _parse_standard_datetime(standard_time)
    return parsed.strftime("%Y-%jT%H:%M:%S.%f")[:-3] + "Z"


def get_workable_time(now: datetime | None = None) -> str:
    """Return the supplied time (or current UTC time) in OEM epoch format."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return convert_iso_dis_8601(current.astimezone(timezone.utc).isoformat())


def parse_oem_epoch(epoch: str) -> datetime:
    """Parse an OEM epoch such as ``2026-221T12:30:00.000Z``."""
    for timestamp_format in ("%Y-%jT%H:%M:%S.%fZ", "%Y-%jT%H:%M:%SZ"):
        try:
            return datetime.strptime(epoch, timestamp_format).replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
    raise ValueError(f"Invalid OEM epoch: {epoch!r}")


def fetch_epoch_data(data: Sequence[StateVector], epoch: str) -> dict[str, Any]:
    """Return the state vector nearest to the requested epoch."""
    if not data:
        raise ValueError("Cannot search an empty state-vector sequence")
    target = parse_oem_epoch(epoch)
    try:
        nearest = min(
            data,
            key=lambda vector: abs(parse_oem_epoch(str(vector["EPOCH"])) - target),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("State-vector data is missing a valid EPOCH") from exc
    return dict(nearest)


def cartesian_velocity_to_speed(x_dot: float, y_dot: float, z_dot: float) -> float:
    """Compute speed from Cartesian velocity components."""
    return math.hypot(float(x_dot), float(y_dot), float(z_dot))


def compute_average_speed(data: Sequence[StateVector]) -> float:
    """Compute mean speed across a non-empty state-vector sequence."""
    if not data:
        raise ValueError("Cannot average an empty state-vector sequence")
    speeds = [
        cartesian_velocity_to_speed(
            vector["X_DOT"]["#text"],
            vector["Y_DOT"]["#text"],
            vector["Z_DOT"]["#text"],
        )
        for vector in data
    ]
    return sum(speeds) / len(speeds)


def _nonnegative_int(value: str | int | None, name: str, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed < 0:
        raise ValueError(f"{name} must be nonnegative")
    return parsed


def fetch_index_request(
    data: Sequence[StateVector],
    offset: str | int | None = None,
    limit: str | int | None = None,
) -> list[StateVector]:
    """Return at most *limit* state vectors beginning at *offset*."""
    start = _nonnegative_int(offset, "offset", 0)
    count = _nonnegative_int(limit, "limit", len(data) - start)
    return list(data[start : start + count])


def get_comment(document: Document) -> list[str]:
    """Return comments embedded in an OEM document."""
    return document["ndm"]["oem"]["body"]["segment"]["data"]["COMMENT"]


def get_header(document: Document) -> dict[str, Any]:
    """Return the OEM document header."""
    return document["ndm"]["oem"]["header"]


def get_meta(document: Document) -> dict[str, Any]:
    """Return OEM segment metadata."""
    return document["ndm"]["oem"]["body"]["segment"]["metadata"]


def compute_location_astropy(vector: StateVector) -> tuple[float, float, float]:
    """Transform a GCRS state-vector position into geodetic coordinates.

    Returns latitude and longitude in degrees and altitude in kilometres.
    """
    obstime = Time(parse_oem_epoch(str(vector["EPOCH"])))
    position = coordinates.CartesianRepresentation(
        [
            float(vector["X"]["#text"]),
            float(vector["Y"]["#text"]),
            float(vector["Z"]["#text"]),
        ],
        unit=units.km,
    )
    gcrs = coordinates.GCRS(position, obstime=obstime)
    itrs = gcrs.transform_to(coordinates.ITRS(obstime=obstime))
    location = coordinates.EarthLocation.from_geocentric(*itrs.cartesian.xyz)
    return (
        float(location.lat.to_value(units.deg)),
        float(location.lon.to_value(units.deg)),
        float(location.height.to_value(units.km)),
    )


def reverse_geocode(latitude: float, longitude: float) -> dict[str, Any] | None:
    """Resolve coordinates to an address when the public geocoder is available."""
    try:
        result = Nominatim(user_agent="iss-tracker-portfolio").reverse(
            (latitude, longitude), zoom=15, language="en", timeout=5
        )
    except GeocoderServiceError:
        return None
    return result.raw.get("address") if result is not None else None


def _location_payload(vector: StateVector) -> dict[str, Any]:
    latitude, longitude, altitude = compute_location_astropy(vector)
    return {
        "epoch": vector["EPOCH"],
        "latitude": {"value": latitude, "units": "deg"},
        "longitude": {"value": longitude, "units": "deg"},
        "altitude": {"value": altitude, "units": "km"},
        "geolocation": reverse_geocode(latitude, longitude),
    }


@app.errorhandler(ValueError)
def handle_bad_request(error: ValueError):
    return jsonify(error=str(error)), 400


@app.errorhandler(UpstreamDataError)
def handle_upstream_error(error: UpstreamDataError):
    return jsonify(error=str(error)), 502


@app.get("/")
def service_index():
    return jsonify(
        service="ISS Orbital Data Tracker API",
        endpoints=[
            "/health",
            "/header",
            "/metadata",
            "/comment",
            "/epochs",
            "/epochs/<epoch>",
            "/epochs/<epoch>/speed",
            "/epochs/<epoch>/location",
            "/now",
        ],
    )


@app.get("/health")
def health_request():
    return jsonify(status="ok")


@app.get("/metadata")
def meta_request():
    return jsonify(get_meta(get_data()))


@app.get("/header")
def header_request():
    return jsonify(get_header(get_data()))


@app.get("/comment")
def comment_request():
    return jsonify(get_comment(get_data()))


@app.get("/epochs")
def index_request():
    vectors = get_state_vectors(get_data())
    result = fetch_index_request(
        vectors,
        offset=request.args.get("offset"),
        limit=request.args.get("limit"),
    )
    return jsonify(result)


@app.get("/epochs/<epoch>")
def epoch_request(epoch: str):
    vector = fetch_epoch_data(get_state_vectors(get_data()), epoch)
    return jsonify(vector)


@app.get("/epochs/<epoch>/speed")
def speed_request(epoch: str):
    vector = fetch_epoch_data(get_state_vectors(get_data()), epoch)
    speed = cartesian_velocity_to_speed(
        vector["X_DOT"]["#text"],
        vector["Y_DOT"]["#text"],
        vector["Z_DOT"]["#text"],
    )
    return jsonify(epoch=vector["EPOCH"], speed={"value": speed, "units": "km/s"})


@app.get("/epochs/<epoch>/location")
def location_request(epoch: str):
    vector = fetch_epoch_data(get_state_vectors(get_data()), epoch)
    return jsonify(_location_payload(vector))


@app.get("/now")
def now_request():
    vector = fetch_epoch_data(get_state_vectors(get_data()), get_workable_time())
    result = deepcopy(vector)
    result["speed"] = {
        "value": cartesian_velocity_to_speed(
            vector["X_DOT"]["#text"],
            vector["Y_DOT"]["#text"],
            vector["Z_DOT"]["#text"],
        ),
        "units": "km/s",
    }
    result["location"] = _location_payload(vector)
    return jsonify(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=5000, type=int)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app.run(
        host=args.host,
        port=args.port,
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )


if __name__ == "__main__":
    main()
