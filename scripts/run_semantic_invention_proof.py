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
from akgm_n0.learner import SemanticExtendedProgram  # noqa: E402


KIND = "natural_weighted_fourth_order_recurrence"


def main() -> int:
    discovery = json.loads(
        (ROOT / "reports/data/semantic_invention_discovery_latest.json").read_text(
            encoding="utf-8"
        )
    )
    bounded = FormulaSuccessRoom(
        ROOT / "artifacts/formula_rooms/success/successful_formulas.jsonl"
    )
    source_id = discovery["success_room_record"]["room_record_id"]
    source = next(item for item in bounded.records if item.room_record_id == source_id)
    program = SemanticExtendedProgram.from_dict(dict(source.definition))
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
    strict = UniversalFormulaRoom(
        ROOT / "artifacts/formula_rooms/parametric/proven_formulas.jsonl"
    )
    before = len(strict.records)
    record = strict.record(program, certificate, verification)
    after = len(strict.records)
    if after < 33:
        raise RuntimeError(f"expected at least 33 strict formulas, got {after}")
    total = sum(len(item.verification["obligations"]) for item in strict.records)
    passed = sum(
        sum(obligation["passed"] for obligation in item.verification["obligations"])
        for item in strict.records
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = "RUN-semantic-invention-proof-" + stamp
    run_dir = ROOT / "artifacts/runs" / run_id
    run_dir.mkdir(parents=True)
    report = {
        "report_version": "semantic-invention-universal-proof-v0.1",
        "run_id": run_id,
        "source_discovery_run_id": discovery["run_id"],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": "invented_semantic_equivalence_and_formula_universally_proven",
        "formula": discovery["posthoc_interpretation"]["formula"],
        "theorem_kind": KIND,
        "invented_semantic": discovery["invented_semantic"],
        "domain": verifier.DOMAINS[KIND],
        "invariants": list(certificate.claimed_invariants),
        "termination_measure": certificate.claimed_termination_measure,
        "proof": verification.to_dict(),
        "strict_room_record": record.to_dict(),
        "strict_formula_total_before": before,
        "strict_formula_total_after": after,
        "room_proof_obligation_count": total,
        "room_proof_obligation_passed_count": passed,
        "discovery_summary": {
            "compressed_instruction_count": discovery["compressed_instruction_count"],
            "equivalent_expanded_instruction_count": discovery["equivalent_expanded_instruction_count"],
            "crossed_old_instruction_limit": discovery["crossed_old_instruction_limit"],
            "cegis_round_count": len(discovery["cegis_rounds"]),
            "sealed_passed": sum(item["passed"] for item in discovery["sealed_results"]),
            "sealed_total": len(discovery["sealed_results"]),
            "mistakes_recorded": len(discovery["mistake_ids"]),
            "first_counterexample": discovery["first_counterexample"],
        },
        "autonomy_boundary": {
            "invented": "the system detected a repeated proven 11-instruction microprogram, allocated unused opcode 16 and learned its descriptor roles without a preassigned mathematical name",
            "verified": "the evaluator proved opcode 16 equivalent to natural-counter repeated addition before admitting the dependent formula",
            "host_supplied": "the detector, descriptor codec, extended interpreter and proof schema are host code; semantic execution is therefore constrained invention, not unrestricted self-modification",
        },
    }
    artifact = run_dir / "semantic_invention_proof_report.json"
    artifact.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for destination in (
        ROOT / "reports/data/semantic_invention_proof_latest.json",
        ROOT / "dashboard/data/semantic_invention_proof_latest.json",
    ):
        shutil.copyfile(artifact, destination)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "semantic_id": program.invented_semantic.semantic_id,
                "opcode": program.invented_semantic.opcode,
                "strict_formula_total": after,
                "new_record": record.room_record_id,
                "proof_obligations": len(verification.obligations),
                "proof_passed": sum(item.passed for item in verification.obligations),
                "room_obligations": total,
                "room_passed": passed,
                "artifact_path": str(artifact.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
