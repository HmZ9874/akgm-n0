from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import AdaptiveMistakeLibrary, FormulaSuccessRoom
from akgm_n0.learner import (
    AutonomousExperimentLoop,
    CompositionExecutor,
    CompositionGraphProgram,
    CompositionGraphSearch,
    CompositionNode,
    DisagreementExperimentPlanner,
    ProofCarryingReasoner,
    ReasoningTraceVerifier,
    ReflectiveProgram,
)


def main() -> int:
    proof_report = json.loads(
        (ROOT / "reports/data/universal_formula_proof_latest.json").read_text(
            encoding="utf-8"
        )
    )
    success_room = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    definitions = {record.operation_id: record.definition for record in success_room.records}
    episode_display_names = {
        "2^n",
        "3^n",
        "bit_length(n)",
        "abs(a-b)",
        "n^2",
        "n mod 4",
        "floor(sqrt(n))",
        "min(a,b)",
    }
    primitive_records = [
        item
        for item in proof_report["formulas"]
        if item["display_formula"] in episode_display_names
        if item["source_operation_id"] in definitions
        and definitions[item["source_operation_id"]].get("substrate")
        == "anonymous_unified_word_machine_v0.1"
    ]
    library = {
        item["source_operation_id"]: ReflectiveProgram.from_dict(
            dict(definitions[item["source_operation_id"]])
        )
        for item in primitive_records
    }
    arities = {
        item["source_operation_id"]: int(item["domain"]["arity"])
        for item in primitive_records
    }
    component_proofs = {
        item["source_operation_id"]: item["universal_room_record_id"]
        for item in primitive_records
    }

    # These names are used only by the host to build the sealed oracle and the
    # posthoc report.  The reasoner receives only the anonymous mappings above.
    posthoc = {item["display_formula"]: item["source_operation_id"] for item in primitive_records}
    target = CompositionGraphProgram(
        (
            CompositionNode(posthoc["3^n"], ("input:0",)),
            CompositionNode(posthoc["2^n"], ("input:0",)),
            CompositionNode(posthoc["abs(a-b)"], ("node:0", "node:1")),
            CompositionNode(posthoc["bit_length(n)"], ("node:2",)),
            CompositionNode(posthoc["n^2"], ("node:3",)),
        )
    )
    target_executor = CompositionExecutor(library)

    def oracle(row: tuple[float, ...]) -> float:
        return float(target_executor.execute(target, row).output_value)

    reasoner = ProofCarryingReasoner(
        library,
        arities,
        component_proofs,
        maximum_depth=4,
        maximum_binary_depth=3,
        maximum_nodes=7,
        maximum_argument_states=5000,
        beam_per_depth=20000,
        hypotheses_per_behavior=5,
        top_k=20000,
    )
    seed_rows = ((0.0,), (1.0,), (2.0,))
    active = AutonomousExperimentLoop(
        reasoner,
        planner=DisagreementExperimentPlanner(maximum_candidates=100),
        maximum_rounds=9,
    ).run(
        opaque_task_id="anonymous-proof-carrying-reasoning",
        initial_rows=seed_rows,
        initial_outputs=tuple(oracle(row) for row in seed_rows),
        oracle=oracle,
        value_pool=tuple(range(21)),
    )

    final_candidate = active.final_candidate
    sealed_rows = tuple((float(value),) for value in range(21, 26))
    sealed_cases = tuple((row, oracle(row)) for row in sealed_rows)
    verifier = ReasoningTraceVerifier(library, component_proofs)
    verification = verifier.verify(final_candidate, sealed_cases)
    sealed_passed = sum(item["passed"] for item in verification["case_results"])

    final_observation = __import__(
        "akgm_n0.learner", fromlist=["NumericTableObservation"]
    ).NumericTableObservation.create(
        opaque_session_id="reasoning-final-observation",
        input_rows=active.input_rows,
        output_values=active.output_values,
        validity_mask=(True,) * len(active.input_rows),
        action_receipt="autonomous_reasoning_final_evidence",
    )
    final_search = reasoner.search(final_observation)

    # The old search is the honest fixed-depth baseline: it can express only a
    # two-node chain or two one-node branches followed by one binary merge.
    baseline_search = CompositionGraphSearch(library, arities, top_k=5000)
    baseline_report = baseline_search.search(final_observation)
    baseline_exact = next(
        (candidate for candidate in baseline_report.top_candidates if candidate.exact),
        baseline_report.top_candidates[0],
    )
    baseline_results = []
    for row, expected in sealed_cases:
        try:
            predicted = baseline_search.executor.execute(
                baseline_exact.program, row
            ).output_value
        except Exception:
            predicted = None
        baseline_results.append(
            {"inputs": list(row), "predicted": predicted, "observed": expected}
        )
    for item in baseline_results:
        item["passed"] = item["predicted"] == item["observed"]
    baseline_passed = sum(item["passed"] for item in baseline_results)

    mistake_library = AdaptiveMistakeLibrary(
        ROOT / "artifacts/mistakes/adaptive_mistakes.jsonl"
    )
    new_mistake_ids = []
    all_check_cases = tuple(zip(active.input_rows, active.output_values, strict=True)) + sealed_cases
    for candidate in final_search.top_candidates:
        if candidate.candidate_id == final_candidate.candidate_id:
            continue
        counterexamples = []
        for row, expected in all_check_cases:
            try:
                predicted = reasoner.executor.execute(candidate.program, row).output_value
            except Exception:
                predicted = None
            if predicted != expected:
                counterexamples.append(
                    {
                        "input": list(row),
                        "predicted": predicted,
                        "observed": expected,
                    }
                )
        if not counterexamples:
            continue
        record = mistake_library.record(
            candidate.program,
            failed_scope="proof_carrying_reasoning_sealed",
            condition_key="anonymous-multistep-v0.1",
            counterexamples=counterexamples,
            source_candidate_id=candidate.candidate_id,
        )
        if record.mistake_id not in new_mistake_ids:
            new_mistake_ids.append(record.mistake_id)
        if len(new_mistake_ids) == 10:
            break

    active_queries = [
        round_.proposed_experiment.to_dict()
        for round_ in active.rounds
        if round_.observed_output is not None and round_.proposed_experiment is not None
    ]
    gates = [
        {
            "gate_id": "variable_depth_path_created",
            "passed": len(final_candidate.program.nodes) >= 5
            and final_candidate.reasoning_depth >= 4,
            "actual": len(final_candidate.program.nodes),
            "threshold": 5,
        },
        {
            "gate_id": "all_steps_backed_by_universal_records",
            "passed": all(
                step.component_proof_record_id.startswith("UF-")
                for step in final_candidate.reasoning_steps
            ),
            "actual": len(final_candidate.reasoning_steps),
            "threshold": len(final_candidate.program.nodes),
        },
        {
            "gate_id": "self_selected_counterexamples_exist",
            "passed": len(active_queries) > 0,
            "actual": len(active_queries),
            "threshold": 1,
        },
        {
            "gate_id": "sealed_transfer_exact",
            "passed": sealed_passed == len(sealed_cases),
            "actual": sealed_passed,
            "threshold": len(sealed_cases),
        },
        {
            "gate_id": "outperforms_fixed_depth_baseline",
            "passed": sealed_passed > baseline_passed,
            "actual": f"{sealed_passed}>{baseline_passed}",
            "threshold": "strictly_better",
        },
        {
            "gate_id": "independent_trace_replay",
            "passed": verification["passed"],
            "actual": sum(item["passed"] for item in verification["obligations"]),
            "threshold": len(verification["obligations"]),
        },
        {
            "gate_id": "wrong_paths_enter_mistake_room",
            "passed": len(new_mistake_ids) == 10,
            "actual": len(new_mistake_ids),
            "threshold": 10,
        },
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "failed", "gates": gates}, indent=2))
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-reasoning-optimization-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "proof-carrying-reasoning-optimization-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "variable_depth_reasoning_verified",
        "reasoner": {
            "primitive_operation_count": len(library),
            "maximum_depth": reasoner.maximum_depth,
            "maximum_binary_depth": reasoner.maximum_binary_depth,
            "maximum_nodes": reasoner.maximum_nodes,
            "graph_template_supplied": False,
            "formula_names_supplied": False,
            "host_selected_episode_operation_pool": True,
            "behavioral_hypotheses_per_signature": reasoner.hypotheses_per_behavior,
        },
        "experiment": {
            "host_seed_count": len(seed_rows),
            "self_selected_query_count": len(active_queries),
            "total_observation_count": len(active.input_rows),
            "self_selected_queries": active_queries,
            "rounds": [round_.to_dict() for round_ in active.rounds],
        },
        "result": {
            "candidate": final_candidate.to_dict(),
            "reasoning_depth": final_candidate.reasoning_depth,
            "reasoning_step_count": len(final_candidate.reasoning_steps),
            "posthoc_interpretation": "bit_length(abs(3^n - 2^n))^2",
            "component_proof_records": [
                step.component_proof_record_id for step in final_candidate.reasoning_steps
            ],
            "layers": [layer.to_dict() for layer in final_search.layers],
        },
        "sealed_transfer": {
            "passed": sealed_passed,
            "total": len(sealed_cases),
            "cases": verification["case_results"],
        },
        "fixed_depth_baseline": {
            "maximum_graph_nodes": 3,
            "candidate": baseline_exact.to_dict(),
            "sealed_passed": baseline_passed,
            "sealed_total": len(sealed_cases),
            "cases": baseline_results,
        },
        "verification": verification,
        "mistake_feedback": {
            "new_mistake_ids": new_mistake_ids,
            "count": len(new_mistake_ids),
        },
        "gates": gates,
        "learner_received": {
            "anonymous_numeric_rows": True,
            "anonymous_verified_operation_ids": True,
            "component_proof_record_ids": True,
            "operation_or_formula_names": False,
            "target_graph": False,
            "target_intermediate_values": False,
        },
        "limitations": [
            "Reasoning is bounded by configured depth, node count, beam size, and unary/binary arity.",
            "The components were previously proven; this run created a new reasoning path rather than new primitive semantics.",
            "The host selected an eight-operation working-memory episode; full 30-operation reasoning still exceeds the current beam.",
            "Sealed transfer and proof-lineage replay do not replace a new symbolic theorem certificate for the posthoc formula.",
        ],
    }
    artifact = run_dir / "reasoning_optimization_report.json"
    artifact.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for destination in (
        ROOT / "reports/data/reasoning_optimization_latest.json",
        ROOT / "dashboard/data/reasoning_optimization_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "reasoning_depth": final_candidate.reasoning_depth,
                "reasoning_steps": len(final_candidate.reasoning_steps),
                "self_selected_queries": len(active_queries),
                "sealed": f"{sealed_passed}/{len(sealed_cases)}",
                "fixed_depth_baseline": f"{baseline_passed}/{len(sealed_cases)}",
                "mistakes_recorded": len(new_mistake_ids),
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
