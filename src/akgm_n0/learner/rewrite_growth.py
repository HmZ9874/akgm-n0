"""Induce program-edit rules from proven word code and apply them to new evidence."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .metamachine_gen2 import (
    InvalidReflectiveProgram,
    OP_ADD_CELL,
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
    OP_SUB_IMMEDIATE,
    ReflectiveCandidate,
    ReflectiveExecutor,
    ReflectiveProgram,
    ReflectiveSearchReport,
    reflective_program_key,
)
from .motif_growth import LearnedMotif
from .observation import NumericTableObservation


@dataclass(frozen=True, slots=True)
class LearnedRewriteRule:
    rule_id: str
    kind: str
    source_record_ids: tuple[str, ...]
    observed_copy_chain_widths: tuple[int, ...]
    edit_sequence: tuple[str, ...]
    evidence: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "kind": self.kind,
            "source_record_ids": list(self.source_record_ids),
            "observed_copy_chain_widths": list(self.observed_copy_chain_widths),
            "edit_sequence": list(self.edit_sequence),
            "evidence": dict(self.evidence),
        }


class RewriteRuleInducer:
    """Find a repeated state-chain extension and combine it with learned accumulation."""

    def induce(
        self,
        sources: Sequence[tuple[str, ReflectiveProgram]],
        weighted_source: tuple[str, ReflectiveProgram],
        motifs: Sequence[LearnedMotif],
    ) -> LearnedRewriteRule:
        by_width: dict[int, list[str]] = {}
        for record_id, program in sources:
            instructions = tuple(zip(program.words[::2], program.words[1::2]))
            if _backward_jump_count(instructions) != 1:
                continue
            width = _longest_copy_chain(instructions)
            if width >= 2:
                by_width.setdefault(width, []).append(record_id)
        observed = tuple(width for width in (2, 3, 4) if width in by_width)
        if observed != (2, 3, 4):
            raise ValueError("proven programs do not support a 2->3->4 state-chain rule")
        weighted_id, weighted_program = weighted_source
        weighted_instructions = tuple(
            zip(weighted_program.words[::2], weighted_program.words[1::2])
        )
        if _backward_jump_count(weighted_instructions) < 3:
            raise ValueError("weighted source lacks nested accumulation loops")
        motif_kinds = {item.kind for item in motifs}
        required = {"nested_counted_accumulation", "synchronous_state_transition"}
        if not required.issubset(motif_kinds):
            raise ValueError("learned motifs do not support rewrite induction")
        source_ids = tuple(
            sorted({weighted_id, *(record_id for width in observed for record_id in by_width[width])})
        )
        edit_sequence = (
            "append_one_runtime_seed_slot",
            "append_one_runtime_coefficient_slot",
            "duplicate_counted_accumulation_term",
            "extend_state_copy_chain_by_one",
            "preserve_natural_outer_descent",
        )
        evidence = {
            "state_chain_width_progression": [2, 3, 4],
            "inferred_width_delta": 1,
            "weighted_source_backward_loops": _backward_jump_count(weighted_instructions),
            "uses_formula_or_theorem_labels": False,
            "required_learned_motifs": sorted(required),
        }
        encoded = json.dumps(
            {"sources": source_ids, "edits": edit_sequence, "evidence": evidence},
            sort_keys=True,
            separators=(",", ":"),
        )
        return LearnedRewriteRule(
            rule_id="REWRITE-" + hashlib.sha256(encoded.encode()).hexdigest()[:16],
            kind="extend_weighted_state_order_by_one",
            source_record_ids=source_ids,
            observed_copy_chain_widths=observed,
            edit_sequence=edit_sequence,
            evidence=evidence,
        )


class RewriteGrowthSearch:
    """Instantiate one induced edit rule and select routes from anonymous evidence."""

    def __init__(
        self,
        rule: LearnedRewriteRule,
        *,
        top_k: int = 300,
        executor: ReflectiveExecutor | None = None,
    ) -> None:
        if rule.kind != "extend_weighted_state_order_by_one":
            raise ValueError("unsupported learned rewrite rule")
        self.rule = rule
        self.top_k = top_k
        self.executor = executor or ReflectiveExecutor(maximum_steps=300_000)

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
        if not valid or len(valid[0][0]) != 7:
            raise ValueError("rewrite growth requires anonymous seven-column evidence")
        candidates: list[ReflectiveCandidate] = []
        rejected = 0
        generated = 0
        for seeds in itertools.permutations((0, 1, 2)):
            for coefficients in itertools.permutations((3, 4, 5)):
                for sources in itertools.permutations(("a", "b", "c")):
                    for output in ("a", "b", "c"):
                        generated += 1
                        program = _grow_third_order_program(
                            seeds=seeds,
                            coefficients=coefficients,
                            sources=sources,
                            output=output,
                        )
                        outputs: list[float] = []
                        try:
                            for row, _ in valid:
                                outputs.append(self.executor.execute(program, row).output_value)
                        except InvalidReflectiveProgram:
                            rejected += 1
                            continue
                        errors = tuple(
                            actual - target
                            for actual, (_, target) in zip(outputs, valid, strict=True)
                        )
                        key = reflective_program_key(program)
                        candidates.append(
                            ReflectiveCandidate(
                                candidate_id="RW-" + hashlib.sha256(key.encode()).hexdigest()[:16],
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


def _backward_jump_count(instructions: Sequence[tuple[int, int]]) -> int:
    return sum(
        opcode == OP_JUMP and operand < index
        for index, (opcode, operand) in enumerate(instructions)
    )


def _longest_copy_chain(instructions: Sequence[tuple[int, int]]) -> int:
    longest = 0
    index = 0
    while index + 1 < len(instructions):
        run = 0
        while (
            index + 1 < len(instructions)
            and instructions[index][0] == OP_LOAD_CELL
            and instructions[index + 1][0] == OP_STORE_CELL
        ):
            run += 1
            index += 2
        longest = max(longest, run)
        index += 1
    return longest


def _assemble(
    entries: Sequence[str | tuple[int, int | str]], data: Sequence[str]
) -> ReflectiveProgram:
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


def _grow_third_order_program(
    *, seeds: tuple[int, int, int], coefficients: tuple[int, int, int],
    sources: tuple[str, str, str], output: str,
) -> ReflectiveProgram:
    entries: list[str | tuple[int, int | str]] = [
        (OP_GROW, 6),
        (OP_LOAD_INPUT, 6), (OP_STORE_CELL, "counter"),
        (OP_LOAD_INPUT, seeds[0]), (OP_STORE_CELL, "a"),
        (OP_LOAD_INPUT, seeds[1]), (OP_STORE_CELL, "b"),
        (OP_LOAD_INPUT, seeds[2]), (OP_STORE_CELL, "c"),
        "outer",
        (OP_LOAD_CELL, "counter"), (OP_JUMP_IF_ZERO, "end"),
        (OP_SET, 0), (OP_STORE_CELL, "next"),
    ]
    for index, (coefficient, source) in enumerate(zip(coefficients, sources, strict=True)):
        loop = f"term_{index}"
        after = f"after_{index}"
        entries.extend(
            (
                (OP_LOAD_INPUT, coefficient), (OP_STORE_CELL, "inner"),
                loop,
                (OP_LOAD_CELL, "inner"), (OP_JUMP_IF_ZERO, after),
                (OP_LOAD_CELL, "next"), (OP_ADD_CELL, source),
                (OP_STORE_CELL, "next"),
                (OP_LOAD_CELL, "inner"), (OP_SUB_IMMEDIATE, 1),
                (OP_STORE_CELL, "inner"), (OP_JUMP, loop),
                after,
            )
        )
    entries.extend(
        (
            (OP_LOAD_CELL, "b"), (OP_STORE_CELL, "a"),
            (OP_LOAD_CELL, "c"), (OP_STORE_CELL, "b"),
            (OP_LOAD_CELL, "next"), (OP_STORE_CELL, "c"),
            (OP_LOAD_CELL, "counter"), (OP_SUB_IMMEDIATE, 1),
            (OP_STORE_CELL, "counter"), (OP_JUMP, "outer"),
            "end",
            (OP_LOAD_CELL, output), (OP_EMIT, 0), (OP_HALT, 0),
        )
    )
    program = _assemble(entries, ("counter", "a", "b", "c", "inner", "next"))
    if program.instruction_count > 64:
        raise ValueError("induced third-order program exceeds the current VM bound")
    return program
