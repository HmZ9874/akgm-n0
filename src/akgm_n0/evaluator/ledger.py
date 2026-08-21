"""Append-only, hash-chained knowledge state ledger."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, Protocol



class SerializableProgram(Protocol):
    def to_dict(self) -> Mapping[str, Any]: ...


KnowledgeStatus = Literal[
    "proposed", "fit_passed", "verified", "admitted", "bounded", "rejected"
]

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "proposed": frozenset({"fit_passed", "rejected"}),
    "fit_passed": frozenset({"verified", "rejected"}),
    "verified": frozenset({"admitted", "bounded", "rejected"}),
    "admitted": frozenset({"bounded", "rejected"}),
    "bounded": frozenset({"admitted", "rejected"}),
    "rejected": frozenset(),
}


class LedgerError(ValueError):
    """Raised for invalid transitions or a damaged event chain."""


@dataclass(frozen=True, slots=True)
class KnowledgeState:
    knowledge_id: str
    status: KnowledgeStatus
    program_ast: Mapping[str, Any]
    parent_ids: tuple[str, ...]
    provenance: Mapping[str, Any]
    latest_evidence: Mapping[str, Any]


class KnowledgeLedger:
    """Persist every status change without updating historical records."""

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
        self._states: dict[str, KnowledgeState] = {}
        if self.path.exists():
            self._load_and_verify()

    @property
    def events(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._events)

    def propose(
        self,
        program: SerializableProgram,
        *,
        parent_ids: tuple[str, ...],
        provenance: Mapping[str, Any],
        evidence: Mapping[str, Any] | None = None,
    ) -> str:
        knowledge_id = f"K-{len(self._states) + 1:06d}"
        event = self._new_event(
            knowledge_id=knowledge_id,
            from_status=None,
            to_status="proposed",
            reason="candidate_proposed",
            payload={
                "program_ast": program.to_dict(),
                "parent_ids": list(parent_ids),
                "provenance": dict(provenance),
                "evidence": dict(evidence or {}),
            },
        )
        self._append_event(event)
        return knowledge_id

    def transition(
        self,
        knowledge_id: str,
        to_status: KnowledgeStatus,
        *,
        reason: str,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        try:
            state = self._states[knowledge_id]
        except KeyError as exc:
            raise LedgerError(f"unknown knowledge id: {knowledge_id}") from exc
        if to_status not in ALLOWED_TRANSITIONS[state.status]:
            raise LedgerError(f"invalid transition: {state.status} -> {to_status}")
        event = self._new_event(
            knowledge_id=knowledge_id,
            from_status=state.status,
            to_status=to_status,
            reason=reason,
            payload={"evidence": dict(evidence or {})},
        )
        self._append_event(event)

    def get(self, knowledge_id: str) -> KnowledgeState:
        try:
            return self._states[knowledge_id]
        except KeyError as exc:
            raise LedgerError(f"unknown knowledge id: {knowledge_id}") from exc

    def _new_event(
        self,
        *,
        knowledge_id: str,
        from_status: KnowledgeStatus | None,
        to_status: KnowledgeStatus,
        reason: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        timestamp = self._clock()
        if timestamp.tzinfo is None:
            raise LedgerError("ledger clock must return a timezone-aware datetime")
        event: dict[str, Any] = {
            "schema_version": "knowledge-event-v0.1",
            "event_index": len(self._events),
            "timestamp": timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "knowledge_id": knowledge_id,
            "from_status": from_status,
            "to_status": to_status,
            "reason": reason,
            "payload": dict(payload),
            "previous_event_hash": (
                self._events[-1]["event_hash"] if self._events else self.ZERO_HASH
            ),
        }
        event["event_hash"] = _event_hash(event)
        return event

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
                    raise LedgerError(f"invalid JSON at ledger line {line_number}") from exc
                if event.get("event_index") != len(self._events):
                    raise LedgerError(f"event index mismatch at ledger line {line_number}")
                if event.get("previous_event_hash") != previous_hash:
                    raise LedgerError(f"hash chain mismatch at ledger line {line_number}")
                if event.get("event_hash") != _event_hash(event):
                    raise LedgerError(f"event hash mismatch at ledger line {line_number}")
                self._apply_event(event)
                self._events.append(event)
                previous_hash = event["event_hash"]

    def _apply_event(self, event: Mapping[str, Any]) -> None:
        knowledge_id = str(event["knowledge_id"])
        from_status = event["from_status"]
        to_status = str(event["to_status"])
        payload = event["payload"]
        if knowledge_id not in self._states:
            if from_status is not None or to_status != "proposed":
                raise LedgerError("first knowledge event must be a proposal")
            self._states[knowledge_id] = KnowledgeState(
                knowledge_id=knowledge_id,
                status="proposed",
                program_ast=payload["program_ast"],
                parent_ids=tuple(payload["parent_ids"]),
                provenance=payload["provenance"],
                latest_evidence=payload.get("evidence", {}),
            )
            return

        current = self._states[knowledge_id]
        if from_status != current.status or to_status not in ALLOWED_TRANSITIONS[current.status]:
            raise LedgerError(
                f"invalid stored transition for {knowledge_id}: {from_status} -> {to_status}"
            )
        self._states[knowledge_id] = KnowledgeState(
            knowledge_id=knowledge_id,
            status=to_status,
            program_ast=current.program_ast,
            parent_ids=current.parent_ids,
            provenance=current.provenance,
            latest_evidence=payload.get("evidence", {}),
        )


def _event_hash(event: Mapping[str, Any]) -> str:
    value = dict(event)
    value.pop("event_hash", None)
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
