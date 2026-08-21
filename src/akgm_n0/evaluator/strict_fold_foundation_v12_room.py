"""Hash-chained success room for strict fold foundations."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from akgm_n0.learner.strict_fold_foundation_v12 import FoldProgram

from .strict_fold_foundation_v12 import FoldFoundationProof, prove_fold_foundation


class StrictFoldFoundationRoom:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._events)

    def record(self, program: FoldProgram, proof: FoldFoundationProof, *, run_id: str) -> dict[str, Any]:
        if not proof.passed or prove_fold_foundation(program).to_dict() != proof.to_dict():
            raise ValueError("fold proof cannot be replayed")
        for event in self._events:
            if event["semantic_id"] == proof.semantic_id:
                return event
        event: dict[str, Any] = {
            "schema_version": "strict-fold-room-v12.1",
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

    def _load(self) -> None:
        previous = "0" * 64
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event["record_index"] != len(self._events) or event["previous_hash"] != previous or event["record_hash"] != _hash(event):
                raise ValueError(f"fold room chain failed at line {line_number}")
            program = FoldProgram.from_dict(event["program"])
            if prove_fold_foundation(program).to_dict() != event["proof"]:
                raise ValueError(f"fold room replay failed at line {line_number}")
            self._events.append(event)
            previous = event["record_hash"]


def _hash(event: dict[str, Any]) -> str:
    value = dict(event)
    value.pop("record_hash", None)
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
