"""Run the first isolated MetaMachine Gen 1 state-graph experiment."""

from __future__ import annotations

import itertools
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import HiddenSymbolTraceEnvironment, KnowledgeLedger
from akgm_n0.learner import (
    StateGraphExecutor,
    StateGraphLibrary,
    StateGraphProgram,
    StateGraphSearch,
)


SECRET = b"local-metamachine-gen1-v0.1"
SYMBOL_PERMUTATION = (1, 0)


def observation(traces: tuple[tuple[int, ...], ...], seed: int):
    return HiddenSymbolTraceEnvironment(
        traces,
        seed=seed,
        secret=SECRET,
        symbol_permutation=SYMBOL_PERMUTATION,
    ).observe()


def has_reachable_nontrivial_cycle(program: StateGraphProgram) -> bool:
    reachable = {program.initial_state_id}
    pending = [program.initial_state_id]
    while pending:
        state = pending.pop()
        for target in program.transition_table[state]:
            if target not in reachable:
                reachable.add(target)
                pending.append(target)
    for start in reachable:
        frontier = [
            target for target in program.transition_table[start] if target != start
        ]
        seen: set[int] = set()
        while frontier:
            state = frontier.pop()
            if state == start:
                return True
            if state in seen:
                continue
            seen.add(state)
            frontier.extend(program.transition_table[state])
    return False


