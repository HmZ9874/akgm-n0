"""Generic law mining and independent acceptance audit for the V15 substrate."""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Callable, Sequence

from akgm_n0.learner.self_extending_substrate_v15 import (
    AnonymousTask,
    CrossTaskMacroMinerV15,
    RecurrentProposalPolicy,
    UnifiedCounterVM,
    UnifiedProgram,
    UnifiedVMError,
    default_anonymous_tasks,
    migrated_training_programs,
    primitive_leakage_audit,
    program_mutations,
    rename_registers,
    CounterexampleGuidedControllerV15,
)


@dataclass(frozen=True, slots=True)
class MinedLaw:
    law_id: str
    family: str
    statement: str
    passed: bool
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"law_id": self.law_id, "family": self.family, "statement": self.statement, "passed": self.passed, "evidence": self.evidence}


class GenericLawMinerV15:
    """Inspect behavior arity and mine laws without task names or expected formulas."""

    def __init__(self, vm: UnifiedCounterVM | None = None) -> None:
        self.vm = vm or UnifiedCounterVM()

    def mine(
        self,
        task: AnonymousTask,
        program: UnifiedProgram,
        operation_library: Sequence[UnifiedProgram] = (),
    ) -> tuple[MinedLaw, ...]:
        output_arity = len(task.cases[0][1])
        if len(task.cases[0][0]) == 2 and output_arity == 1:
            laws = list(self._binary_laws(task, program))
            laws.extend(self._recurrence_laws(task, program, operation_library))
            return tuple(laws)
        if output_arity == 2:
            return tuple(self._polynomial_relations(task))
        return ()

    def _run(self, program: UnifiedProgram, inputs: tuple[int, ...]) -> tuple[int, ...]:
        return self.vm.execute(program, inputs).outputs

    def _binary_laws(self, task: AnonymousTask, program: UnifiedProgram) -> tuple[MinedLaw, ...]:
        observed = {inputs: outputs[0] for inputs, outputs in task.cases}
        limit = min(5, max(max(inputs) for inputs in observed))

        def value(left: int, right: int) -> int:
            try:
                return observed[left, right]
            except KeyError:
                return self._run(program, (left, right))[0]

        commutative = all(value(a, b) == value(b, a) for a in range(limit + 1) for b in range(limit + 1))
        identities = tuple(e for e in range(3) if all(value(e, a) == a == value(a, e) for a in range(limit + 1)))
        annihilators = tuple(z for z in range(3) if all(value(z, a) == z == value(a, z) for a in range(limit + 1)))
        associative = all(value(value(a, b), c) == value(a, value(b, c)) for a in range(4) for b in range(4) for c in range(4))
        distributive = all(value(a, b + c) == value(a, b) + value(a, c) for a in range(4) for b in range(4) for c in range(4))
        raw = (
            ("commutative", commutative, {"limit": limit}),
            ("identity_search", bool(identities), {"values": list(identities)}),
            ("annihilator_search", bool(annihilators), {"values": list(annihilators)}),
            ("associative", associative, {"cube": 4}),
            ("distributive_over_observed_combine", distributive, {"cube": 4}),
        )
        return tuple(MinedLaw(_law_id(program, name), "generic_binary_law", name, passed, evidence) for name, passed, evidence in raw)

    def _recurrence_laws(
        self,
        task: AnonymousTask,
        program: UnifiedProgram,
        operation_library: Sequence[UnifiedProgram],
    ) -> tuple[MinedLaw, ...]:
        observed = {inputs: outputs[0] for inputs, outputs in task.cases}
        results = []
        for operation in operation_library:
            matches = True
            comparisons = 0
            for (base, count), output in observed.items():
                successor = observed.get((base, count + 1))
                if successor is None:
                    continue
                try:
                    predicted = self._run(operation, (output, base))[0]
                except UnifiedVMError:
                    matches = False
                    break
                comparisons += 1
                if predicted != successor:
                    matches = False
                    break
            results.append(MinedLaw(
                _law_id(program, "successor_via_" + operation.program_id),
                "generic_library_recurrence",
                "F(input_0,input_1+1)=LIB(F(input_0,input_1),input_0)",
                matches and comparisons > 0,
                {"library_program_id": operation.program_id, "comparisons": comparisons},
            ))
        return tuple(results)

    def _polynomial_relations(self, task: AnonymousTask) -> tuple[MinedLaw, ...]:
        rows = tuple(inputs + outputs for inputs, outputs in task.cases)
        names = tuple(f"v{index}" for index in range(len(rows[0])))
        monomials: list[tuple[int, ...]] = [(0,) * len(names)]
        for index in range(len(names)):
            powers = [0] * len(names)
            powers[index] = 1
            monomials.append(tuple(powers))
        for left in range(len(names)):
            for right in range(left, len(names)):
                powers = [0] * len(names)
                powers[left] += 1
                powers[right] += 1
                monomials.append(tuple(powers))
        matrix = [[Fraction(_monomial(row, powers)) for powers in monomials] for row in rows]
        basis = _nullspace(matrix)
        laws = []
        for vector in sorted(basis, key=lambda item: (sum(value != 0 for value in item), tuple(item)))[:8]:
            integer_vector = _integerize(vector)
            if not any(integer_vector):
                continue
            statement = _render_relation(integer_vector, monomials, names)
            laws.append(MinedLaw(
                "LAW-" + hashlib.sha256(statement.encode()).hexdigest()[:16],
                "generic_degree_two_invariant",
                statement,
                all(sum(coefficient * _monomial(row, powers) for coefficient, powers in zip(integer_vector, monomials, strict=True)) == 0 for row in rows),
                {"degree_limit": 2, "row_count": len(rows), "coefficients": integer_vector},
            ))
        return tuple(laws)


