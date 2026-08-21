from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from akgm_n0.learner.root_frontier import RootFoundationSemantic
from .root_frontier_proof import verify_root_foundation_semantic


class RootFrontierRoom:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(self, semantic: RootFoundationSemantic, proof: Mapping[str, Any]) -> Mapping[str, Any]:
        replay = verify_root_foundation_semantic(semantic)
        if not replay["passed"] or dict(proof) != replay:
            raise ValueError("root proof cannot replay")
        existing = next(
            (item for item in self._events if item["semantic"]["semantic_id"] == semantic.semantic_id),
            None,
        )
        if existing:
            return existing
        event = {
            "schema_version": "exact-root-event-v0.1",
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
            if (
                event.get("event_index") != len(self._events)
                or event.get("previous_event_hash") != previous
                or event.get("event_hash") != _hash_event(event)
            ):
                raise ValueError(f"root room chain mismatch {line_number}")
            semantic = RootFoundationSemantic.from_dict(event["semantic"])
            proof = verify_root_foundation_semantic(semantic)
            if not proof["passed"] or event.get("proof") != proof:
                raise ValueError("stored root proof cannot replay")
            self._events.append(event)
            previous = event["event_hash"]


def _hash_event(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
