"""Append-only rejection memory for ordered indexed compositions."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from akgm_n0.learner.indexed_semantics import IndexedNode, indexed_node_key


class IndexedMistakeLibraryError(ValueError):
    """Raised when the indexed-mistake hash chain is invalid."""


@dataclass(frozen=True, slots=True)
class IndexedMistakeRecord:
    mistake_id: str
    failed_scope: str
    condition_key: str
    program_signature: str
    counterexamples: tuple[Mapping[str, Any], ...]
    source_candidate_id: str


class IndexedMistakeLibrary:
    ZERO_HASH = "0" * 64

    def __init__(self, path: Path, *, clock: Callable[[], datetime] | None = None):
        self.path = path.resolve()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[dict[str, Any]] = []
        self._records: list[IndexedMistakeRecord] = []
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[IndexedMistakeRecord, ...]:
        return tuple(self._records)

    def find_equivalent(
        self, program: IndexedNode, *, failed_scope: str, condition_key: str
    ) -> tuple[IndexedMistakeRecord, ...]:
        signature = indexed_node_key(program)
        return tuple(
            record
            for record in self._records
            if record.failed_scope == failed_scope
            and record.condition_key == condition_key
            and record.program_signature == signature
        )

    def candidate_gate(
        self, *, failed_scope: str, condition_key: str
    ) -> Callable[[IndexedNode], bool]:
        return lambda program: not self.find_equivalent(
            program, failed_scope=failed_scope, condition_key=condition_key
        )

    def record(
        self,
        program: IndexedNode,
        *,
        failed_scope: str,
        condition_key: str,
        counterexamples: Sequence[Mapping[str, Any]],
        source_candidate_id: str,
    ) -> IndexedMistakeRecord:
        if not failed_scope or not condition_key or not counterexamples:
            raise ValueError("indexed mistake requires scope, condition, and evidence")
        existing = self.find_equivalent(
            program, failed_scope=failed_scope, condition_key=condition_key
        )
        if existing:
            return existing[0]
        signature = indexed_node_key(program)
        mistake_id = "IM-" + hashlib.sha256(
            f"{failed_scope}|{condition_key}|{signature}".encode("utf-8")
        ).hexdigest()[:16]
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise IndexedMistakeLibraryError("mistake clock must be timezone-aware")
        event: dict[str, Any] = {
            "schema_version": "indexed-mistake-event-v0.1",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "mistake_id": mistake_id,
            "failed_scope": failed_scope,
            "condition_key": condition_key,
            "program_signature": signature,
            "program": program.to_dict(),
            "counterexamples": [dict(item) for item in counterexamples],
            "source_candidate_id": source_candidate_id,
            "previous_event_hash": (
                self._events[-1]["event_hash"] if self._events else self.ZERO_HASH
            ),
        }
        event["event_hash"] = _event_hash(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(
            event, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._events.append(event)
        self._records.append(_record_from_event(event))
        return self._records[-1]

    def _load_and_verify(self) -> None:
        previous_hash = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise IndexedMistakeLibraryError(
                        f"invalid JSON at line {line_number}"
                    ) from exc
                if event.get("event_index") != len(self._events):
                    raise IndexedMistakeLibraryError("event index mismatch")
                if event.get("previous_event_hash") != previous_hash:
                    raise IndexedMistakeLibraryError("hash chain mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise IndexedMistakeLibraryError("event hash mismatch")
                self._events.append(event)
                self._records.append(_record_from_event(event))
                previous_hash = event["event_hash"]


def _record_from_event(event: Mapping[str, Any]) -> IndexedMistakeRecord:
    return IndexedMistakeRecord(
        mistake_id=str(event["mistake_id"]),
        failed_scope=str(event["failed_scope"]),
        condition_key=str(event["condition_key"]),
        program_signature=str(event["program_signature"]),
        counterexamples=tuple(event["counterexamples"]),
        source_candidate_id=str(event["source_candidate_id"]),
    )


def _event_hash(event: Mapping[str, Any]) -> str:
    value = dict(event)
    value.pop("event_hash", None)
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
