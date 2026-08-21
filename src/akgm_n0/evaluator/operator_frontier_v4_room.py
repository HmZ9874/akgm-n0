from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.meta_autonomy_v3 import EvolvedProgram
from .operator_frontier_v4 import behavior_signature, operator_worlds, verify_operator_program


class VerifiedOperatorRoom:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        self._cases = {case.world.world_id: case for case in operator_worlds()}
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        case = self._cases[str(record["world_id"])]
        program = EvolvedProgram.from_dict(record["program"])
        verification = verify_operator_program(case, program)
        signature = behavior_signature(case, program)
        if (
            not verification["passed"]
            or record.get("symbolic_verification") != verification
            or record.get("behavior_signature") != signature
            or record.get("promoted") is not True
        ):
            raise ValueError("operator cannot enter verified room")
        operator_id = str(record["operator_id"])
        existing = next((item for item in self._events if item["operator_id"] == operator_id), None)
        if existing:
            return existing
        event: dict[str, Any] = {
            "schema_version": "verified-operator-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "operator_id": operator_id,
            "world_id": case.world.world_id,
            "record": dict(record),
            "previous_event_hash": self._events[-1]["event_hash"] if self._events else self.ZERO_HASH,
        }
        event["event_hash"] = _hash_event(event)
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
            record = event.get("record", {})
            try:
                case = self._cases[event["world_id"]]
                program = EvolvedProgram.from_dict(record["program"])
                semantic_valid = (
                    verify_operator_program(case, program) == record["symbolic_verification"]
                    and record["symbolic_verification"]["passed"]
                    and behavior_signature(case, program) == record["behavior_signature"]
                )
            except (KeyError, TypeError, ValueError):
                semantic_valid = False
            if (
                event.get("event_index") != len(self._events)
                or event.get("previous_event_hash") != previous
                or event.get("event_hash") != _hash_event(event)
                or not semantic_valid
            ):
                raise ValueError(f"verified operator room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["event_hash"]


def _hash_event(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
