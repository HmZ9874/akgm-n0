"""Independent worlds and acceptance verifier for V16 cold-start semantics."""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
from dataclasses import dataclass, replace
from typing import Any, Sequence

from akgm_n0.learner.cold_start_semantics_v16 import (
    BASE_OPS,
    DATA_OPS,
    ColdStartSemanticResearcherV16,
    OperatorDefinitionV16,
    PrimitiveWorkload,
    RuntimeInstruction,
    SelfExtendingCounterVM,
    SemanticRuntimeError,
    compress_with_operator,
    operator_surface_audit,
)


@dataclass(frozen=True, slots=True)
class OperatorVerificationV16:
    operator_id: str
    passed: bool
    certificate_digest_matches: bool
    exhaustive_cases: int
    counterexample: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "passed": self.passed,
            "certificate_digest_matches": self.certificate_digest_matches,
            "exhaustive_cases": self.exhaustive_cases,
            "counterexample": self.counterexample,
        }


class IndependentSemanticVerifierV16:
    """Compare runtime dispatch against the frozen primitive certificate."""

    def verify(
        self,
        definition: OperatorDefinitionV16,
        installed_vm: SelfExtendingCounterVM,
        *,
        value_limit: int = 3,
    ) -> OperatorVerificationV16:
        recomputed = installed_vm.flatten_body(definition.body)
        recomputed_digest = hashlib.sha256(
            json.dumps([item.to_dict() for item in recomputed], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        digest_matches = recomputed_digest == definition.certificate_digest and recomputed == definition.primitive_body
        reference_vm = SelfExtendingCounterVM()
        register_count = max(2, definition.arity)
        checked = 0
        first_counterexample = None
        for binding in itertools.product(range(register_count), repeat=definition.arity):
            for state in itertools.product(range(value_limit + 1), repeat=register_count):
                checked += 1
                direct = self._capture(
                    installed_vm,
                    (RuntimeInstruction(definition.operator_id, tuple(binding)),),
                    state,
                )
                reference = self._capture(
                    reference_vm,
                    tuple(
                        RuntimeInstruction(item.op, tuple(binding[role] for role in item.operands))
                        for item in definition.primitive_body
                    ),
                    state,
                )
                if direct != reference and first_counterexample is None:
                    first_counterexample = {
                        "binding": list(binding),
                        "state": list(state),
                        "runtime": direct,
                        "certificate": reference,
                    }
        passed = digest_matches and first_counterexample is None
        if not digest_matches and first_counterexample is None:
            first_counterexample = {"kind": "certificate_digest_mismatch"}
        return OperatorVerificationV16(definition.operator_id, passed, digest_matches, checked, first_counterexample)

    @staticmethod
    def _capture(
        vm: SelfExtendingCounterVM,
        instructions: Sequence[RuntimeInstruction],
        state: Sequence[int],
    ) -> list[Any]:
        try:
            final, _, _ = vm.apply_sequence(instructions, state)
            return ["ok", list(final)]
        except SemanticRuntimeError as error:
            return ["error", str(error)]


def anonymous_primitive_workloads(
    seed: int,
    *,
    phase_nonce: str,
    family_count: int = 4,
    workloads_per_family: int = 64,
    instruction_count: int = 40,
) -> tuple[PrimitiveWorkload, ...]:
    """Create target-free primitive traces; the nonce separates train/holdout."""

    mixed_seed = int(hashlib.sha256(f"{seed}:{phase_nonce}".encode()).hexdigest()[:16], 16)
    rng = random.Random(mixed_seed)
    profiles = (
        ("u_inc", "u_inc", "u_dec", "u_zero", "u_unit"),
        ("u_zero", "u_unit", "u_inc", "u_inc", "u_dec"),
        ("u_inc", "u_dec", "u_zero", "u_unit", "u_dec"),
        ("u_unit", "u_inc", "u_zero", "u_inc", "u_dec"),
    )
    workloads = []
    for family_index in range(family_count):
        family_id = f"F-{family_index:02d}"
        register_count = 3 + family_index % 2
        choices = profiles[family_index % len(profiles)]
        for workload_index in range(workloads_per_family):
            initial = [rng.randrange(0, 5) for _ in range(register_count)]
            state = list(initial)
            instructions = []
            previous_op: str | None = None
            previous_register: int | None = None
            for _ in range(instruction_count):
                draw = rng.random()
                if previous_op is not None and draw < 0.36:
                    op = previous_op
                    register = previous_register  # type: ignore[assignment]
                elif previous_op is not None and draw < 0.58:
                    op = previous_op
                    register = rng.randrange(register_count)
                elif previous_register is not None and draw < 0.76:
                    op = rng.choice(choices)
                    register = previous_register
                else:
                    op = rng.choice(choices)
                    register = rng.randrange(register_count)
                if op == "u_dec" and state[register] == 0:
                    op = "u_inc"
                if op == "u_zero":
                    state[register] = 0
                elif op == "u_unit":
                    state[register] = 1
                elif op == "u_inc":
                    state[register] += 1
                elif op == "u_dec":
                    state[register] -= 1
                instructions.append(RuntimeInstruction(op, (register,)))
                previous_op = op
                previous_register = register
            payload = {
                "seed": mixed_seed,
                "family": family_id,
                "index": workload_index,
                "instructions": [item.to_dict() for item in instructions],
            }
            workload_id = "W-" + hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:16]
            workloads.append(PrimitiveWorkload(
                family_id, workload_id, register_count, tuple(initial), tuple(instructions),
            ))
    return tuple(workloads)


def _mutate_definition(definition: OperatorDefinitionV16) -> OperatorDefinitionV16:
    body = list(definition.body)
    for index, item in enumerate(body):
        if item.op in DATA_OPS:
            replacement = "u_zero" if item.op != "u_zero" else "u_inc"
            body[index] = replace(item, op=replacement)
            return replace(definition, body=tuple(body))
    raise RuntimeError("mutation audit could not find a primitive body instruction")


def _install_and_verify(
    definitions: Sequence[OperatorDefinitionV16],
) -> tuple[SelfExtendingCounterVM, tuple[OperatorVerificationV16, ...]]:
    vm = SelfExtendingCounterVM()
    verifier = IndependentSemanticVerifierV16()
    reports = []
    for definition in definitions:
        vm.install_operator(definition)
        reports.append(verifier.verify(definition, vm))
    return vm, tuple(reports)


def _holdout_audit(
    definitions: Sequence[OperatorDefinitionV16],
    holdout: Sequence[PrimitiveWorkload],
) -> dict[str, Any]:
    vm, verification = _install_and_verify(definitions)
    streams = {item.workload_id: item.instructions for item in holdout}
    families = {item.workload_id: item.family_id for item in holdout}
    usage = []
    for definition in definitions:
        family_set: set[str] = set()
        occurrences = 0
        for workload_id, stream in tuple(streams.items()):
            compressed, uses = compress_with_operator(stream, definition)
            if uses:
                family_set.add(families[workload_id])
                occurrences += uses
            streams[workload_id] = compressed
        usage.append({
            "operator_id": definition.operator_id,
            "family_support": len(family_set),
            "occurrences": occurrences,
        })

    before_tokens = sum(item.encoded_tokens for item in holdout)
    after_tokens = sum(sum(instruction.encoded_tokens for instruction in streams[item.workload_id]) for item in holdout)
    exact_replays = 0
    dynamic_dispatches = 0
    primitive_vm = SelfExtendingCounterVM()
    failures = []
    for workload in holdout:
        try:
            expected, _, _ = primitive_vm.apply_sequence(workload.instructions, workload.initial_state)
            actual, dispatches, _ = vm.apply_sequence(streams[workload.workload_id], workload.initial_state)
            if expected == actual:
                exact_replays += 1
            else:
                failures.append({"workload_id": workload.workload_id, "expected": list(expected), "actual": list(actual)})
            dynamic_dispatches += dispatches
        except SemanticRuntimeError as error:
            failures.append({"workload_id": workload.workload_id, "error": str(error)})
    return {
        "operator_verification": [item.to_dict() for item in verification],
        "operator_usage": usage,
        "workload_count": len(holdout),
        "exact_replays": exact_replays,
        "failures": failures[:10],
        "tokens_before": before_tokens,
        "tokens_after": after_tokens,
        "token_reduction": 1.0 - after_tokens / before_tokens,
        "dynamic_dispatches": dynamic_dispatches,
    }


def _mutation_audit(definition: OperatorDefinitionV16) -> dict[str, Any]:
    mutated = _mutate_definition(definition)
    vm = SelfExtendingCounterVM()
    vm.install_operator(mutated)
    result = IndependentSemanticVerifierV16().verify(mutated, vm)
    return {
        "candidate_id": mutated.operator_id,
        "rejected": not result.passed,
        "reason": "certificate_or_behavior_counterexample",
        "counterexample": result.counterexample,
    }


def run_v16_acceptance(*, trials: int = 20) -> dict[str, Any]:
    if trials < 1:
        raise ValueError("at least one cold-start trial is required")
    trial_reports = []
    for trial_index in range(trials):
        seed = 91_003 + trial_index * 7_919
        training = anonymous_primitive_workloads(seed, phase_nonce="learner-visible")
        holdout = anonymous_primitive_workloads(seed, phase_nonce="evaluator-sealed")
        researcher = ColdStartSemanticResearcherV16()
        discovery = researcher.discover(training)
        holdout_report = _holdout_audit(discovery.operators, holdout)
        mutation = _mutation_audit(discovery.operators[0]) if discovery.operators else {
            "candidate_id": None, "rejected": False, "counterexample": None,
        }
        trial_reports.append({
            "trial_index": trial_index,
            "seed_commitment": hashlib.sha256(str(seed).encode()).hexdigest(),
            "manifest": discovery.manifest,
            "installed_operator_count": len(discovery.operators),
            "generation_depth": max((item.generation for item in discovery.operators), default=0),
            "operators": [item.to_dict() for item in discovery.operators],
            "training": {
                "tokens_before": discovery.training_tokens_before,
                "tokens_after": discovery.training_tokens_after,
                "token_reduction": discovery.training_reduction,
            },
            "holdout": holdout_report,
            "rejected_candidate_count": len(discovery.rejected),
            "sample_rejections": [item.to_dict() for item in discovery.rejected[:8]],
            "mutation_audit": mutation,
        })

    all_operators = [operator for trial in trial_reports for operator in trial["operators"]]
    # Hashes are deliberately excluded: a hexadecimal id can contain strings
    # such as "add" by chance.  The executable opcode surfaces are the subject
    # of this leakage audit.
    executable_opcodes = [
        instruction["op"].lower()
        for operator in all_operators
        for body_name in ("body", "primitive_body")
        for instruction in operator[body_name]
    ]
    readable_opcodes = [
        opcode for opcode in executable_opcodes
        if opcode not in BASE_OPS and re.fullmatch(r"nu_[0-9a-f]{12}", opcode) is None
    ]
    forbidden = ("add", "subtract", "multiply", "divide", "power", "root", "log", "formula", "target")
    forbidden_hits = sorted({term for term in forbidden for opcode in readable_opcodes if term in opcode})
    surface = {
        "passed": not forbidden_hits and not readable_opcodes,
        "forbidden_hits": forbidden_hits,
        "non_opaque_dynamic_opcodes": readable_opcodes,
        "opaque_dynamic_id_pattern": "nu_[0-9a-f]{12}",
    }

    obligations = (
        {"obligation_id": "twenty_independent_cold_starts", "passed": trials >= 20 and len(trial_reports) == trials},
        {"obligation_id": "zero_migrated_or_seed_success_programs", "passed": all(
            trial["manifest"]["initial_success_program_count"] == 0
            and trial["manifest"]["imported_program_count"] == 0
            and trial["manifest"]["prior_artifact_reads"] == 0
            for trial in trial_reports
        )},
        {"obligation_id": "initial_registry_is_exactly_eight_primitives", "passed": all(
            set(trial["manifest"]["base_opcodes"]) == BASE_OPS
            and trial["manifest"]["initial_dynamic_operator_count"] == 0
            for trial in trial_reports
        )},
        {"obligation_id": "at_least_five_runtime_operators_each_trial", "passed": all(trial["installed_operator_count"] >= 5 for trial in trial_reports)},
        {"obligation_id": "recursive_operator_composition_each_trial", "passed": all(trial["generation_depth"] >= 2 for trial in trial_reports)},
        {"obligation_id": "all_operator_certificates_independently_verified", "passed": all(
            all(item["passed"] for item in trial["holdout"]["operator_verification"])
            for trial in trial_reports
        )},
        {"obligation_id": "every_operator_reused_in_three_holdout_families", "passed": all(
            all(item["family_support"] >= 3 for item in trial["holdout"]["operator_usage"])
            for trial in trial_reports
        )},
        {"obligation_id": "sealed_holdout_replay_is_exact", "passed": all(
            trial["holdout"]["exact_replays"] == trial["holdout"]["workload_count"]
            and not trial["holdout"]["failures"]
            for trial in trial_reports
        )},
        {"obligation_id": "runtime_dynamic_dispatch_observed", "passed": all(trial["holdout"]["dynamic_dispatches"] > 0 for trial in trial_reports)},
        {"obligation_id": "holdout_token_reduction_at_least_thirty_percent", "passed": all(trial["holdout"]["token_reduction"] >= 0.30 for trial in trial_reports)},
        {"obligation_id": "mutated_semantics_enter_mistake_room", "passed": all(trial["mutation_audit"]["rejected"] for trial in trial_reports)},
        {"obligation_id": "no_named_high_level_operation_or_target_formula", "passed": surface["passed"]},
    )
    return {
        "benchmark_version": "cold-start-runtime-semantics-v16.0",
        "passed": all(item["passed"] for item in obligations),
        "classification": "verified_cold_start_runtime_semantic_abstraction",
        "base_opcodes": sorted(BASE_OPS),
        "trial_count": trials,
        "trials": trial_reports,
        "aggregate": {
            "installed_operator_count": sum(trial["installed_operator_count"] for trial in trial_reports),
            "minimum_operators_per_trial": min(trial["installed_operator_count"] for trial in trial_reports),
            "minimum_generation_depth": min(trial["generation_depth"] for trial in trial_reports),
            "mean_training_token_reduction": sum(trial["training"]["token_reduction"] for trial in trial_reports) / trials,
            "mean_holdout_token_reduction": sum(trial["holdout"]["token_reduction"] for trial in trial_reports) / trials,
            "holdout_workloads": sum(trial["holdout"]["workload_count"] for trial in trial_reports),
            "exact_holdout_replays": sum(trial["holdout"]["exact_replays"] for trial in trial_reports),
            "dynamic_dispatches": sum(trial["holdout"]["dynamic_dispatches"] for trial in trial_reports),
            "mutations_rejected": sum(trial["mutation_audit"]["rejected"] for trial in trial_reports),
        },
        "surface_audit": surface,
        "proof_obligations": list(obligations),
        "limitations": [
            "This proves cold-start runtime abstraction from recurring primitive programs, not discovery of all mathematics from raw numeric observations.",
            "The eight primitive actions, finite workload generator, and minimum-description-length reward are externally supplied.",
            "Equivalence is exhaustive only inside the stated finite counter and operand bounds; replay adds independently seeded workloads.",
            "Installed operators are acyclic parameterized programs; unrestricted self-modifying control flow is not claimed.",
        ],
    }
