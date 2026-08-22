"""Allowlisted network and literature broker for V46."""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request


USER_AGENT = "AKGM-N0-open-science/0.1 (public autonomous research prototype)"


SOURCES = {
    "NETSRC-4b60e57e": {
        "world_id": "WORLD-692abdb0cf477f47",
        "kind": "noaa_water_level",
        "url": "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" + urllib.parse.urlencode({
            "product": "water_level",
            "application": "AKGM_N0_V46",
            "begin_date": "20240201",
            "end_date": "20240207",
            "datum": "MLLW",
            "station": "1612340",
            "time_zone": "gmt",
            "units": "metric",
            "format": "json",
        }),
        "sealed_metadata": {
            "institution": "NOAA Center for Operational Oceanographic Products and Services",
            "domain": "coastal water level",
            "location": "Honolulu, Hawaii station 1612340",
            "documentation": "https://api.tidesandcurrents.noaa.gov/api/prod/",
        },
    },
    "NETSRC-96608f33": {
        "world_id": "WORLD-a83610976b378d8f",
        "kind": "usgs_earthquakes",
        "url": "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urllib.parse.urlencode({
            "format": "geojson",
            "starttime": "2025-01-01",
            "endtime": "2025-02-01",
            "minmagnitude": "4.5",
            "orderby": "time-asc",
            "eventtype": "earthquake",
        }),
        "sealed_metadata": {
            "institution": "United States Geological Survey",
            "domain": "global earthquake events",
            "location": "global catalog",
            "documentation": "https://earthquake.usgs.gov/fdsnws/event/1/",
        },
    },
    "NETSRC-a18728df": {
        "world_id": "WORLD-90f60bd59102a427",
        "kind": "nasa_power",
        "url": "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode({
            "parameters": "T2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,PS",
            "community": "AG",
            "longitude": "139.6917",
            "latitude": "35.6895",
            "start": "20240101",
            "end": "20240331",
            "format": "JSON",
            "time-standard": "UTC",
        }),
        "sealed_metadata": {
            "institution": "NASA Langley Research Center",
            "domain": "meteorology and surface solar energy",
            "location": "Tokyo grid point",
            "documentation": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/",
        },
    },
}


def _download(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    started = time.time_ns()
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
        status = response.status
        content_type = response.headers.get("Content-Type")
    ended = time.time_ns()
    if not payload:
        raise RuntimeError("allowlisted network source returned no bytes")
    return payload, {
        "url": url,
        "status": status,
        "content_type": content_type,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "started_at_unix_ns": started,
        "ended_at_unix_ns": ended,
    }


def _anonymous_records(kind, payload):
    data = json.loads(payload)
    if kind == "noaa_water_level":
        rows = []
        for index, item in enumerate(data.get("data", ())):
            try:
                rows.append({"q0": float(index), "q1": float(item["v"])})
            except (KeyError, TypeError, ValueError):
                continue
        return rows
    if kind == "usgs_earthquakes":
        rows = []
        for index, item in enumerate(data.get("features", ())):
            coordinates = item.get("geometry", {}).get("coordinates", ())
            properties = item.get("properties", {})
            if len(coordinates) >= 3 and properties.get("mag") is not None:
                rows.append({
                    "q0": float(index),
                    "q1": float(properties["mag"]),
                    "q2": float(coordinates[2]),
                })
        return rows
    if kind == "nasa_power":
        parameters = data["properties"]["parameter"]
        rows = []
        for index, date in enumerate(sorted(parameters["T2M"])):
            values = (
                float(parameters["ALLSKY_SFC_SW_DWN"][date]),
                float(parameters["PRECTOTCORR"][date]),
                float(parameters["PS"][date]),
                float(parameters["T2M"][date]),
            )
            if all(value > -900 for value in values):
                rows.append({"q0": float(index), "q1": values[0], "q2": values[1], "q3": values[2], "q4": values[3]})
        return rows
    raise ValueError("unsupported source parser")


def _literature(query):
    url = "https://api.crossref.org/v1/works?" + urllib.parse.urlencode({
        "query.bibliographic": query,
        "rows": "12",
        "select": "DOI,title,author,published,container-title,type,is-referenced-by-count",
    })
    raw, receipt = _download(url)
    payload = json.loads(raw)
    records = []
    for item in payload.get("message", {}).get("items", ()):
        title = item.get("title") or []
        records.append({
            "doi": item.get("DOI"),
            "title": title[0] if title else None,
            "type": item.get("type"),
            "container_title": (item.get("container-title") or [None])[0],
            "is_referenced_by_count": int(item.get("is-referenced-by-count", 0)),
        })
    return records, receipt


def main():
    commitment = None
    collected = False
    event_index = 0
    for line in sys.stdin:
        request = json.loads(line)
        operation = request.get("op")
        try:
            if operation == "catalog":
                response = {
                    "ok": True,
                    "sources": [
                        {
                            "source_id": source_id,
                            "related_world_id": item["world_id"],
                            "acquisition_cost": 1.0,
                            "provenance_verifiable": True,
                            "domain_name_exposed": False,
                        }
                        for source_id, item in sorted(SOURCES.items())
                    ],
                    "arbitrary_urls_allowed": False,
                }
            elif operation == "commit_source":
                source_id = str(request.get("source_id", ""))
                digest = str(request.get("commitment", ""))
                if commitment is not None or source_id not in SOURCES or len(digest) != 64:
                    response = {"ok": False, "error": "invalid_or_duplicate_source_commitment"}
                else:
                    commitment = {"source_id": source_id, "digest": digest}
                    response = {"ok": True, "event_index": event_index, **commitment}
                    event_index += 1
            elif operation == "collect":
                if commitment is None or request.get("commitment") != commitment["digest"]:
                    response = {"ok": False, "error": "source_commitment_required"}
                else:
                    source = SOURCES[commitment["source_id"]]
                    raw, receipt = _download(source["url"])
                    rows = _anonymous_records(source["kind"], raw)
                    collected = True
                    response = {
                        "ok": True,
                        "event_index": event_index,
                        "source_id": commitment["source_id"],
                        "records": rows,
                        "record_count": len(rows),
                        "receipt": receipt,
                        "domain_name_exposed": False,
                    }
                    event_index += 1
            elif operation == "reveal_metadata":
                if not collected or commitment is None:
                    response = {"ok": False, "error": "collection_required_before_metadata_reveal"}
                else:
                    response = {
                        "ok": True,
                        "event_index": event_index,
                        "metadata": SOURCES[commitment["source_id"]]["sealed_metadata"],
                    }
                    event_index += 1
            elif operation == "literature_search":
                query = " ".join(str(request.get("query", "")).split())[:300]
                if not query:
                    response = {"ok": False, "error": "nonempty_literature_query_required"}
                else:
                    records, receipt = _literature(query)
                    response = {
                        "ok": True,
                        "event_index": event_index,
                        "query": query,
                        "records": records,
                        "record_count": len(records),
                        "receipt": receipt,
                        "provider": "Crossref REST API",
                        "full_text_reviewed": False,
                    }
                    event_index += 1
            elif operation == "shutdown":
                print(json.dumps({"ok": True}), flush=True)
                return 0
            else:
                response = {"ok": False, "error": "unsupported_operation"}
        except Exception as error:
            response = {"ok": False, "error": type(error).__name__, "message": str(error)}
        print(json.dumps(response, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
