from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .meta_autonomy_v3_benchmark import verify_meta_autonomy_report


class MetaAutonomyV3Room:
    """Append-only, hash-chained room for replayable capability reports."""

    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(self, report: Mapping[str, Any]) -> Mapping[str, Any]:
        verification = verify_meta_autonomy_report(report)
        if not verification["passed"]:
            raise ValueError("meta-autonomy benchmark cannot replay")
        digest = str(report["content_digest"])
        existing = next(
            (event for event in self._events if event["report"]["content_digest"] == digest),
            None,
        )
        if existing:
            return existing
        event: dict[str, Any] = {
            "schema_version": "meta-autonomy-v3-room-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "report": dict(report),
            "verification": verification,
            "previous_event_hash": self._events[-1]["event_hash"] if self._events else self.ZERO_HASH,
        }
        event["event_hash"] = _hash_event(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        self._events.append(event)
        return event

    def _load(self) -> None:
        previous = self.ZERO_HASH
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line:
                continue
            event = json.loads(line)
            valid_chain = (
                event.get("event_index") == len(self._events)
                and event.get("previous_event_hash") == previous
                and event.get("event_hash") == _hash_event(event)
            )
            verification = verify_meta_autonomy_report(event.get("report", {}))
            if not valid_chain or not verification["passed"] or event.get("verification") != verification:
                raise ValueError(f"meta-autonomy room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["event_hash"]


def _hash_event(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
