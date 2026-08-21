from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.meta_autonomy_v3 import EvolvedProgram
from .operator_catalog_v5 import (
    additional_operator_specs,
    catalog_behavior_signature,
    verify_additional_operator,
)
from .operator_frontier_v4 import behavior_signature, operator_worlds, verify_operator_program


class VerifiedOperatorCatalogRoom:
    """Append-only room that replays every operator before accepting it."""

    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        self._base_cases = {case.world.world_id: case for case in operator_worlds()}
        self._additional = {spec.world_id: spec for spec in additional_operator_specs()}
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def _replay_record(self, record: Mapping[str, Any]) -> bool:
        program = EvolvedProgram.from_dict(record["program"])
        world_id = str(record["world_id"])
        if world_id in self._base_cases:
            case = self._base_cases[world_id]
            proof = verify_operator_program(case, program)
            signature = behavior_signature(case, program)
        else:
            spec = self._additional[world_id]
            proof = verify_additional_operator(spec, program)
            signature = catalog_behavior_signature(spec, program)
        return bool(
            proof["passed"]
            and proof == record["symbolic_verification"]
            and signature == record["behavior_signature"]
            and record.get("promoted") is True
            and record.get("name_visible_to_learner") is False
        )

    def record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self._replay_record(record):
            raise ValueError("operator cannot enter verified catalog room")
        operator_id = str(record["operator_id"])
        existing = next((item for item in self._events if item["operator_id"] == operator_id), None)
        if existing:
            return existing
        event: dict[str, Any] = {
            "schema_version": "verified-operator-catalog-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "operator_id": operator_id,
            "world_id": str(record["world_id"]),
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
            try:
                semantic_valid = self._replay_record(event["record"])
            except (KeyError, TypeError, ValueError, OverflowError):
                semantic_valid = False
            if (
                event.get("event_index") != len(self._events)
                or event.get("previous_event_hash") != previous
                or event.get("event_hash") != _hash_event(event)
                or not semantic_valid
            ):
                raise ValueError(f"verified operator catalog room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["event_hash"]


def _hash_event(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
