from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.high_school_reasoning import HighSchoolProgram
from .high_school_benchmark_v6 import high_school_specs, verify_high_school_program


class HighSchoolCapabilityRoom:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        self._specs = {item.competency_id: item for item in high_school_specs()}
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def _valid(self, record: Mapping[str, Any]) -> bool:
        spec = self._specs[str(record["competency_id"])]
        program = HighSchoolProgram.from_dict(record["program"])
        proof = verify_high_school_program(spec, program)
        return bool(
            proof["passed"] and proof == record["verification"]
            and record.get("passed") is True and record.get("name_visible_to_learner") is False
        )

    def record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self._valid(record):
            raise ValueError("competency cannot enter high-school capability room")
        competency_id = str(record["competency_id"])
        existing = next((item for item in self._events if item["competency_id"] == competency_id), None)
        if existing:
            return existing
        event: dict[str, Any] = {
            "schema_version": "high-school-capability-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "competency_id": competency_id,
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
                raise ValueError(f"high-school room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["event_hash"]


def _hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
