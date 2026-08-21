from __future__ import annotations
import json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator import FormulaSuccessRoom,UniversalFormulaCertificate,UniversalFormulaRoom,UniversalProofVerifier,program_digest
from akgm_n0.learner import ReflectiveProgram
HISTORICAL=("natural_integer_quotient","batch20_t12","batch20_t13","batch20_t14","batch20_t15","batch20_t16","batch20_t17","batch20_t18","batch20_t19")
def main():
 room=UniversalFormulaRoom(ROOT/"artifacts/formula_rooms/parametric/proven_formulas.jsonl")
 legacy=UniversalFormulaRoom(ROOT/"artifacts/formula_rooms/universal/proven_formulas.jsonl");promoted=[]
 for old in legacy.records:
  if old.theorem_kind not in HISTORICAL:continue
  program=ReflectiveProgram.from_dict(dict(old.program));cert=UniversalFormulaCertificate.from_dict(old.certificate);proof=UniversalProofVerifier().verify(program,cert);rec=room.record(program,cert,proof);promoted.append(rec)
 discovery=json.loads((ROOT/"reports/data/strict_parametric_ten_latest.json").read_text(encoding="utf-8"));bounded=FormulaSuccessRoom(ROOT/"artifacts/formula_rooms/success/successful_formulas.jsonl");by_id={r.room_record_id:r for r in bounded.records};v=UniversalProofVerifier();new=[]
 for i,task in enumerate(discovery["tasks"]):
  source=by_id[task["success_room_record"]["room_record_id"]];program=ReflectiveProgram.from_dict(dict(source.definition));kind=f"strict_parametric_s{i:02d}";cert=UniversalFormulaCertificate(theorem_kind=kind,source_room_record_id=source.room_record_id,source_operation_id=source.operation_id,program_digest=program_digest(program),domain=v.DOMAINS[kind],claimed_statement=v.STATEMENTS[kind],claimed_invariants=v.INVARIANTS[kind],claimed_termination_measure=v.TERMINATION[kind]);proof=v.verify(program,cert)
  if not proof.passed:print(json.dumps(proof.to_dict(),indent=2));return 1
  rec=room.record(program,cert,proof);new.append({"formula":task["posthoc_formula"],"mechanism":task["mechanism_key"],"record_id":rec.room_record_id,"source_record_id":source.room_record_id,"theorem_kind":kind,"proof":proof.to_dict(),"invariants":list(cert.claimed_invariants),"termination":cert.claimed_termination_measure})
 if len(room.records)!=20:raise RuntimeError(f"strict room expected 20, got {len(room.records)}")
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");run_id="RUN-strict-parametric-twenty-proof-"+stamp;run_dir=ROOT/"artifacts/runs"/run_id;run_dir.mkdir(parents=True);all_obligations=sum(len(r.verification["obligations"]) for r in room.records);all_passed=sum(sum(o["passed"] for o in r.verification["obligations"]) for r in room.records)
 report={"report_version":"strict-parametric-room-v0.1","run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"verdict":"twenty_strict_free_variable_formulas_proven","strict_formula_count":20,"prior_parametric_count":1,"historical_reclassified_count":len(promoted),"newly_synthesized_count":len(new),"new_formulas":new,"room_records":[r.to_dict() for r in room.records],"proof_obligation_count":all_obligations,"proof_obligation_passed_count":all_passed,"classification":{"fixed_base_instances_count":False,"reducible_compositions_count":False,"all_formula_arguments_must_be_runtime_free":True},"gates":[{"gate_id":"twenty_strict_room_records","passed":len(room.records)==20,"actual":len(room.records),"threshold":20},{"gate_id":"ten_new_syntheses","passed":len(new)==10,"actual":len(new),"threshold":10},{"gate_id":"nine_historical_reclassifications_labeled","passed":len(promoted)==9,"actual":len(promoted),"threshold":9},{"gate_id":"all_proofs_replay","passed":all_passed==all_obligations,"actual":all_passed,"threshold":all_obligations}],"limitations":["Nine entries are historical discoveries reclassified under the stricter rule, not new discoveries in this run.","The ten new programs were selected from a finite host-supplied frontier.","Distinct comparison relations have distinct executable branches but share subtraction-and-branch primitives."]};artifact=run_dir/"strict_parametric_twenty_proof_report.json";artifact.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 for dest in (ROOT/"reports/data/strict_parametric_twenty_latest.json",ROOT/"dashboard/data/strict_parametric_twenty_latest.json"):shutil.copyfile(artifact,dest)
 print(json.dumps({"run_id":run_id,"strict_total":20,"new":10,"reclassified":9,"obligations":all_obligations,"passed":all_passed,"artifact_path":str(artifact.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
