from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from akgm_n0.evaluator import (
    FormulaSuccessRoom,
    UniversalFormulaCertificate,
    UniversalFormulaRoom,
    UniversalProofVerifier,
    program_digest,
)
from akgm_n0.learner import ReflectiveProgram


def main() -> int:
    policy = json.loads((PROJECT_ROOT / "configs" / "discovery_stop_policy.json").read_text(encoding="utf-8"))
    discovery = json.loads((PROJECT_ROOT / "reports" / "data" / "twenty_formula_frontier_latest.json").read_text(encoding="utf-8"))
    if policy["minimum_new_successful_formulas_per_batch"] != 20 or len(discovery["tasks"]) != 20:
        raise RuntimeError("active twenty-formula stop policy is not satisfied")
    bounded_room = FormulaSuccessRoom(PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl")
    sources = {item.room_record_id: item for item in bounded_room.records}
    verifier = UniversalProofVerifier()
    pending = []
    for task in discovery["tasks"]:
        theorem_kind = "batch20_" + task["opaque_task"]
        source_id = task["success_room_record"]["room_record_id"]
        source = sources[source_id]
        program = ReflectiveProgram.from_dict(dict(source.definition))
        certificate = UniversalFormulaCertificate(
            theorem_kind=theorem_kind,
            source_room_record_id=source.room_record_id,
            source_operation_id=source.operation_id,
            program_digest=program_digest(program),
            domain=verifier.DOMAINS[theorem_kind],
            claimed_statement=verifier.STATEMENTS[theorem_kind],
            claimed_invariants=verifier.INVARIANTS[theorem_kind],
            claimed_termination_measure=verifier.TERMINATION[theorem_kind],
        )
        verification = verifier.verify(program, certificate)
        pending.append((task, source, program, certificate, verification))
    gates = [
        {"gate_id": "active_stop_policy_twenty", "passed": len(pending)==20, "actual": len(pending), "threshold": 20},
        {"gate_id": "twenty_distinct_program_bindings", "passed": len({item[3].program_digest for item in pending})==20, "actual": len({item[3].program_digest for item in pending}), "threshold": 20},
        {"gate_id": "twenty_distinct_theorem_rules", "passed": len({item[3].theorem_kind for item in pending})==20, "actual": len({item[3].theorem_kind for item in pending}), "threshold": 20},
        {"gate_id": "all_twenty_proofs_passed", "passed": all(item[4].passed for item in pending), "actual": sum(item[4].passed for item in pending), "threshold": 20},
        {"gate_id": "all_domains_explicit", "passed": all(dict(item[3].domain)==verifier.DOMAINS[item[3].theorem_kind] for item in pending), "actual": sum(dict(item[3].domain)==verifier.DOMAINS[item[3].theorem_kind] for item in pending), "threshold": 20},
        {"gate_id": "discovery_logic_and_behavior_gates_passed", "passed": all(gate["passed"] for gate in discovery["gates"]), "actual": sum(gate["passed"] for gate in discovery["gates"]), "threshold": len(discovery["gates"])},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "proof_gate_failed", "gates": gates}, ensure_ascii=False, indent=2)); return 1

    universal_room = UniversalFormulaRoom(PROJECT_ROOT / "artifacts" / "formula_rooms" / "universal" / "proven_formulas.jsonl")
    if len(universal_room.records) != 10:
        raise RuntimeError(f"expected ten prior proofs, found {len(universal_room.records)}")
    new_results = []
    for task, source, program, certificate, verification in pending:
        proven = universal_room.record(program, certificate, verification)
        new_results.append({
            "mechanism": task["mechanism"], "display_formula": task["posthoc_formula"],
            "source_bounded_record_id": source.room_record_id, "source_operation_id": source.operation_id,
            "universal_room_record_id": proven.room_record_id,
            "program_digest": certificate.program_digest, "instruction_count": program.instruction_count,
            "domain": dict(certificate.domain), "theorem_statement": verification.recomputed_statement,
            "invariants": list(certificate.claimed_invariants),
            "termination_measure": certificate.claimed_termination_measure,
            "verification": verification.to_dict(),
        })
    previous = json.loads((PROJECT_ROOT / "reports" / "data" / "universal_formula_proof_latest.json").read_text(encoding="utf-8"))
    all_results = previous["formulas"] + new_results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-twenty-universal-proof-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    obligation_count = sum(len(item["verification"]["obligations"]) for item in all_results)
    passed_count = sum(sum(obligation["passed"] for obligation in item["verification"]["obligations"]) for item in all_results)
    report = {
        "report_version": "universal-formula-proof-report-v0.3", "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "三十个程序的全定义域证明审查",
        "verdict": "twenty_new_and_thirty_total_proven_on_declared_abstract_domains",
        "declared_domain": "每条证书分别声明：自然数、自然数对、正除数域或整数域",
        "scope_warning": "通用性指抽象无限精度整数转移语义；当前浮点执行器仍有步数、精度和幅值资源边界。",
        "audit_before_run": {"bounded_active_formula_count": len(bounded_room.records),
                             "universally_compliant_count": 10,
                             "reason": "本轮开始前已有十条可重算证明。"},
        "proof_method": {
            "search_side": "anonymous numeric evidence plus twenty host-compiled structural hypotheses",
            "proof_side": "independent program digests, exact polynomial identities, state induction, ranking functions, and exhaustive integer order cases",
            "finite_sampling_used_as_proof": False, "external_symbolic_library": False,
            "proof_recomputed_on_room_admission": True,
            "semantic_model": "abstract unbounded integer transition semantics",
        },
        "formulas": all_results, "new_formula_count": 20, "total_proven_formula_count": len(all_results),
        "gates": gates, "universal_room_active_count": len(universal_room.records),
        "proof_obligation_count": obligation_count, "proof_obligation_passed_count": passed_count,
        "status_change": {"bounded_hypotheses_retained": len(bounded_room.records),
                          "newly_promoted_to_universal_room": 20,
                          "total_universal_room": len(universal_room.records),
                          "bounded_room_mutated_by_proof": False},
        "limitations": [
            "全域证明针对抽象无限精度整数语义；部署执行器的浮点精度、幅值和步数限制仍然存在。",
            "20 个结构假设由宿主编译后交给匿名行为选择器，因此本轮不是模型自主发明全部 20 种语法。",
            "数学名称和证明规则在匿名发现结束后才进入评价器。",
            "证明只覆盖各证书声明的域；带除数的三条公式明确排除 d=0。",
            "其余 18 个活动候选仍为 bounded，不能称为通用公式。",
        ],
    }
    artifact = run_directory / "twenty_universal_formula_proof_report.json"
    with artifact.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2); stream.write("\n")
    for destination in (PROJECT_ROOT / "reports" / "data" / "universal_formula_proof_latest.json",
                        PROJECT_ROOT / "dashboard" / "data" / "universal_formula_proof_latest.json",
                        PROJECT_ROOT / "reports" / "data" / "twenty_universal_proof_latest.json",
                        PROJECT_ROOT / "dashboard" / "data" / "twenty_universal_proof_latest.json"):
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact, destination)
    print(json.dumps({"run_id": run_id, "verdict": report["verdict"],
                      "new_proven_formula_count": 20, "total_proven_formula_count": len(all_results),
                      "proof_obligations": obligation_count, "proof_obligations_passed": passed_count,
                      "new_universal_room_records": [item["universal_room_record_id"] for item in new_results],
                      "artifact_path": str(artifact.relative_to(PROJECT_ROOT))}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
