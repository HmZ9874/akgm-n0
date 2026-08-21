from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.autonomous_operator_research_v7 import DiscoveredOperator
from .autonomous_operator_research_v7 import posthoc_formula, verify_researched_operator


class AutonomousOperatorV7Room:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    @staticmethod
    def _valid(record: Mapping[str, Any]) -> bool:
        item = DiscoveredOperator.from_dict(record)
        proof = verify_researched_operator(item)
        return bool(
            proof["passed"] and proof == record["verification"]
            and record.get("promoted") is True
            and record.get("posthoc_formula") == posthoc_formula(item)
        )

    def record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self._valid(record):
            raise ValueError("operator cannot enter autonomous V7 room")
        operator_id = str(record["operator_id"])
        existing = next((item for item in self._events if item["operator_id"] == operator_id), None)
        if existing:
            return existing
        event: dict[str, Any] = {
            "schema_version": "autonomous-operator-v7-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "operator_id": operator_id,
            "record": dict(record),
            "previous_event_hash": self._events[-1]["event_hash"] if self._events else self.ZERO_HASH,
        }
        event["event_hash"] = _hash(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._events.append(event)
        return event

    def _load(self) -> None:
        previous = self.ZERO_HASH
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line:
                continue
            event = json.loads(line)
            try:
                valid = self._valid(event["record"])
            except (KeyError, TypeError, ValueError):
                valid = False
            if (
                event.get("event_index") != len(self._events)
                or event.get("previous_event_hash") != previous
                or event.get("event_hash") != _hash(event)
                or not valid
            ):
                raise ValueError(f"autonomous V7 room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["event_hash"]


def _hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
