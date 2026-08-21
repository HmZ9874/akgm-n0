"""Search, independently challenge, and ledger one candidate."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    HiddenSequenceEnvironment,
    IndependentVerifier,
    KnowledgeLedger,
    SequenceWorldSpec,
    VerificationCase,
)
from akgm_n0.learner import NextValueProgramSearch


SECRET = b"local-verification-smoke-only"


def make_observation(spec: SequenceWorldSpec, seed: int):
    return HiddenSequenceEnvironment(spec, seed=seed, secret=SECRET).observe(spec.length)


def main() -> int:
    source = make_observation(SequenceWorldSpec("affine", (7.0, 3.0), 12), 104729)
    search_report = NextValueProgramSearch(maximum_nodes=3, top_k=1).search(source)
    candidate = search_report.top_candidates[0]

    cases = [
        VerificationCase.create(
            scope="source_holdout",
            observation=make_observation(
                SequenceWorldSpec("affine", (7.0, 3.0), 12), 130363
            ),
            refit_prefix_length=6,
            required_for_validity=True,
        ),
        VerificationCase.create(
            scope="registered_ood",
            observation=make_observation(
                SequenceWorldSpec("affine", (1000.0, -17.0), 12), 155921
            ),
            refit_prefix_length=6,
            required_for_validity=True,
        ),
        VerificationCase.create(
            scope="adversarial_challenge",
            observation=make_observation(
                SequenceWorldSpec("polynomial2", (1.0, 0.0, 1.0), 12), 181081
            ),
            refit_prefix_length=6,
            required_for_validity=False,
        ),
    ]
    verification = IndependentVerifier().verify(candidate.program, cases)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-verifier-smoke-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    ledger = KnowledgeLedger(run_directory / "knowledge_ledger.jsonl")
    knowledge_id = ledger.propose(
        candidate.program,
        parent_ids=tuple(sorted({node["op"] for node in _walk_ast(candidate.program.to_dict())})),
        provenance={
            "run_id": run_id,
            "search_candidate_id": candidate.candidate_id,
            "verifier_version": verification.verifier_version,
        },
        evidence={"search": candidate.to_dict()},
    )
    ledger.transition(
        knowledge_id,
        "fit_passed",
        reason="search_train_and_validation_passed",
        evidence={"train_mse": candidate.train_mse, "validation_mse": candidate.validation_mse},
    )
    if verification.status == "rejected":
        ledger.transition(
            knowledge_id,
            "rejected",
            reason="required_verification_case_failed",
            evidence=verification.to_dict(),
        )
    else:
        ledger.transition(
            knowledge_id,
            "verified",
            reason="required_verification_cases_passed",
            evidence=verification.to_dict(),
        )
        if verification.status == "bounded":
            ledger.transition(
                knowledge_id,
                "bounded",
                reason="adversarial_counterexample_found",
                evidence=verification.to_dict(),
            )

    report_path = run_directory / "verification_report.json"
    payload = {
        "claim": "verification_and_ledger_smoke_test_only",
        "run_id": run_id,
        "knowledge_id": knowledge_id,
        "final_status": ledger.get(knowledge_id).status,
        "search_candidate": candidate.to_dict(),
        "verification": verification.to_dict(),
        "ledger_event_count": len(ledger.events),
    }
    with report_path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {**payload, "artifact_path": report_path.relative_to(PROJECT_ROOT).as_posix()},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _walk_ast(node: dict):
    yield node
    for child in node.get("args", []):
        yield from _walk_ast(child)


if __name__ == "__main__":
    raise SystemExit(main())
