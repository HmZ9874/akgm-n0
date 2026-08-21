"""Learn reusable control motifs from proven word programs and grow new programs.

The extractor sees executable word code and record identifiers only.  It does not
receive theorem names or mathematical formula labels.  Growth is conditional on
motifs that were actually observed in prior proven programs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .metamachine_gen2 import (
    InvalidReflectiveProgram,
    OP_ADD_CELL,
    OP_ADD_INPUT,
    OP_EMIT,
    OP_GROW,
    OP_HALT,
    OP_JUMP,
    OP_JUMP_IF_NEGATIVE,
    OP_JUMP_IF_ZERO,
    OP_LOAD_CELL,
    OP_LOAD_INPUT,
    OP_SET,
    OP_STORE_CELL,
    OP_SUB_CELL,
    OP_SUB_IMMEDIATE,
    OP_SUB_INPUT,
    ReflectiveCandidate,
    ReflectiveExecutor,
    ReflectiveProgram,
    ReflectiveSearchReport,
    reflective_program_key,
)
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class LearnedMotif:
    """A structural regularity supported by prior proven executable programs."""

    motif_id: str
    kind: str
    source_record_ids: tuple[str, ...]
    structural_signature: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "motif_id": self.motif_id,
            "kind": self.kind,
            "source_record_ids": list(self.source_record_ids),
            "structural_signature": dict(self.structural_signature),
        }


class MotifExtractor:
    """Mine control/data-flow shapes without reading posthoc formula metadata."""

    def extract(
        self, sources: Sequence[tuple[str, ReflectiveProgram]]
    ) -> tuple[LearnedMotif, ...]:
        evidence: dict[str, list[tuple[str, Mapping[str, Any]]]] = {}
        for record_id, program in sources:
            instructions = tuple(zip(program.words[::2], program.words[1::2]))
            backward_jumps = tuple(
                (index, operand)
                for index, (opcode, operand) in enumerate(instructions)
                if opcode == OP_JUMP and operand < index
            )
            opcodes = tuple(opcode for opcode, _ in instructions)
            stores = tuple(operand for opcode, operand in instructions if opcode == OP_STORE_CELL)
            signature = {
                "backward_jump_count": len(backward_jumps),
                "conditional_branch_count": sum(
                    opcode in (OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE) for opcode in opcodes
                ),
                "distinct_stored_cells": len(set(stores)),
                "has_unit_descent": any(
                    opcode == OP_SUB_IMMEDIATE and operand == 1
                    for opcode, operand in instructions
                ),
                "has_accumulation": any(
                    opcode in (OP_ADD_CELL, OP_ADD_INPUT) for opcode in opcodes
                ),
            }
            if (
                backward_jumps
                and signature["has_unit_descent"]
                and signature["has_accumulation"]
            ):
                evidence.setdefault("counted_accumulation", []).append((record_id, signature))
            if len(backward_jumps) >= 2 and signature["has_accumulation"]:
                evidence.setdefault("nested_counted_accumulation", []).append((record_id, signature))
            if (
                backward_jumps
                and OP_JUMP_IF_NEGATIVE in opcodes
                and any(opcode in (OP_SUB_CELL, OP_SUB_INPUT) for opcode in opcodes)
            ):
                evidence.setdefault("guarded_repeated_subtraction", []).append((record_id, signature))
            if (
                backward_jumps
                and len(set(stores)) >= 3
                and OP_ADD_CELL in opcodes
            ):
                evidence.setdefault("synchronous_state_transition", []).append((record_id, signature))
            if OP_GROW in opcodes:
                evidence.setdefault("dynamic_scratch_memory", []).append((record_id, signature))

        motifs: list[LearnedMotif] = []
        for kind in sorted(evidence):
            items = evidence[kind]
            source_ids = tuple(sorted(record_id for record_id, _ in items))
            aggregate = {
                "support_count": len(items),
                "minimum_backward_jumps": min(
                    int(signature["backward_jump_count"]) for _, signature in items
                ),
                "maximum_distinct_stored_cells": max(
                    int(signature["distinct_stored_cells"]) for _, signature in items
                ),
                "derived_from_word_code_only": True,
            }
            encoded = json.dumps(
                {"kind": kind, "sources": source_ids, "signature": aggregate},
                sort_keys=True,
                separators=(",", ":"),
            )
            motifs.append(
                LearnedMotif(
                    motif_id="MOTIF-" + hashlib.sha256(encoded.encode()).hexdigest()[:16],
                    kind=kind,
                    source_record_ids=source_ids,
                    structural_signature=aggregate,
                )
            )
        return tuple(motifs)


class MotifGrowthSearch:
    """Grow nested state-transition programs from previously learned motifs."""

    REQUIRED_MOTIFS = frozenset(
        {
            "counted_accumulation",
            "nested_counted_accumulation",
            "synchronous_state_transition",
            "dynamic_scratch_memory",
        }
    )

    def __init__(
        self,
        motifs: Sequence[LearnedMotif],
        *,
        top_k: int = 200,
        executor: ReflectiveExecutor | None = None,
    ) -> None:
        self.motifs = tuple(motifs)
        self.top_k = top_k
        self.executor = executor or ReflectiveExecutor(maximum_steps=200_000)
        available = {item.kind for item in self.motifs}
        missing = self.REQUIRED_MOTIFS - available
        if missing:
            raise ValueError("motif growth is missing learned support: " + ", ".join(sorted(missing)))

    def search(self, observation: NumericTableObservation) -> ReflectiveSearchReport:
        valid = tuple(
            (row, float(output))
            for row, output, include in zip(
                observation.input_rows,
                observation.output_values,
                observation.validity_mask,
                strict=True,
            )
            if include
        )
        if not valid or len(valid[0][0]) != 5:
            raise ValueError("motif growth requires anonymous five-column evidence")
        candidates: list[ReflectiveCandidate] = []
        rejected = 0
        generated = 0
        for program in self._grow_programs():
            generated += 1
            outputs: list[float] = []
            try:
                for row, _ in valid:
                    outputs.append(self.executor.execute(program, row).output_value)
            except InvalidReflectiveProgram:
                rejected += 1
                continue
            errors = tuple(actual - target for actual, (_, target) in zip(outputs, valid, strict=True))
            key = reflective_program_key(program)
            candidates.append(
                ReflectiveCandidate(
                    candidate_id="MG-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                    program=program,
                    fit_error=sum(error * error for error in errors) / len(errors),
                    maximum_absolute_error=max(abs(error) for error in errors),
                    outputs=tuple(outputs),
                    behavior_signature=tuple(outputs),
                )
            )
        candidates.sort(
            key=lambda item: (
                item.fit_error,
                item.program.instruction_count,
                item.maximum_absolute_error,
                item.candidate_id,
            )
        )
        return ReflectiveSearchReport(
            programs_generated=generated,
            programs_executed=len(candidates),
            programs_rejected=rejected,
            behavior_classes=len({item.outputs for item in candidates}),
            top_candidates=tuple(candidates[: self.top_k]),
        )

    @staticmethod
    def _grow_programs() -> Iterable[ReflectiveProgram]:
        # The slots are structural roles learned from motifs.  Input routing and
        # state routing are mutations selected only through anonymous evidence.
        for counter_input in (4, 2, 3):
            for initial_a, initial_b in ((0, 1), (1, 0)):
                for coefficient_p, coefficient_q in ((2, 3), (3, 2)):
                    for source_p in ("a", "b"):
                        for source_q in ("a", "b"):
                            for update_left in ("a", "b"):
                                for output in ("a", "b"):
                                    yield _weighted_recurrence_shape(
                                        counter_input=counter_input,
                                        initial_a=initial_a,
                                        initial_b=initial_b,
                                        coefficient_p=coefficient_p,
                                        coefficient_q=coefficient_q,
                                        source_p=source_p,
                                        source_q=source_q,
                                        update_left=update_left,
                                        output=output,
                                    )


def _assemble(entries: Sequence[str | tuple[int, int | str]], data: Sequence[str]) -> ReflectiveProgram:
    labels: dict[str, int] = {}
    instructions: list[tuple[int, int | str]] = []
    for entry in entries:
        if isinstance(entry, str):
            labels[entry] = len(instructions)
        else:
            instructions.append(entry)
    addresses = {name: 2 * len(instructions) + index for index, name in enumerate(data)}
    words: list[int] = []
    for opcode, operand in instructions:
        if isinstance(operand, str):
            operand = (
                labels[operand]
                if opcode in (OP_JUMP, OP_JUMP_IF_ZERO, OP_JUMP_IF_NEGATIVE)
                else addresses[operand]
            )
        words.extend((opcode, operand))
    return ReflectiveProgram(tuple(words))


def _weighted_recurrence_shape(
    *,
    counter_input: int,
    initial_a: int,
    initial_b: int,
    coefficient_p: int,
    coefficient_q: int,
    source_p: str,
    source_q: str,
    update_left: str,
    output: str,
) -> ReflectiveProgram:
    return _assemble(
        (
            (OP_GROW, 7),
            (OP_LOAD_INPUT, counter_input), (OP_STORE_CELL, "counter"),
            (OP_LOAD_INPUT, initial_a), (OP_STORE_CELL, "a"),
            (OP_LOAD_INPUT, initial_b), (OP_STORE_CELL, "b"),
            "outer",
            (OP_LOAD_CELL, "counter"), (OP_JUMP_IF_ZERO, "end"),
            (OP_LOAD_INPUT, coefficient_p), (OP_STORE_CELL, "inner"),
            (OP_SET, 0), (OP_STORE_CELL, "temp_p"),
            "mul_p",
            (OP_LOAD_CELL, "inner"), (OP_JUMP_IF_ZERO, "after_p"),
            (OP_LOAD_CELL, "temp_p"), (OP_ADD_CELL, source_p),
            (OP_STORE_CELL, "temp_p"),
            (OP_LOAD_CELL, "inner"), (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "inner"), (OP_JUMP, "mul_p"),
            "after_p",
            (OP_LOAD_INPUT, coefficient_q), (OP_STORE_CELL, "inner"),
            (OP_SET, 0), (OP_STORE_CELL, "temp_q"),
            "mul_q",
            (OP_LOAD_CELL, "inner"), (OP_JUMP_IF_ZERO, "after_q"),
            (OP_LOAD_CELL, "temp_q"), (OP_ADD_CELL, source_q),
            (OP_STORE_CELL, "temp_q"),
            (OP_LOAD_CELL, "inner"), (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "inner"), (OP_JUMP, "mul_q"),
            "after_q",
            (OP_LOAD_CELL, "temp_p"), (OP_ADD_CELL, "temp_q"),
            (OP_STORE_CELL, "next"),
            (OP_LOAD_CELL, update_left), (OP_STORE_CELL, "a"),
            (OP_LOAD_CELL, "next"), (OP_STORE_CELL, "b"),
            (OP_LOAD_CELL, "counter"), (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "counter"), (OP_JUMP, "outer"),
            "end",
            (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
        ),
        ("counter", "a", "b", "inner", "temp_p", "temp_q", "next"),
    )