def _monomial(row: Sequence[int], powers: Sequence[int]) -> int:
    value = 1
    for item, power in zip(row, powers, strict=True):
        value *= item**power
    return value


def _nullspace(matrix: list[list[Fraction]]) -> tuple[tuple[Fraction, ...], ...]:
    if not matrix:
        return ()
    work = [list(row) for row in matrix]
    rows, columns = len(work), len(work[0])
    pivots: list[int] = []
    pivot_row = 0
    for column in range(columns):
        selected = next((row for row in range(pivot_row, rows) if work[row][column]), None)
        if selected is None:
            continue
        work[pivot_row], work[selected] = work[selected], work[pivot_row]
        scale = work[pivot_row][column]
        work[pivot_row] = [value / scale for value in work[pivot_row]]
        for row in range(rows):
            if row == pivot_row or not work[row][column]:
                continue
            factor = work[row][column]
            work[row] = [value - factor * pivot for value, pivot in zip(work[row], work[pivot_row], strict=True)]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == rows:
            break
    free = [column for column in range(columns) if column not in pivots]
    basis = []
    for free_column in free:
        vector = [Fraction(0) for _ in range(columns)]
        vector[free_column] = 1
        for row, pivot in reversed(list(enumerate(pivots))):
            vector[pivot] = -sum(work[row][column] * vector[column] for column in free)
        basis.append(tuple(vector))
    return tuple(basis)


