"""Hash-chained replay rooms for nested and repeated-group foundations."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Generic, Mapping, TypeVar

from akgm_n0.learner.nested_cycle import NestedFoundationSemantic, PartitionFoundationSemantic

from .nested_foundation_proof import verify_nested_foundation_semantic, verify_partition_foundation_semantic


SemanticT = TypeVar("SemanticT", NestedFoundationSemantic, PartitionFoundationSemantic)


class _ReplayRoom(Generic[SemanticT]):
    ZERO_HASH = "0" * 64
    schema_version = ""

    def __init__(
        self,
        path: Path,
        semantic_type: type[SemanticT],
        verifier: Callable[[SemanticT], dict[str, Any]],
    ) -> None:
        self.path = path.resolve()
        self._semantic_type = semantic_type
        self._verifier = verifier
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            self._load()

    @property
    def records(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def record(self, semantic: SemanticT, proof: Mapping[str, Any]) -> Mapping[str, Any]:
        recomputed = self._verifier(semantic)
        if not recomputed["passed"] or dict(proof) != recomputed:
            raise ValueError("foundation proof cannot be reproduced")
        existing = next((item for item in self._events if item["semantic"]["semantic_id"] == semantic.semantic_id), None)
        if existing is not None:
            return existing
        event: dict[str, Any] = {
            "schema_version": self.schema_version,
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
                    raise ValueError(f"room index mismatch at line {line_number}")
                if event.get("previous_event_hash") != previous:
                    raise ValueError("room predecessor mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise ValueError("room hash mismatch")
                semantic = self._semantic_type.from_dict(dict(event["semantic"]))
                proof = self._verifier(semantic)
                if not proof["passed"] or event.get("proof") != proof:
                    raise ValueError("stored proof cannot be replayed")
                self._events.append(event)
                previous = event["event_hash"]


class NestedFoundationRoom(_ReplayRoom[NestedFoundationSemantic]):
    schema_version = "nested-foundation-event-v0.1"

    def __init__(self, path: Path) -> None:
        super().__init__(path, NestedFoundationSemantic, verify_nested_foundation_semantic)


class PartitionFoundationRoom(_ReplayRoom[PartitionFoundationSemantic]):
    schema_version = "partition-foundation-event-v0.1"

    def __init__(self, path: Path) -> None:
        super().__init__(path, PartitionFoundationSemantic, verify_partition_foundation_semantic)


def _event_hash(event: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_hash"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
