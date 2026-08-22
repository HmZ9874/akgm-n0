from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "data/official_worlds_v44/official_worlds_v44_snapshot.json"
USER_AGENT = "AKGM-N0-open-science-prototype/0.1 (public research snapshot)"


def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"empty official response: {url}")
    return payload


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _chunk(values, size, prefix):
    traces = []
    for offset in range(0, len(values) - size + 1, size):
        block = values[offset:offset + size]
        traces.append({
            "trace_id": f"{prefix}-{offset // size:03d}",
            "inputs": [row[0] for row in block],
            "outputs": [row[1] for row in block],
        })
    return traces


def _partition(traces):
    if len(traces) < 6:
        raise RuntimeError("official world does not contain enough trace blocks")
    training = traces[0::3]
    validation = traces[1::3]
    transfer = traces[2::3]
    return {"training": training, "validation": validation, "transfer": transfer}


def _partition_by_group(groups):
    if len(groups) != 6 or any(not group for group in groups):
        raise RuntimeError("official world requires six non-empty source groups")
    return {
        "training": [trace for group in groups[:3] for trace in group],
        "validation": list(groups[3]),
        "transfer": [trace for group in groups[4:] for trace in group],
    }


def _nasa_power_world():
    locations = (
        ("P0", 36.7378, -119.7871),
        ("P1", 34.0522, -118.2437),
        ("P2", 37.7749, -122.4194),
        ("P3", 47.6062, -122.3321),
        ("P4", 40.7128, -74.0060),
        ("P5", 25.7617, -80.1918),
    )
    trace_groups = []
    receipts = []
    for token, latitude, longitude in locations:
        query = urllib.parse.urlencode({
            "parameters": "T2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,PS",
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": "20240101",
            "end": "20241231",
            "format": "JSON",
            "time-standard": "UTC",
        })
        url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + query
        raw = _download(url)
        payload = json.loads(raw)
        parameters = payload["properties"]["parameter"]
        dates = sorted(parameters["T2M"])
        rows = []
        for index, date in enumerate(dates):
            numbers = (
                parameters["ALLSKY_SFC_SW_DWN"][date],
                parameters["PRECTOTCORR"][date],
                parameters["PS"][date],
                parameters["T2M"][date],
            )
            if all(math.isfinite(float(value)) and float(value) > -900 for value in numbers):
                rows.append(((float(numbers[0]), float(numbers[1]), float(numbers[2])), float(numbers[3])))
        trace_groups.append(_chunk(rows, 45, token))
        receipts.append({"url": url, "sha256": _digest(raw), "bytes": len(raw)})
        time.sleep(0.2)
    return {
        "world_id": "WORLD-" + hashlib.sha256(b"NASA-POWER-V44").hexdigest()[:16],
        "anonymous_descriptor": {"channel_count": 3, "temporal": True, "measurement_kind": "continuous"},
        "partitions": _partition_by_group(trace_groups),
        "sealed_metadata": {
            "institution": "NASA Langley Research Center",
            "source": "NASA POWER Daily API",
            "domain": "meteorology and surface solar energy",
            "input_channels": ["all-sky surface shortwave irradiance", "corrected precipitation", "surface pressure"],
            "output_channel": "temperature at two metres",
            "human_equivalent_task": "multivariate autoregressive weather response modelling",
            "documentation": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
            "query_window": "2024-01-01/2024-12-31 UTC",
        },
        "source_receipts": receipts,
    }