def _integerize(vector: Sequence[Fraction]) -> list[int]:
    lcm = 1
    for value in vector:
        lcm = math_lcm(lcm, value.denominator)
    result = [int(value * lcm) for value in vector]
    divisor = 0
    for value in result:
        divisor = math_gcd(divisor, abs(value))
    if divisor:
        result = [value // divisor for value in result]
    first = next((value for value in result if value), 1)
    if first < 0:
        result = [-value for value in result]
    return result


def math_gcd(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return left


def math_lcm(left: int, right: int) -> int:
    return left * right // math_gcd(left, right)


def _render_relation(coefficients: Sequence[int], monomials: Sequence[tuple[int, ...]], names: Sequence[str]) -> str:
    terms = []
    for coefficient, powers in zip(coefficients, monomials, strict=True):
        if not coefficient:
            continue
        factors = [name + (f"^{power}" if power > 1 else "") for name, power in zip(names, powers, strict=True) if power]
        body = "*".join(factors) if factors else "1"
        terms.append(f"{coefficient:+d}*{body}")
    return " ".join(terms).lstrip("+") + " = 0"


def _law_id(program: UnifiedProgram, name: str) -> str:
    return "LAW-" + hashlib.sha256((program.program_id + name).encode()).hexdigest()[:16]


def run_v15_acceptance() -> dict[str, Any]:
    vm = UnifiedCounterVM()
    programs = migrated_training_programs()
    tasks = default_anonymous_tasks()
    mutations = {task_id: program_mutations(program) for task_id, program in programs.items()}
    mistakes = tuple(item for values in mutations.values() for item in values)
    policy = RecurrentProposalPolicy()
    policy.fit(tuple(programs.values()), mistakes)
    controller = CounterexampleGuidedControllerV15(policy, vm)
    reconstructions = []
    selected: dict[str, UnifiedProgram] = {}
    for task_id, source in programs.items():
        candidates = list(mutations[task_id]) + [source]
        permutations = itertools.islice(itertools.permutations(range(source.register_count)), 12)
        candidates.extend(rename_registers(source, permutation) for permutation in permutations)
        result = controller.synthesize(tasks[task_id], tuple(candidates))
        selected[task_id] = result.selected
        reconstructions.append({
            "task_id": task_id,
            "candidate_count": len(candidates),
            "converged": result.converged,
            "selected_program_id": result.selected.program_id,
            "round_count": len(result.rounds),
            "case_evaluations": result.case_evaluations,
            "exhaustive_case_evaluations": result.exhaustive_case_evaluations,
            "evaluation_reduction": result.evaluation_reduction,
            "rounds": [
                {
                    "round_index": round_.round_index,
                    "active_case_indices": list(round_.active_case_indices),
                    "candidates_replayed": round_.candidates_replayed,
                    "selected_program_id": round_.selected_program_id,
                    "counterexample_index": round_.counterexample_index,
                }
                for round_ in result.rounds
            ],
        })
    aggregate_actual = sum(item["case_evaluations"] for item in reconstructions)
    aggregate_exhaustive = sum(item["exhaustive_case_evaluations"] for item in reconstructions)
    macros = CrossTaskMacroMinerV15().mine(selected)
    leakage = primitive_leakage_audit(selected.values())
    laws = {}
    miner = GenericLawMinerV15(vm)
    library = tuple(selected.values())
    for task_id, program in selected.items():
        laws[task_id] = [law.to_dict() for law in miner.mine(tasks[task_id], program, library)]
    rename_checks = []
    for task_id, program in selected.items():
        permutation = tuple(reversed(range(program.register_count)))
        renamed = rename_registers(program, permutation)
        passed = all(vm.execute(renamed, inputs).outputs == expected for inputs, expected in tasks[task_id].cases)
        rename_checks.append({"task_id": task_id, "passed": passed, "permutation": list(permutation)})
    proof_obligations = (
        {"obligation_id": "one_vm_for_all_tasks", "passed": len({program.to_dict()["substrate"] for program in selected.values()}) == 1},
        {"obligation_id": "primitive_opcode_boundary", "passed": leakage["passed"]},
        {"obligation_id": "three_reconstructions_converged", "passed": all(item["converged"] for item in reconstructions)},
        {"obligation_id": "aggregate_search_reduction_at_least_80_percent", "passed": 1 - aggregate_actual / aggregate_exhaustive >= 0.8},
        {"obligation_id": "register_renaming_invariance", "passed": all(item["passed"] for item in rename_checks)},
        {"obligation_id": "cross_task_macro_support", "passed": bool(macros) and macros[0].task_support >= 3},
        {"obligation_id": "macro_saves_expanded_tokens", "passed": bool(macros) and macros[0].savings_per_use > 0},
        {"obligation_id": "generic_law_mining_produced_evidence", "passed": all(any(law["passed"] for law in items) for items in laws.values())},
        {"obligation_id": "cold_start_claim_withheld", "passed": all(program.provenance != "cold_start_discovery" for program in programs.values())},
    )
    return {
        "benchmark_version": "self-extending-substrate-v15.1",
        "passed": all(item["passed"] for item in proof_obligations),
        "classification": "verified_unified_substrate_with_migrated_training_memory",
        "vm": {
            "opcodes": sorted(next(iter(selected.values())).to_dict()["instructions"][0].keys()) if False else sorted({item.op for program in selected.values() for item in program.instructions}),
            "programs": {task_id: program.to_dict() for task_id, program in selected.items()},
        },
        "reconstructions": reconstructions,
        "aggregate": {
            "case_evaluations": aggregate_actual,
            "exhaustive_case_evaluations": aggregate_exhaustive,
            "evaluation_reduction": 1 - aggregate_actual / aggregate_exhaustive,
        },
        "proposal_policy": {
            "architecture": "first_order_recurrent_opcode_policy",
            "transformer": False,
            "positive_transition_count": sum(policy.transition_counts.values()),
            "negative_transition_count": sum(policy.negative_transitions.values()),
        },
        "macros": [item.to_dict() for item in macros[:20]],
        "generic_laws": laws,
        "register_renaming": rename_checks,
        "leakage_audit": leakage,
        "proof_obligations": list(proof_obligations),
        "limitations": [
            "The three seed programs are migrated audited memories, so this is not a cold-start rediscovery result.",
            "The structured compiler and mutation operators remain host code.",
            "Macros are mined and scored but are expanded before execution; runtime opcode self-installation remains future work.",
            "Generic law mining is bounded to binary laws, library recurrences, and degree-two polynomial invariants.",
        ],
    }
