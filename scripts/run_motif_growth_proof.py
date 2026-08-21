from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from akgm_n0.evaluator import (  # noqa: E402
    FormulaSuccessRoom,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
    program_digest,
)
from akgm_n0.learner import ReflectiveProgram  # noqa: E402


KIND = "natural_weighted_second_order_recurrence"


def main() -> int:
    discovery = json.loads(
        (ROOT / "reports/data/motif_growth_discovery_latest.json").read_text(
            encoding="utf-8"
        )
    )
    bounded_room = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    source_id = discovery["success_room_record"]["room_record_id"]
    source = next(item for item in bounded_room.records if item.room_record_id == source_id)
    program = ReflectiveProgram.from_dict(dict(source.definition))
    verifier = UniversalProofVerifier()
    certificate = UniversalFormulaCertificate(
        theorem_kind=KIND,
        source_room_record_id=source.room_record_id,
        source_operation_id=source.operation_id,
        program_digest=program_digest(program),
        domain=verifier.DOMAINS[KIND],
        claimed_statement=verifier.STATEMENTS[KIND],
        claimed_invariants=verifier.INVARIANTS[KIND],
        claimed_termination_measure=verifier.TERMINATION[KIND],
    )
    verification = verifier.verify(program, certificate)
    if not verification.passed:
        print(json.dumps(verification.to_dict(), ensure_ascii=False, indent=2))
        return 1
    strict_room = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    before = len(strict_room.records)
    strict_record = strict_room.record(program, certificate, verification)
    after = len(strict_room.records)
    if after != 31:
        raise RuntimeError(f"expected 31 strict formulas after proof, got {after}")

    total_obligations = sum(
        len(record.verification["obligations"]) for record in strict_room.records
    )
    passed_obligations = sum(
        sum(item["passed"] for item in record.verification["obligations"])
        for record in strict_room.records
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-motif-growth-proof-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "motif-growth-universal-proof-v0.1",
        "run_id": run_id,
        "source_discovery_run_id": discovery["run_id"],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "universally_proven_and_admitted",
        "formula": discovery["posthoc_interpretation"]["formula"],
        "theorem_kind": KIND,
        "domain": verifier.DOMAINS[KIND],
        "invariants": list(certificate.claimed_invariants),
        "termination_measure": certificate.claimed_termination_measure,
        "proof": verification.to_dict(),
        "strict_room_record": strict_record.to_dict(),
        "strict_formula_total_before": before,
        "strict_formula_total_after": after,
        "room_proof_obligation_count": total_obligations,
        "room_proof_obligation_passed_count": passed_obligations,
        "discovery_summary": {
            "learned_motif_count": len(discovery["learned_motifs"]),
            "cegis_round_count": len(discovery["cegis_rounds"]),
            "sealed_passed": sum(item["passed"] for item in discovery["sealed_results"]),
            "sealed_total": len(discovery["sealed_results"]),
            "mistakes_recorded": len(discovery["mistake_ids"]),
            "first_counterexample": discovery["first_counterexample"],
        },
        "autonomy_boundary": {
            "learned": "loop, nested accumulation, memory and state-transition motifs were extracted from proven word code without formula labels",
            "grown": "input routing, coefficient routing, state sources and output state were selected from anonymous evidence",
            "host_supplied": "motif detectors, mutation slots, VM instructions and the independent theorem proof rule remain implemented by the host",
        },
    }
    artifact = run_dir / "motif_growth_proof_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/motif_growth_proof_latest.json",
        ROOT / "dashboard/data/motif_growth_proof_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "strict_formula_total": after,
                "new_record": strict_record.room_record_id,
                "proof_obligations": len(verification.obligations),
                "proof_passed": sum(item.passed for item in verification.obligations),
                "room_obligations": total_obligations,
                "room_passed": passed_obligations,
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