def _noaa_tide_world():
    stations = ("9414290", "9410230", "8443970", "8724580", "8518750", "9447130")
    trace_groups = []
    receipts = []
    for station_index, station in enumerate(stations):
        query = urllib.parse.urlencode({
            "product": "water_level",
            "application": "AKGM_N0_OPEN_RESEARCH",
            "begin_date": "20240101",
            "end_date": "20240131",
            "datum": "MLLW",
            "station": station,
            "time_zone": "gmt",
            "units": "metric",
            "format": "json",
        })
        url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + query
        raw = _download(url)
        payload = json.loads(raw)
        rows = []
        for index, item in enumerate(payload.get("data", ())):
            try:
                output = float(item["v"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append(((float(index),), output))
        trace_groups.append(_chunk(rows, 240, f"S{station_index}"))
        receipts.append({"url": url, "sha256": _digest(raw), "bytes": len(raw)})
        time.sleep(0.2)
    return {
        "world_id": "WORLD-" + hashlib.sha256(b"NOAA-COOPS-V44").hexdigest()[:16],
        "anonymous_descriptor": {"channel_count": 1, "temporal": True, "measurement_kind": "continuous"},
        "partitions": _partition_by_group(trace_groups),
        "sealed_metadata": {
            "institution": "NOAA Center for Operational Oceanographic Products and Services",
            "source": "NOAA CO-OPS Data API",
            "domain": "coastal water level",
            "input_channels": ["elapsed six-minute sample index"],
            "output_channel": "verified or preliminary water level relative to MLLW",
            "human_equivalent_task": "short-horizon autoregressive tide-level modelling",
            "documentation": "https://api.tidesandcurrents.noaa.gov/api/prod/",
            "query_window": "2024-01-01/2024-01-31 GMT",
        },
        "source_receipts": receipts,
    }


def _usgs_event_world():
    query = urllib.parse.urlencode({
        "format": "csv",
        "starttime": "2024-01-01",
        "endtime": "2025-01-01",
        "minmagnitude": "4.5",
        "orderby": "time-asc",
        "eventtype": "earthquake",
    })
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + query
    raw = _download(url)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    rows = []
    previous_time = None
    for index, item in enumerate(reader):
        timestamp = datetime.fromisoformat(item["time"].replace("Z", "+00:00")).timestamp()
        elapsed_hours = 0.0 if previous_time is None else (timestamp - previous_time) / 3600.0
        previous_time = timestamp
        values = (
            elapsed_hours,
            float(item["latitude"]),
            float(item["longitude"]),
            float(item["depth"]),
        )
        output = float(item["mag"])
        if all(math.isfinite(value) for value in values + (output,)):
            rows.append((values, output))
    traces = _chunk(rows, 64, "E")
    training_end = max(1, int(len(traces) * 0.6))
    validation_end = max(training_end + 1, int(len(traces) * 0.8))
    partitions = {
        "training": traces[:training_end],
        "validation": traces[training_end:validation_end],
        "transfer": traces[validation_end:],
    }
    return {
        "world_id": "WORLD-" + hashlib.sha256(b"USGS-EVENT-V44").hexdigest()[:16],
        "anonymous_descriptor": {"channel_count": 4, "temporal": True, "measurement_kind": "event_sequence"},
        "partitions": partitions,
        "sealed_metadata": {
            "institution": "United States Geological Survey",
            "source": "USGS Earthquake Catalog FDSN Event Web Service",
            "domain": "global earthquake event sequence",
            "input_channels": ["elapsed event time", "latitude", "longitude", "depth"],
            "output_channel": "catalog magnitude",
            "human_equivalent_task": "event-sequence magnitude modelling; intentionally difficult control world",
            "documentation": "https://earthquake.usgs.gov/fdsnws/event/1/",
            "query_window": "2024-01-01/2025-01-01 UTC; magnitude >= 4.5",
        },
        "source_receipts": [{"url": url, "sha256": _digest(raw), "bytes": len(raw)}],
    }


def main():
    worlds = [_nasa_power_world(), _noaa_tide_world(), _usgs_event_world()]
    payload = {
        "snapshot_version": "official-world-registry-v44.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "world_count": len(worlds),
        "selection_labels_exposed_to_learner": False,
        "worlds": worlds,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload["snapshot_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({
        "destination": str(DESTINATION),
        "world_count": len(worlds),
        "snapshot_sha256": payload["snapshot_sha256"],
        "trace_counts": {
            world["world_id"]: {
                name: len(items) for name, items in world["partitions"].items()
            } for world in worlds
        },
    }, indent=2))


if __name__ == "__main__":
    main()
