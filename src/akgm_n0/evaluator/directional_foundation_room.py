"""Replayable room for two-symbol directional foundation semantics."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.directional_tape import DirectionalFoundationSemantic

from .directional_foundation_proof import verify_directional_foundation_semantic


class DirectionalFoundationRoom:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(self, semantic: DirectionalFoundationSemantic, proof: Mapping[str, Any]) -> Mapping[str, Any]:
        recomputed = verify_directional_foundation_semantic(semantic)
        if not recomputed["passed"] or dict(proof) != recomputed:
            raise ValueError("directional foundation proof cannot be reproduced")
        existing = next((item for item in self._events if item["semantic"]["semantic_id"] == semantic.semantic_id), None)
        if existing is not None:
            return existing
        event: dict[str, Any] = {
            "schema_version": "directional-foundation-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "semantic": semantic.to_dict(),
            "proof": recomputed,
            "previous_event_hash": self._events[-1]["event_hash"] if self._events else self.ZERO_HASH,
        }
        event["event_hash"] = _event_hash(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._events.append(event)
        return event

    def _load(self) -> None:
        previous = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("event_index") != len(self._events):
                    raise ValueError(f"directional room index mismatch at line {line_number}")
                if event.get("previous_event_hash") != previous:
                    raise ValueError("directional room predecessor mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise ValueError("directional room hash mismatch")
                semantic = DirectionalFoundationSemantic.from_dict(dict(event["semantic"]))
                proof = verify_directional_foundation_semantic(semantic)
                if not proof["passed"] or event.get("proof") != proof:
                    raise ValueError("stored directional proof cannot be replayed")
                self._events.append(event)
                previous = event["event_hash"]


def _event_hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

