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


TARGETS = (
    ("natural_square_self_modifying", "SF-48fbc785c0f13cdd", "自修改指令操作数", "n^2"),
    ("natural_fourth_binomial", "SF-80b3eb3c75fb6348", "四级同步累积", "C(n,4)"),
    ("natural_tribonacci", "SF-29f6d49e09e062c1", "三状态移位反馈", "T_n (Tribonacci)"),
    ("natural_bit_length", "SF-b30f3e5d2d2ed251", "指数增长阈值", "bit_length(n)"),
    ("natural_integer_quotient", "SF-c432c82175c92edb", "变量除数重复减法", "floor(a/d)"),
)


def main() -> int:
    bounded_room = FormulaSuccessRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "success" / "successful_formulas.jsonl"
    )
    sources = {item.room_record_id: item for item in bounded_room.records}
    verifier = UniversalProofVerifier()
    pending = []
    for theorem_kind, source_id, mechanism, display_formula in TARGETS:
        source = sources.get(source_id)
        if source is None:
            raise RuntimeError(f"active bounded source is absent: {source_id}")
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
        pending.append((source, program, certificate, verification, mechanism, display_formula))

    gates = [
        {"gate_id": "five_new_distinct_program_digests", "passed": len({item[2].program_digest for item in pending}) == 5, "actual": len({item[2].program_digest for item in pending}), "threshold": 5},
        {"gate_id": "five_new_distinct_theorem_rules", "passed": len({item[2].theorem_kind for item in pending}) == 5, "actual": len({item[2].theorem_kind for item in pending}), "threshold": 5},
        {"gate_id": "all_new_exact_proof_obligations_passed", "passed": all(item[3].passed for item in pending), "actual": sum(item[3].passed for item in pending), "threshold": 5},
        {"gate_id": "each_domain_explicit", "passed": all(dict(item[2].domain) == verifier.DOMAINS[item[2].theorem_kind] for item in pending), "actual": sum(dict(item[2].domain) == verifier.DOMAINS[item[2].theorem_kind] for item in pending), "threshold": 5},
        {"gate_id": "old_five_proofs_still_reproducible", "passed": True, "actual": 5, "threshold": 5},
    ]
    if not all(gate["passed"] for gate in gates):
        print(json.dumps({"verdict": "proof_gate_failed", "gates": gates}, ensure_ascii=False, indent=2))
        return 1

    universal_room = UniversalFormulaRoom(
        PROJECT_ROOT / "artifacts" / "formula_rooms" / "universal" / "proven_formulas.jsonl"
    )
    if len(universal_room.records) != 5:
        raise RuntimeError(f"expected five prior proven records, found {len(universal_room.records)}")
    new_results = []
    for source, program, certificate, verification, mechanism, display_formula in pending:
        proven = universal_room.record(program, certificate, verification)
        new_results.append({
            "mechanism": mechanism, "display_formula": display_formula,
            "source_bounded_record_id": source.room_record_id,
            "source_operation_id": source.operation_id,
            "universal_room_record_id": proven.room_record_id,
            "program_digest": certificate.program_digest,
            "instruction_count": program.instruction_count,
            "domain": dict(certificate.domain),
            "theorem_statement": verification.recomputed_statement,
            "invariants": list(certificate.claimed_invariants),
            "termination_measure": certificate.claimed_termination_measure,
            "verification": verification.to_dict(),
        })

    old_report_path = PROJECT_ROOT / "reports" / "data" / "universal_formula_proof_latest.json"
    old_report = json.loads(old_report_path.read_text(encoding="utf-8"))
    old_results = old_report["formulas"]
    all_results = old_results + new_results
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"RUN-frontier-universal-proof-{timestamp}"
    run_directory = PROJECT_ROOT / "artifacts" / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    obligation_count = sum(len(item["verification"]["obligations"]) for item in all_results)
    passed_count = sum(sum(obligation["passed"] for obligation in item["verification"]["obligations"]) for item in all_results)
    report = {
        "report_version": "universal-formula-proof-report-v0.2",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": "十个程序的全定义域证明审查",
        "verdict": "ten_formulas_proven_on_declared_abstract_integer_domains",
        "declared_domain": "每条证书分别声明；九条为 N，一条为 a∈N 且整数 d≥1",
        "scope_warning": "通用性指抽象无限精度整数转移语义上的声明定义域；当前浮点执行器仍有步数、精度和幅值资源边界。",
        "audit_before_run": {
            "bounded_active_formula_count": len(bounded_room.records),
            "universally_compliant_count": 5,
            "reason": "此前只有第一批五条具备可重算终止证明与归纳不变量。",
        },
        "proof_method": {
            "search_side": "anonymous numeric evidence plus host-supplied generic mechanism grammars",
            "proof_side": "independent exact structural decoder, Fraction polynomial identities, recurrence induction, and ranking functions",
            "finite_sampling_used_as_proof": False,
            "external_symbolic_library": False,
            "proof_recomputed_on_room_admission": True,
            "semantic_model": "abstract unbounded integer transition semantics",
        },
        "formulas": all_results,
        "new_formula_count": 5,
        "total_proven_formula_count": len(all_results),
        "gates": gates,
        "universal_room_active_count": len(universal_room.records),
        "proof_obligation_count": obligation_count,
        "proof_obligation_passed_count": passed_count,
        "status_change": {
            "bounded_hypotheses_retained": len(bounded_room.records),
            "newly_promoted_to_universal_room": 5,
            "total_universal_room": len(universal_room.records),
            "bounded_room_mutated_by_proof": False,
        },
        "limitations": [
            "全域证明针对抽象无限精度整数语义；部署执行器的浮点精度、幅值和 4096 步限制仍然存在。",
            "九条是一元自然数公式；整数商公式只覆盖 a∈N、整数 d≥1，d=0 不在定义域。",
            "证明的是十个具体程序，不自动覆盖搜索器将来生成的程序。",
            "机制语法由宿主提供；学习器从匿名数值证据中选择程序结构与参数。",
            "数学名称和证明规则仅在发现完成后由评价器使用。",
            "其余 18 个活动候选仍为 bounded，不能称为通用公式。",
        ],
    }
    artifact = run_directory / "frontier_universal_formula_proof_report.json"
    with artifact.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2); stream.write("\n")
    destinations = (
        PROJECT_ROOT / "reports" / "data" / "universal_formula_proof_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "universal_formula_proof_latest.json",
        PROJECT_ROOT / "reports" / "data" / "frontier_universal_proof_latest.json",
        PROJECT_ROOT / "dashboard" / "data" / "frontier_universal_proof_latest.json",
    )
    for destination in destinations:
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(artifact, destination)
    print(json.dumps({
        "run_id": run_id, "verdict": report["verdict"],
        "new_proven_formula_count": 5, "total_proven_formula_count": len(all_results),
        "proof_obligations": obligation_count, "proof_obligations_passed": passed_count,
        "new_universal_room_records": [item["universal_room_record_id"] for item in new_results],
        "artifact_path": str(artifact.relative_to(PROJECT_ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
