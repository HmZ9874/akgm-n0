"""Persistent, condition-scoped memory of disproved program families."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from akgm_n0.learner.dsl import ProgramNode


class MistakeLibraryError(ValueError):
    """Raised when the stored mistake chain is invalid."""


@dataclass(frozen=True, slots=True)
class MistakeRecord:
    mistake_id: str
    objective_id: str
    failed_scope: str
    condition_key: str
    family_signature: str
    representative_program_ast: Mapping[str, Any]
    counterexamples: tuple[Mapping[str, Any], ...]
    source_candidate_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mistake_id": self.mistake_id,
            "objective_id": self.objective_id,
            "failed_scope": self.failed_scope,
            "condition_key": self.condition_key,
            "family_signature": self.family_signature,
            "representative_program_ast": dict(self.representative_program_ast),
            "counterexamples": [dict(item) for item in self.counterexamples],
            "source_candidate_id": self.source_candidate_id,
        }


class MistakeLibrary:
    """Append-only mistake records with equivalence-aware replay checks."""

    ZERO_HASH = "0" * 64

    def __init__(
        self,
        path: Path,
        *,
        concept_library: Mapping[str, ProgramNode] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path.resolve()
        self.concept_library = dict(concept_library or {})
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[dict[str, Any]] = []
        self._records: list[MistakeRecord] = []
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[MistakeRecord, ...]:
        return tuple(self._records)

    def record(
        self,
        program: ProgramNode,
        *,
        objective_id: str,
        failed_scope: str,
        condition_key: str,
        counterexamples: Sequence[Mapping[str, Any]],
        source_candidate_id: str,
    ) -> MistakeRecord:
        if not objective_id or not failed_scope or not condition_key:
            raise ValueError("mistake conditions cannot be empty")
        if not counterexamples:
            raise ValueError("a disproved program requires at least one counterexample")
        signature = program_family_signature(program, self.concept_library)
        existing = self.find_equivalent(
            program,
            objective_id=objective_id,
            failed_scope=failed_scope,
            condition_key=condition_key,
        )
        if existing:
            return existing[0]
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise MistakeLibraryError("mistake clock must be timezone-aware")
        mistake_id = "M-" + hashlib.sha256(
            f"{objective_id}|{failed_scope}|{condition_key}|{signature}".encode("utf-8")
        ).hexdigest()[:16]
        event: dict[str, Any] = {
            "schema_version": "mistake-event-v0.1",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "mistake_id": mistake_id,
            "objective_id": objective_id,
            "failed_scope": failed_scope,
            "condition_key": condition_key,
            "family_signature": signature,
            "representative_program_ast": program.to_dict(),
            "counterexamples": [dict(item) for item in counterexamples],
            "source_candidate_id": source_candidate_id,
            "previous_event_hash": (
                self._events[-1]["event_hash"] if self._events else self.ZERO_HASH
            ),
        }
        event["event_hash"] = _event_hash(event)
        self._append_event(event)
        return self._records[-1]

    def find_equivalent(
        self,
        program: ProgramNode,
        *,
        objective_id: str,
        failed_scope: str,
        condition_key: str,
    ) -> tuple[MistakeRecord, ...]:
        signature = program_family_signature(program, self.concept_library)
        return tuple(
            record
            for record in self._records
            if record.objective_id == objective_id
            and record.failed_scope == failed_scope
            and record.condition_key == condition_key
            and record.family_signature == signature
        )

    def candidate_gate(
        self,
        *,
        objective_id: str,
        failed_scope: str,
        condition_key: str,
    ) -> Callable[[ProgramNode], bool]:
        """Return True only for candidates not disproved under these conditions."""

        return lambda program: not self.find_equivalent(
            program,
            objective_id=objective_id,
            failed_scope=failed_scope,
            condition_key=condition_key,
        )

    def _append_event(self, event: dict[str, Any]) -> None:
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

    def _load_and_verify(self) -> None:
        previous_hash = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise MistakeLibraryError(
                        f"invalid JSON at mistake line {line_number}"
                    ) from exc
                if event.get("event_index") != len(self._events):
                    raise MistakeLibraryError("mistake event index mismatch")
                if event.get("previous_event_hash") != previous_hash:
                    raise MistakeLibraryError("mistake hash chain mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise MistakeLibraryError("mistake event hash mismatch")
                self._events.append(event)
                self._records.append(_record_from_event(event))
                previous_hash = event["event_hash"]


def program_family_signature(
    program: ProgramNode, concept_library: Mapping[str, ProgramNode] | None = None
) -> str:
    """Canonicalize the linear program family, ignoring free-parameter sign."""

    definitions = dict(concept_library or {})
    visiting: set[str] = set()

    def reduce(node: ProgramNode) -> dict[str, int]:
        if node.op in definitions:
            if node.op in visiting:
                raise MistakeLibraryError("concept library cycle in signature")
            visiting.add(node.op)
            result = reduce(definitions[node.op])
            visiting.remove(node.op)
            return result
        if node.op == "p_read_offset":
            if node.offset is None:
                raise MistakeLibraryError("read node has no offset")
            return {f"read:{node.offset}": 1}
        if node.op == "p_scalar_parameter":
            if node.parameter_slot is None:
                raise MistakeLibraryError("parameter node has no slot")
            return {f"parameter:{node.parameter_slot}": 1}
        if node.op not in {"p_add", "p_subtract"} or len(node.args) != 2:
            raise MistakeLibraryError(f"cannot canonicalize operation: {node.op}")
        left = reduce(node.args[0])
        right = reduce(node.args[1])
        result = dict(left)
        direction = 1 if node.op == "p_add" else -1
        for key, value in right.items():
            result[key] = result.get(key, 0) + direction * value
            if result[key] == 0:
                del result[key]
        return result

    coefficients = reduce(program)
    normalized = {
        key: (1 if key.startswith("parameter:") else value)
        for key, value in coefficients.items()
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def _record_from_event(event: Mapping[str, Any]) -> MistakeRecord:
    return MistakeRecord(
        mistake_id=str(event["mistake_id"]),
        objective_id=str(event["objective_id"]),
        failed_scope=str(event["failed_scope"]),
        condition_key=str(event["condition_key"]),
        family_signature=str(event["family_signature"]),
        representative_program_ast=event["representative_program_ast"],
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
