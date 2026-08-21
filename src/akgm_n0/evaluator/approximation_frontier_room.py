from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.approximation_frontier import ApproximationFoundationSemantic
from .approximation_frontier_proof import verify_approximation_foundation_semantic


class ApproximationFrontierRoom:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(self, semantic: ApproximationFoundationSemantic, proof: Mapping[str, Any]) -> Mapping[str, Any]:
        replay = verify_approximation_foundation_semantic(semantic)
        if not replay["passed"] or dict(proof) != replay:
            raise ValueError("approximation proof cannot replay")
        existing = next((event for event in self._events if event["semantic"]["semantic_id"] == semantic.semantic_id), None)
        if existing:
            return existing
        event = {
            "schema_version": "approximation-memory-event-v0.1",
            "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "semantic": semantic.to_dict(),
            "proof": replay,
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
            if event.get("event_index") != len(self._events) or event.get("previous_event_hash") != previous or event.get("event_hash") != _hash_event(event):
                raise ValueError(f"approximation room chain mismatch {line_number}")
            semantic = ApproximationFoundationSemantic.from_dict(event["semantic"])
            proof = verify_approximation_foundation_semantic(semantic)
            if not proof["passed"] or event.get("proof") != proof:
                raise ValueError("stored approximation proof cannot replay")
            self._events.append(event)
            previous = event["event_hash"]


def _hash_event(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps({key: value for key, value in event.items() if key != "event_hash"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
