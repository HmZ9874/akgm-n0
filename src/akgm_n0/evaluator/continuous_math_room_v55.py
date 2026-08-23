"""Hash-chained success ledger for V55 exact counter semantics."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from akgm_n0.learner.cold_start_semantics_v16 import OperatorDefinitionV16
from akgm_n0.learner.continuous_math_research_v55 import (
    exact_semantic_for_operator_v55,
    exact_semantic_text_v55,
    operator_from_dict_v55,
)
from .continuous_math_research_v55 import verify_exact_semantic_v55


def _event_hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


class ContinuousMathSuccessRoomV55:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def sync(
        self, definitions: Sequence[OperatorDefinitionV16]
    ) -> tuple[Mapping[str, Any], ...]:
        existing = {
            item["exact_semantic"]["exact_signature"] for item in self._events
        }
        added = []
        for definition in definitions:
            semantic = exact_semantic_for_operator_v55(definition)
            if semantic.exact_signature in existing:
                continue
            proof = verify_exact_semantic_v55(definition, semantic)
            if not proof["passed"]:
                raise ValueError("V55 exact proof cannot be reproduced for success room")
            event: dict[str, Any] = {
                "schema_version": "continuous-math-success-event-v55.0",
                "event_index": len(self._events),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "operator": definition.to_dict(),
                "exact_semantic": semantic.to_dict(),
                "posthoc_formula": exact_semantic_text_v55(semantic),
                "proof": proof,
                "previous_event_hash": self._events[-1]["event_hash"]
                if self._events
                else self.ZERO_HASH,
            }
            event["event_hash"] = _event_hash(event)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self._events.append(event)
            existing.add(semantic.exact_signature)
            added.append(event)
        return tuple(added)

    def _load(self) -> None:
        previous = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("event_index") != len(self._events):
                    raise ValueError(f"V55 success room index mismatch at line {line_number}")
                if event.get("previous_event_hash") != previous:
                    raise ValueError("V55 success room previous hash mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise ValueError("V55 success room event hash mismatch")
                definition = operator_from_dict_v55(event["operator"])
                semantic = exact_semantic_for_operator_v55(definition)
                proof = verify_exact_semantic_v55(definition, semantic)
                if (
                    not proof["passed"]
                    or event.get("exact_semantic") != semantic.to_dict()
                    or event.get("proof") != proof
                ):
                    raise ValueError("V55 success room proof replay failed")
                self._events.append(event)
                previous = event["event_hash"]
