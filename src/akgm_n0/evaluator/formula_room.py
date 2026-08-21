"""Append-only room for executable formulas that passed registered checks."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol


class SerializableFormula(Protocol):
    def to_dict(self) -> Mapping[str, Any]: ...


class FormulaRoomError(ValueError):
    """Raised when a success record is invalid or the room chain is damaged."""


@dataclass(frozen=True, slots=True)
class SuccessfulFormulaRecord:
    room_record_id: str
    operation_id: str
    definition: Mapping[str, Any]
    parent_operation_ids: tuple[str, ...]
    validation_scope: str
    knowledge_status: str
    evidence: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "room_record_id": self.room_record_id,
            "operation_id": self.operation_id,
            "definition": dict(self.definition),
            "parent_operation_ids": list(self.parent_operation_ids),
            "validation_scope": self.validation_scope,
            "knowledge_status": self.knowledge_status,
            "evidence": dict(self.evidence),
        }


class FormulaSuccessRoom:
    """Persist condition-scoped successful executable formulas without overwrites."""

    ZERO_HASH = "0" * 64
    ACCEPTED_KNOWLEDGE_STATUSES = frozenset({"verified", "admitted", "bounded"})

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path.resolve()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._events: list[dict[str, Any]] = []
        self._records: list[SuccessfulFormulaRecord] = []
        self._disqualifications: dict[str, Mapping[str, Any]] = {}
        if self.path.exists():
            self._load_and_verify()

    @property
    def records(self) -> tuple[SuccessfulFormulaRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.room_record_id not in self._disqualifications
        )

    @property
    def historical_records(self) -> tuple[SuccessfulFormulaRecord, ...]:
        return tuple(self._records)

    @property
    def disqualifications(self) -> Mapping[str, Mapping[str, Any]]:
        return dict(self._disqualifications)

    def record(
        self,
        formula: SerializableFormula,
        *,
        operation_id: str,
        parent_operation_ids: tuple[str, ...],
        validation_scope: str,
        knowledge_status: str,
        evidence: Mapping[str, Any],
    ) -> SuccessfulFormulaRecord:
        if not operation_id or not validation_scope:
            raise ValueError("operation_id and validation_scope cannot be empty")
        if knowledge_status not in self.ACCEPTED_KNOWLEDGE_STATUSES:
            raise FormulaRoomError(
                "formula must be independently verified before entering the room"
            )
        if not evidence:
            raise FormulaRoomError("a successful formula requires validation evidence")
        existing = next(
            (
                record
                for record in self._records
                if record.operation_id == operation_id
                and record.validation_scope == validation_scope
            ),
            None,
        )
        if existing is not None:
            return existing
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise FormulaRoomError("formula room clock must be timezone-aware")
        room_record_id = "SF-" + hashlib.sha256(
            f"{operation_id}|{validation_scope}".encode("utf-8")
        ).hexdigest()[:16]
        event: dict[str, Any] = {
            "schema_version": "successful-formula-event-v0.1",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "room_record_id": room_record_id,
            "operation_id": operation_id,
            "definition": dict(formula.to_dict()),
            "parent_operation_ids": list(parent_operation_ids),
            "validation_scope": validation_scope,
            "knowledge_status": knowledge_status,
            "evidence": dict(evidence),
            "previous_event_hash": (
                self._events[-1]["event_hash"] if self._events else self.ZERO_HASH
            ),
        }
        event["event_hash"] = _event_hash(event)
        self._append(event)
        return self._records[-1]

    def disqualify(
        self,
        room_record_id: str,
        *,
        reason: str,
        evidence: Mapping[str, Any],
    ) -> None:
        if not any(
            record.room_record_id == room_record_id for record in self._records
        ):
            raise FormulaRoomError(f"unknown formula room record: {room_record_id}")
        if room_record_id in self._disqualifications:
            return
        if not reason or not evidence:
            raise FormulaRoomError("disqualification requires reason and evidence")
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise FormulaRoomError("formula room clock must be timezone-aware")
        event: dict[str, Any] = {
            "schema_version": "successful-formula-event-v0.1",
            "event_kind": "disqualified",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "room_record_id": room_record_id,
            "reason": reason,
            "evidence": dict(evidence),
            "previous_event_hash": (
                self._events[-1]["event_hash"] if self._events else self.ZERO_HASH
            ),
        }
        event["event_hash"] = _event_hash(event)
        self._append(event)

    def _append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(
            event, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._events.append(event)
        self._apply_event(event)

    def _load_and_verify(self) -> None:
        previous_hash = self.ZERO_HASH
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise FormulaRoomError(
                        f"invalid JSON at formula room line {line_number}"
                    ) from exc
                if event.get("event_index") != len(self._events):
                    raise FormulaRoomError("formula room event index mismatch")
                if event.get("previous_event_hash") != previous_hash:
                    raise FormulaRoomError("formula room hash chain mismatch")
                if event.get("event_hash") != _event_hash(event):
                    raise FormulaRoomError("formula room event hash mismatch")
                self._events.append(event)
                self._apply_event(event)
                previous_hash = event["event_hash"]

    def _apply_event(self, event: Mapping[str, Any]) -> None:
        event_kind = event.get("event_kind", "admitted")
        if event_kind == "admitted":
            self._records.append(_record_from_event(event))
            return
        if event_kind == "disqualified":
            room_record_id = str(event["room_record_id"])
            if not any(
                record.room_record_id == room_record_id for record in self._records
            ):
                raise FormulaRoomError("disqualification precedes formula admission")
            self._disqualifications[room_record_id] = {
                "reason": event["reason"],
                "evidence": event["evidence"],
                "timestamp": event["timestamp"],
            }
            return
        raise FormulaRoomError(f"unknown formula room event kind: {event_kind}")


def _record_from_event(event: Mapping[str, Any]) -> SuccessfulFormulaRecord:
    return SuccessfulFormulaRecord(
        room_record_id=str(event["room_record_id"]),
        operation_id=str(event["operation_id"]),
        definition=event["definition"],
        parent_operation_ids=tuple(event["parent_operation_ids"]),
        validation_scope=str(event["validation_scope"]),
        knowledge_status=str(event["knowledge_status"]),
        evidence=event["evidence"],
    )


def _event_hash(event: Mapping[str, Any]) -> str:
    value = dict(event)
    value.pop("event_hash", None)
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
