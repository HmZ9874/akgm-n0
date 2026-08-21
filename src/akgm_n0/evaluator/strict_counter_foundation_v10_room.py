"""Hash-chained success room for strict counter foundations."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from akgm_n0.learner.strict_counter_foundation_v10 import CounterProgram

from .strict_counter_foundation_v10 import CounterFoundationProof, prove_counter_foundation


class StrictCounterFoundationRoom:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._events)

    def record(
        self,
        program: CounterProgram,
        proof: CounterFoundationProof,
        *,
        run_id: str,
    ) -> dict[str, Any]:
        replay = prove_counter_foundation(program)
        if not proof.passed or replay.to_dict() != proof.to_dict():
            raise ValueError("counter foundation proof cannot be independently replayed")
        for event in self._events:
            if event["semantic_id"] == proof.semantic_id:
                return event
        event: dict[str, Any] = {
            "schema_version": "strict-counter-foundation-room-v10.1",
            "record_index": len(self._events),
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "run_id": run_id,
            "semantic_id": proof.semantic_id,
            "classification": "target_free_bounded_structural_discovery",
            "program": program.to_dict(),
            "proof": proof.to_dict(),
            "previous_hash": self._events[-1]["record_hash"] if self._events else "0" * 64,
        }
        event["record_hash"] = _hash(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._events.append(event)
        return event

    def _load_and_verify(self) -> None:
        previous = "0" * 64
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event["record_index"] != len(self._events) or event["previous_hash"] != previous:
                raise ValueError(f"strict counter room chain failed at line {line_number}")
            if event["record_hash"] != _hash(event):
                raise ValueError(f"strict counter room hash failed at line {line_number}")
            program = CounterProgram.from_dict(event["program"])
            if prove_counter_foundation(program).to_dict() != event["proof"]:
                raise ValueError(f"strict counter room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["record_hash"]


def _hash(event: dict[str, Any]) -> str:
    payload = dict(event)
    payload.pop("record_hash", None)
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
