"""Replay room for derived finite-mass semantics."""

from __future__ import annotations

import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from akgm_n0.learner.finite_mass_frontier import FiniteMassSemantic
from .finite_mass_proof import verify_finite_mass_semantic


class FiniteMassRoom:
    ZERO_HASH = "0" * 64
    def __init__(self, path: Path) -> None:
        self.path = path.resolve(); self._events: list[dict[str, Any]] = []
        if self.path.exists(): self._load()
    @property
    def records(self) -> tuple[Mapping[str, Any], ...]: return tuple(self._events)
    def record(self, semantic: FiniteMassSemantic, proof: Mapping[str, Any]) -> Mapping[str, Any]:
        recomputed = verify_finite_mass_semantic(semantic)
        if not recomputed["passed"] or dict(proof) != recomputed: raise ValueError("finite mass proof cannot be reproduced")
        existing = next((x for x in self._events if x["semantic"]["semantic_id"] == semantic.semantic_id), None)
        if existing is not None: return existing
        event: dict[str, Any] = {"schema_version": "finite-mass-event-v0.1", "event_index": len(self._events),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "semantic": semantic.to_dict(),
            "proof": recomputed, "previous_event_hash": self._events[-1]["event_hash"] if self._events else self.ZERO_HASH}
        event["event_hash"] = _hash(event); self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"); stream.flush(); os.fsync(stream.fileno())
        self._events.append(event); return event
    def _load(self) -> None:
        previous = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip(): continue
                event = json.loads(line)
                if event.get("event_index") != len(self._events) or event.get("previous_event_hash") != previous or event.get("event_hash") != _hash(event):
                    raise ValueError(f"finite mass room chain mismatch at line {line_number}")
                semantic = FiniteMassSemantic.from_dict(event["semantic"]); proof = verify_finite_mass_semantic(semantic)
                if not proof["passed"] or event.get("proof") != proof: raise ValueError("stored finite mass proof cannot be replayed")
                self._events.append(event); previous = event["event_hash"]


def _hash(event: Mapping[str, Any]) -> str:
    payload = {k: v for k, v in event.items() if k != "event_hash"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
