"""Persistent memory for disproved unordered-relation program semantics."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from akgm_n0.learner.relations import RelationNode


class RelationMistakeLibraryError(ValueError):
    """Raised when the relation-mistake event chain is invalid."""


@dataclass(frozen=True, slots=True)
class RelationMistakeRecord:
    mistake_id: str
    objective_id: str
    failed_scope: str
    condition_key: str
    semantic_signature: str
    representative_program: Mapping[str, Any]
    counterexamples: tuple[Mapping[str, Any], ...]
    source_candidate_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mistake_id": self.mistake_id,
            "objective_id": self.objective_id,
            "failed_scope": self.failed_scope,
            "condition_key": self.condition_key,
            "semantic_signature": self.semantic_signature,
            "representative_program": dict(self.representative_program),
            "counterexamples": [dict(item) for item in self.counterexamples],
            "source_candidate_id": self.source_candidate_id,
        }


def relation_semantic_signature(program: RelationNode) -> str:
    """Canonicalize the current relation language as affine behavior a*x+b."""

    def reduce(node: RelationNode) -> tuple[float, float]:
        if node.op == "r_value":
            return (1.0, 0.0)
        if node.op == "r_constant" and node.constant is not None:
            return (0.0, float(node.constant))
        if node.op not in {"r_add", "r_subtract"} or len(node.args) != 2:
            raise RelationMistakeLibraryError(
                f"cannot canonicalize relation operation: {node.op}"
            )
        left = reduce(node.args[0])
        right = reduce(node.args[1])
        direction = 1.0 if node.op == "r_add" else -1.0
        return (left[0] + direction * right[0], left[1] + direction * right[1])

    coefficient, constant = reduce(program)
    return json.dumps(
        {"coefficient": coefficient, "constant": constant},
        sort_keys=True,
        separators=(",", ":"),
    )


class RelationMistakeLibrary:
    """Append-only, condition-scoped rejection memory for relation programs."""

    ZERO_HASH = "0" * 64

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path.resolve()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[dict[str, Any]] = []
        self._records: list[RelationMistakeRecord] = []
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[RelationMistakeRecord, ...]:
        return tuple(self._records)

    def find_equivalent(
        self,
        program: RelationNode,
        *,
        objective_id: str,
        failed_scope: str,
        condition_key: str,
    ) -> tuple[RelationMistakeRecord, ...]:
        signature = relation_semantic_signature(program)
        return tuple(
            record
            for record in self._records
            if record.objective_id == objective_id
            and record.failed_scope == failed_scope
            and record.condition_key == condition_key
            and record.semantic_signature == signature
        )

    def candidate_gate(
        self,
        *,
        objective_id: str,
        failed_scope: str,
        condition_key: str,
    ) -> Callable[[RelationNode], bool]:
        return lambda program: not self.find_equivalent(
            program,
            objective_id=objective_id,
            failed_scope=failed_scope,
            condition_key=condition_key,
        )

    def record(
        self,
        program: RelationNode,
        *,
        objective_id: str,
        failed_scope: str,
        condition_key: str,
        counterexamples: Sequence[Mapping[str, Any]],
        source_candidate_id: str,
    ) -> RelationMistakeRecord:
        if not objective_id or not failed_scope or not condition_key:
            raise ValueError("relation mistake conditions cannot be empty")
        if not counterexamples:
            raise ValueError("a rejected relation requires counterexamples")
        existing = self.find_equivalent(
            program,
            objective_id=objective_id,
            failed_scope=failed_scope,
            condition_key=condition_key,
        )
        if existing:
            return existing[0]
        signature = relation_semantic_signature(program)
        mistake_id = "RM-" + hashlib.sha256(
            f"{objective_id}|{failed_scope}|{condition_key}|{signature}".encode("utf-8")
        ).hexdigest()[:16]
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise RelationMistakeLibraryError("mistake clock must be timezone-aware")
        event: dict[str, Any] = {
            "schema_version": "relation-mistake-event-v0.1",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "mistake_id": mistake_id,
            "objective_id": objective_id,
            "failed_scope": failed_scope,
            "condition_key": condition_key,
            "semantic_signature": signature,
            "representative_program": program.to_dict(),
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
                    raise RelationMistakeLibraryError(
                        f"invalid JSON at relation mistake line {line_number}"
                    ) from exc
                if event.get("event_index") != len(self._events):
                    raise RelationMistakeLibraryError("event index mismatch")
                if event.get("previous_event_hash") != previous_hash:
                    raise RelationMistakeLibraryError("hash chain mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise RelationMistakeLibraryError("event hash mismatch")
                self._events.append(event)
                self._records.append(_record_from_event(event))
                previous_hash = event["event_hash"]


def _record_from_event(event: Mapping[str, Any]) -> RelationMistakeRecord:
    return RelationMistakeRecord(
        mistake_id=str(event["mistake_id"]),
        objective_id=str(event["objective_id"]),
        failed_scope=str(event["failed_scope"]),
        condition_key=str(event["condition_key"]),
        semantic_signature=str(event["semantic_signature"]),
        representative_program=event["representative_program"],
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
