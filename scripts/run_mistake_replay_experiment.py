"""Disprove, remember, and replay-block an equivalent numeric program family."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    HiddenSequenceEnvironment,
    IndependentVerifier,
    MistakeLibrary,
    SequenceWorldSpec,
    VerificationCase,
)
from akgm_n0.learner import NextValueProgramSearch, add, parameter, read_offset


SECRET = b"local-mistake-replay-v0.1"
CONDITION_KEY = "registered_curve_challenge_v0.1"


def make_observation(spec: SequenceWorldSpec, seed: int):
    return HiddenSequenceEnvironment(spec, seed=seed, secret=SECRET).observe(spec.length)


def main() -> int:
    source = make_observation(SequenceWorldSpec("affine", (7.0, 3.0), 12), 104729)
    initial_search = NextValueProgramSearch(maximum_nodes=3, top_k=1).search(source)
    first_candidate = initial_search.top_candidates[0]
    challenge = VerificationCase.create(
        scope="adversarial_challenge",
        observation=make_observation(
            SequenceWorldSpec("polynomial2", (1.0, 0.0, 1.0), 12), 181081
        ),
        refit_prefix_length=6,
        required_for_validity=False,
    )
    first_verification = IndependentVerifier().verify(first_candidate.program, [challenge])
    if not first_verification.counterexamples:
        raise RuntimeError("registered challenge did not disprove the initial candidate")

    library_path = PROJECT_ROOT / "artifacts" / "mistakes" / "mistake_library.jsonl"
    library = MistakeLibrary(library_path)
    stored = library.record(
        first_candidate.program,
        objective_id=NextValueProgramSearch.OBJECTIVE_ID,
        failed_scope=challenge.scope,
        condition_key=CONDITION_KEY,
        counterexamples=tuple(item.to_dict() for item in first_verification.counterexamples),
        source_candidate_id=first_candidate.candidate_id,
    )

    structurally_different_equivalent = add(parameter(0), read_offset(0))
    equivalent_hits = library.find_equivalent(
        structurally_different_equivalent,
        objective_id=NextValueProgramSearch.OBJECTIVE_ID,
        failed_scope=challenge.scope,
        condition_key=CONDITION_KEY,
    )
    replay_search = NextValueProgramSearch(
        maximum_nodes=3,
        top_k=5,
        candidate_gate=library.candidate_gate(
            objective_id=NextValueProgramSearch.OBJECTIVE_ID,
            failed_scope=challenge.scope,
            condition_key=CONDITION_KEY,
        ),
    ).search(source)
    old_family_returned = any(
        library.find_equivalent(
            item.program,
            objective_id=NextValueProgramSearch.OBJECTIVE_ID,
            failed_scope=challenge.scope,
            condition_key=CONDITION_KEY,
        )
        for item in replay_search.top_candidates
    )
    gates = [
        {
            "gate_id": "counterexample_required_before_storage",
            "passed": bool(first_verification.counterexamples),
            "actual": len(first_verification.counterexamples),
            "threshold": 1,
        },
        {
            "gate_id": "equivalent_structure_recalled",
            "passed": bool(equivalent_hits),
            "actual": len(equivalent_hits),
            "threshold": 1,
        },
        {
            "gate_id": "old_family_blocked_before_scoring",
            "passed": replay_search.programs_filtered > 0 and not old_family_returned,
            "actual": replay_search.programs_filtered,
            "threshold": 1,
        },
        {
            "gate_id": "cross_condition_behavior",
            "passed": None,
            "actual": None,
            "threshold": True,
        },
    ]
    passed = all(gate["passed"] for gate in gates if gate["passed"] is not None)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-mistake-replay-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    report = {
        "report_version": "mistake-replay-report-v0.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "错题库：等价错误回放拦截实验",
        "verdict": "conditionally_passed" if passed else "failed",
        "claim_scope": "same_objective_same_registered_failure_condition",
        "architecture": "append_only_equivalence_aware_replay_memory",
        "first_failure": {
            "candidate": first_candidate.to_dict(),
            "verification": first_verification.to_dict(),
        },
        "stored_mistake": stored.to_dict(),
        "equivalence_probe": {
            "probe_program_ast": structurally_different_equivalent.to_dict(),
            "structurally_identical": (
                structurally_different_equivalent.to_dict()
                == first_candidate.program.to_dict()
            ),
            "matched_mistake_ids": [item.mistake_id for item in equivalent_hits],
        },
        "replay_search": {
            "programs_generated": replay_search.programs_generated,
            "programs_filtered_before_scoring": replay_search.programs_filtered,
            "programs_scored": replay_search.programs_scored,
            "old_family_returned": old_family_returned,
            "top_candidate_ids": [
                item.candidate_id for item in replay_search.top_candidates
            ],
        },
        "library": {
            "record_count": len(library.records),
            "path": library_path.relative_to(PROJECT_ROOT).as_posix(),
            "append_only_hash_chain": True,
        },
        "gates": gates,
        "limitations": [
            "Replay blocking applies only when objective, failure scope, and registered condition all match.",
            "Equivalence is complete only for the current linear add/subtract program language.",
            "A newly generated, non-equivalent hypothesis can still be wrong and must be independently challenged.",
            "The library prevents repeated evaluation of known failures; it does not prove remaining candidates correct.",
        ],
    }
    artifact_path = run_directory / "mistake_replay_report.json"
    with artifact_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    latest_path = PROJECT_ROOT / "reports" / "data" / "mistake_replay_latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, latest_path)
    dashboard_path = PROJECT_ROOT / "dashboard" / "data" / "mistake_replay_latest.json"
    if dashboard_path.parent.parent.exists():
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact_path, dashboard_path)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "verdict": report["verdict"],
                "mistake_id": stored.mistake_id,
                "counterexample_count": len(first_verification.counterexamples),
                "equivalent_probe_matched": bool(equivalent_hits),
                "programs_filtered_before_scoring": replay_search.programs_filtered,
                "old_family_returned": old_family_returned,
                "artifact_path": artifact_path.relative_to(PROJECT_ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
