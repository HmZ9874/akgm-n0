"""Hash-chained room for generation-two operator proofs."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from akgm_n0.learner.operator_evolution import EvolvedMicroOperator

from .evolved_operator_proof import verify_evolved_operator


class EvolvedSemanticRoomError(ValueError):
    pass


class VerifiedEvolvedSemanticRoom:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path, *, clock: Callable[[], datetime] | None = None):
        self.path = path.resolve()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(
        self, operator: EvolvedMicroOperator, verification: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        recomputed = verify_evolved_operator(operator)
        if not recomputed["passed"] or dict(verification) != recomputed:
            raise EvolvedSemanticRoomError("evolved semantic proof cannot be reproduced")
        existing = next(
            (event for event in self._events if event["operator"]["operator_id"] == operator.operator_id),
            None,
        )
        if existing is not None:
            return existing
        now = self._clock()
        event: dict[str, Any] = {
            "schema_version": "verified-evolved-semantic-event-v0.1",
            "event_index": len(self._events),
            "timestamp": now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "operator": operator.to_dict(),
            "verification": recomputed,
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

    def _load_and_verify(self) -> None:
        previous_hash = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    operator = EvolvedMicroOperator.from_dict(event["operator"])
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise EvolvedSemanticRoomError(
                        f"invalid evolved semantic room line {line_number}"
                    ) from exc
                if event.get("event_index") != len(self._events):
                    raise EvolvedSemanticRoomError("event index mismatch")
                if event.get("previous_event_hash") != previous_hash:
                    raise EvolvedSemanticRoomError("hash chain predecessor mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise EvolvedSemanticRoomError("event hash mismatch")
                recomputed = verify_evolved_operator(operator)
                if not recomputed["passed"] or event.get("verification") != recomputed:
                    raise EvolvedSemanticRoomError("stored proof cannot be reproduced")
                self._events.append(event)
                previous_hash = event["event_hash"]


def _event_hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