def main() -> int:
    development_private = (
        (),
        (0,),
        (1,),
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    )
    development = observation(development_private, 104729)
    search_report = StateGraphSearch(maximum_state_count=3, top_k=20).search(
        development
    )
    exact = [item for item in search_report.top_candidates if item.fit_error == 0.0]
    if not exact:
        raise RuntimeError("development search found no exact state graph")
    selected = exact[0]

    exhaustive_blind = tuple(
        trace
        for length in range(3, 9)
        for trace in itertools.product((0, 1), repeat=length)
    )
    long_blind = (
        tuple((index * 7 + 1) % 2 for index in range(31)),
        tuple((index * 5 + 3) % 2 for index in range(64)),
    )
    blind_private = exhaustive_blind + long_blind
    blind = observation(blind_private, 130363)
    executor = StateGraphExecutor()
    case_results = []
    for index, (trace, expected) in enumerate(
        zip(blind.symbol_traces, blind.output_values, strict=True)
    ):
        execution = executor.execute(selected.program, trace)
        case_results.append(
            {
                "case_index": index,
                "trace_length": len(trace),
                "predicted_value": execution.output_value,
                "observed_value": expected,
                "passed": execution.output_value == expected,
                "visited_state_count": len(set(execution.visited_state_ids)),
            }
        )
    blind_passed = all(item["passed"] for item in case_results)
    nontrivial_cycle = has_reachable_nontrivial_cycle(selected.program)
    uses_distinct_internal_states = selected.reachable_state_count >= 2

    semantic_library = StateGraphLibrary()
    promoted = semantic_library.promote(selected.program) if blind_passed else None
    promoted_replay_passed = False
    if promoted is not None:
        promoted_replay_passed = all(
            semantic_library.execute(promoted.operation_id, trace).output_value == expected
            for trace, expected in zip(
                blind.symbol_traces, blind.output_values, strict=True
            )
        )

    gates = [
        {
            "gate_id": "development_exact",
            "passed": selected.fit_error == 0.0,
            "actual": selected.fit_error,
            "threshold": 0.0,
        },
        {
            "gate_id": "exhaustive_unseen_lengths_3_to_8",
            "passed": all(item["passed"] for item in case_results[:-2]),
            "actual": sum(item["passed"] for item in case_results[:-2]),
            "threshold": len(case_results) - 2,
        },
        {
            "gate_id": "maximum_registered_length_64",
            "passed": case_results[-1]["passed"],
            "actual": case_results[-1]["trace_length"],
            "threshold": 64,
        },
        {
            "gate_id": "reachable_nontrivial_state_cycle",
            "passed": nontrivial_cycle,
            "actual": nontrivial_cycle,
            "threshold": True,
        },
        {
            "gate_id": "distinct_internal_state_reuse",
            "passed": uses_distinct_internal_states,
            "actual": selected.reachable_state_count,
            "threshold": 2,
        },
        {
            "gate_id": "promoted_operation_replay",
            "passed": promoted_replay_passed,
            "actual": promoted_replay_passed,
            "threshold": True,
        },
        {
            "gate_id": "autonomous_completion",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
        {
            "gate_id": "dynamic_storage_topology",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    completed = [gate for gate in gates if gate["passed"] is not None]
    verdict = (
        "conditionally_passed"
        if all(gate["passed"] for gate in completed)
        else "failed"
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-metamachine-gen1-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        selected.program,
        parent_ids=("raw_symbol_feed", "anonymous_state_id", "transition_table"),
        provenance={
            "run_id": run_id,
            "search_version": "state-graph-enumerator-v0.1",
            "candidate_id": selected.candidate_id,
        },
        evidence={"development_fit_error": selected.fit_error},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="anonymous_development_traces_exact",
        evidence={"trace_count": len(development_private)},
    )
    if blind_passed and nontrivial_cycle and promoted_replay_passed:
        ledger.transition(
            knowledge_id,
            "verified",
            reason="sealed_longer_traces_and_promoted_replay_passed",
            evidence={"blind_case_count": len(case_results)},
        )
        ledger.transition(
            knowledge_id,
            "bounded",
            reason="host_supplied_completion_and_fixed_state_bound",
            evidence={
                "pending_gates": [
                    gate["gate_id"] for gate in gates if gate["passed"] is None
                ]
            },
        )
    else:
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="registered_metamachine_gate_failed",
            evidence={
                "failed_gates": [
                    gate["gate_id"] for gate in gates if gate["passed"] is False
                ]
            },
        )

    report = {
        "report_version": "metamachine-gen1-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "MetaMachine Gen 1：匿名状态语义生长",
        "verdict": verdict,
        "knowledge_status": ledger.get(knowledge_id).status,
        "claim_scope": "two_symbol_finite_traces_up_to_64_steps",
        "architecture": "enumerated_state_graphs_not_transformer",
        "learner_received": {
            "natural_language": False,
            "target_name": False,
            "target_formula": False,
            "arithmetic_operations": [],
            "structured_storage_operations": [],
            "repetition_operations": [],
            "supplied_substrate": [
                "anonymous_symbol_feed",
                "finite_state_ids",
                "transition_table_execution",
                "completion_after_last_supplied_symbol",
            ],
        },
        "development": {
            "trace_count": len(development_private),
            "maximum_trace_length": 2,
            "programs_generated": search_report.programs_generated,
            "programs_scored_after_canonicalization": search_report.programs_scored,
            "selected_candidate": selected.to_dict(),
        },
        "blind_verification": {
            "search_access": False,
            "case_count": len(case_results),
            "passed_case_count": sum(item["passed"] for item in case_results),
            "failed_case_count": sum(not item["passed"] for item in case_results),
            "exhaustive_lengths": [3, 4, 5, 6, 7, 8],
            "additional_lengths": [31, 64],
            "case_results": case_results,
        },
        "structural_findings": {
            "reachable_state_count": selected.reachable_state_count,
            "reachable_nontrivial_cycle": nontrivial_cycle,
            "distinct_internal_state_reuse": uses_distinct_internal_states,
            "host_supplied_repetition_instruction": False,
            "host_supplied_completion": True,
        },
        "promoted_semantic": (
            {
                **promoted.to_dict(),
                "knowledge_id": knowledge_id,
                "ledger_status": ledger.get(knowledge_id).status,
                "replay_passed": promoted_replay_passed,
            }
            if promoted is not None
            else None
        ),
        "post_hoc_evaluator_interpretation": {
            "assigned_after_blind_verification": True,
            "statement": "One visible symbol preserves the internal state; the other alternates between two states. The final state encodes the parity of one private symbol count.",
            "common_human_analogy": "a one-bit parity accumulator implemented as a two-state machine",
        },
        "gates": gates,
        "ledger_event_count": len(ledger.events),
        "limitations": [
            "The host still supplies one-symbol-per-step execution and completion after the final input symbol.",
            "The search is limited to at most three states, two symbols, two outputs, and 64 supplied steps.",
            "The result creates a derived executable semantic layer, not a new physical computation law.",
            "Autonomous stopping, dynamic storage growth, self-modifying programs, and cross-task semantic composition remain unverified.",
            "The post-hoc human interpretation was not available to the learner during search.",
        ],
    }
    artifact_path = run_directory / "metamachine_gen1_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    registry_path = run_directory / "semantic_registry.json"
    with registry_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(
            {
                "registry_version": "state-graph-semantic-registry-v0.1",
                "entries": [entry.to_dict() for entry in semantic_library.entries],
            },
            stream,
            ensure_ascii=False,
            indent=2,
        )
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "metamachine_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    dashboard_path = PROJECT_ROOT / "dashboard" / "data" / "metamachine_latest.json"
    if dashboard_path.parent.parent.exists():
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, dashboard_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": verdict,
                "knowledge_status": ledger.get(knowledge_id).status,
                "candidate_id": selected.candidate_id,
                "operation_id": promoted.operation_id if promoted else None,
                "programs_generated": search_report.programs_generated,
                "blind_passed": sum(item["passed"] for item in case_results),
                "blind_total": len(case_results),
                "reachable_nontrivial_cycle": nontrivial_cycle,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verdict == "conditionally_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
