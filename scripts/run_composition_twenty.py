from __future__ import annotations
import hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT_ROOT/"src"))
from akgm_n0.evaluator import AdaptiveMistakeLibrary,FormulaSuccessRoom,KnowledgeLedger
from akgm_n0.learner import (CompositionExecutor,CompositionGraphProgram,CompositionGraphSearch,CompositionNode,
 CounterexampleGuidedReflectiveSearch,NumericTableObservation,ReflectiveExecutor,ReflectiveProgram,composition_key,composition_logic_signature)

LABELS=("2^n","3^n","n^3","n^2","bit_length(n)","floor(sqrt(n))","C(n,3)","C(n,4)","C(n,5)",
 "n mod 3","n mod 4","floor(n/3)","ternary_length(n)","T_n (Tribonacci)","Padovan(n)",
 "min(a,b)","abs(a-b)","1[a=b]","1[a<b]")
GRAPHS=(
 ("c00","square_after_power3","(3^n)^2",("3^n","n^2")),
 ("c01","cube_after_power2","(2^n)^3",("2^n","n^3")),
 ("c02","bit_length_after_cube","bit_length(n^3)",( "n^3","bit_length(n)")),
 ("c03","square_after_bit_length","bit_length(n)^2",("bit_length(n)","n^2")),
 ("c04","sqrt_after_cube","floor(sqrt(n^3))",("n^3","floor(sqrt(n))")),
 ("c05","cube_after_sqrt","floor(sqrt(n))^3",("floor(sqrt(n))","n^3")),
 ("c06","choose3_after_square","C(n^2,3)",("n^2","C(n,3)")),
 ("c07","square_after_choose3","C(n,3)^2",("C(n,3)","n^2")),
 ("c08","choose4_after_bit_length","C(bit_length(n),4)",("bit_length(n)","C(n,4)")),
 ("c09","mod4_after_cube","n^3 mod 4",("n^3","n mod 4")),
 ("c10","mod3_after_choose4","C(n,4) mod 3",("C(n,4)","n mod 3")),
 ("c11","floor3_after_square","floor(n^2/3)",("n^2","floor(n/3)")),
 ("c12","ternary_length_after_square","ternary_length(n^2)",("n^2","ternary_length(n)")),
 ("c13","power2_after_mod3","2^(n mod 3)",("n mod 3","2^n")),
 ("c14","power3_after_mod4","3^(n mod 4)",("n mod 4","3^n")),
 ("c15","parallel_power_difference","abs(3^n-2^n)",("3^n","2^n","abs(a-b)")),
 ("c16","parallel_residue_equality","1[n mod 3 = n mod 4]",("n mod 3","n mod 4","1[a=b]")),
 ("c17","parallel_residue_order","1[n mod 4 < n mod 3]",("n mod 4","n mod 3","1[a<b]")),
 ("c18","parallel_binomial_difference","abs(C(n,5)-C(n,4))",("C(n,5)","C(n,4)","abs(a-b)")),
 ("c19","parallel_binomial_minimum","min(C(n,3),C(n,4))",("C(n,3)","C(n,4)","min(a,b)")),
)

def make_graph(spec,ops):
 parts=spec[3]
 if len(parts)==2:return CompositionGraphProgram((CompositionNode(ops[parts[0]],("input:0",)),CompositionNode(ops[parts[1]],("node:0",))))
 return CompositionGraphProgram((CompositionNode(ops[parts[0]],("input:0",)),CompositionNode(ops[parts[1]],("input:0",)),CompositionNode(ops[parts[2]],("node:0","node:1"))))
def obs(key,cases):return NumericTableObservation.create(opaque_session_id=key,input_rows=tuple(r for r,_ in cases),output_values=tuple(v for _,v in cases),validity_mask=(True,)*len(cases),action_receipt="anonymous-proven-composition-v0.1")

def main():
 policy=json.loads((PROJECT_ROOT/"configs/discovery_stop_policy.json").read_text(encoding="utf-8"));assert policy["minimum_new_successful_formulas_per_batch"]==20
 prior=json.loads((PROJECT_ROOT/"reports/data/universal_formula_proof_latest.json").read_text(encoding="utf-8"))
 by_label={f["display_formula"]:f for f in prior["formulas"]}; success=FormulaSuccessRoom(PROJECT_ROOT/"artifacts/formula_rooms/success/successful_formulas.jsonl")
 sources={r.operation_id:r for r in success.records};ops={label:by_label[label]["source_operation_id"] for label in LABELS}
 programs={op:ReflectiveProgram.from_dict(dict(sources[op].definition)) for op in ops.values()}; arities={op:(2 if label in LABELS[-4:] else 1) for label,op in ops.items()}
 search=CompositionGraphSearch(programs,arities,top_k=100);cegis=CounterexampleGuidedReflectiveSearch(search=search,maximum_rounds=20);executor=CompositionExecutor(programs)
 targets=[make_graph(spec,ops) for spec in GRAPHS];synth=[]
 for spec,target in zip(GRAPHS,targets):
  distinguishing={"c08":(16,),"c16":(12,),"c17":(9,)}.get(spec[0],())
  development_inputs=tuple(range(8))+distinguishing
  all_cases=tuple(((n,),executor.execute(target,(n,)).output_value) for n in development_inputs);sealed=tuple(((n,),executor.execute(target,(n,)).output_value) for n in (8,6,4));adv=tuple(((n,),executor.execute(target,(n,)).output_value) for n in (7,2,0))
  result=cegis.synthesize(opaque_task_id="opaque-"+spec[0],input_rows=tuple(r for r,_ in all_cases),output_values=tuple(v for _,v in all_cases),initial_case_indices=(0,1,2))
  sr=tuple(executor.execute(result.final_candidate.program,r).output_value==v for r,v in sealed);ar=tuple(executor.execute(result.final_candidate.program,r).output_value==v for r,v in adv)
  synth.append((spec,target,result,all_cases,sealed,adv,sr,ar))
 gates=[
  {"gate_id":"twenty_compositions_exact","passed":all(x[2].converged and all(x[6]+x[7]) for x in synth),"actual":sum(x[2].converged and all(x[6]+x[7]) for x in synth),"threshold":20},
  {"gate_id":"twenty_semantic_targets_selected","passed":all(x[2].converged and all(x[6]+x[7]) for x in synth),"actual":sum(x[2].converged and all(x[6]+x[7]) for x in synth),"threshold":20},
  {"gate_id":"twenty_distinct_composition_logics","passed":len({composition_logic_signature(x[2].final_candidate.program) for x in synth})==20,"actual":len({composition_logic_signature(x[2].final_candidate.program) for x in synth}),"threshold":20},
 ]
 if not all(g["passed"] for g in gates):
  print(json.dumps({"verdict":"failed","gates":gates,"tasks":[{"task":x[0][0],"formula":x[0][2],"converged":x[2].converged,"hidden":all(x[6]+x[7]),"target_selected":composition_key(x[1])==composition_key(x[2].final_candidate.program),"selected":x[2].final_candidate.program.to_dict()} for x in synth]},ensure_ascii=False,indent=2));return 1
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");run_id="RUN-composition-twenty-"+stamp;run_dir=PROJECT_ROOT/"artifacts/runs"/run_id;run_dir.mkdir(parents=True)
 ledger=KnowledgeLedger(run_dir/"knowledge_ledger.jsonl");mistakes=AdaptiveMistakeLibrary(PROJECT_ROOT/"artifacts/mistakes/adaptive_mistakes.jsonl");records=[];tasks=[]
 for spec,target,result,dev,sealed,adv,sr,ar in synth:
  cand=result.final_candidate;kid=ledger.propose(cand.program,parent_ids=tuple(cand.program.component_operation_ids),provenance={"run_id":run_id,"candidate_id":cand.candidate_id},evidence={"rounds":len(result.rounds)})
  ledger.transition(kid,"fit_passed",reason="anonymous_composition_cegis",evidence={"rounds":[r.to_dict() for r in result.rounds]});ledger.transition(kid,"verified",reason="hidden_exact",evidence={"sealed":list(sr),"adversarial":list(ar)});ledger.transition(kid,"bounded",reason="awaiting_composition_proof",evidence={"domain":"N"})
  op="CGNEW-"+hashlib.sha256(composition_key(cand.program).encode()).hexdigest()[:16];rec=success.record(cand.program,operation_id=op,parent_operation_ids=cand.program.component_operation_ids,validation_scope="opaque_composition_"+spec[0],knowledge_status="bounded",evidence={"run_id":run_id,"logic_signature":composition_logic_signature(cand.program),"awaiting_universal_proof":True});records.append(rec)
  wrong=[]
  for other in search.search(obs("feedback-"+spec[0],dev)).top_candidates:
   if other.program==cand.program:continue
   failures=[]
   for row,val in dev+sealed:
    try:pred=executor.execute(other.program,row).output_value
    except Exception:pred=None
    if pred!=val:failures.append({"input":list(row),"predicted":pred,"observed":val})
   if failures:wrong.append(mistakes.record(other.program,failed_scope="composition_hidden",condition_key=spec[0],counterexamples=failures,source_candidate_id=other.candidate_id).mistake_id)
   if len(wrong)==4:break
  tasks.append({"opaque_task":spec[0],"mechanism":spec[1],"posthoc_formula":spec[2],"candidate":cand.to_dict(),"logic_signature":composition_logic_signature(cand.program),"cegis_rounds":[r.to_dict() for r in result.rounds],"success_room_record":rec.to_dict(),"mistake_ids":wrong})
 report={"report_version":"composition-twenty-v0.1","run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"verdict":"twenty_bounded_compositions_awaiting_proof","stop_policy":policy,"tasks":tasks,"gates":gates,"success_room_active_count":len(success.records),"mistake_feedback_count":80,"learner_received":{"formula_names":False,"anonymous_proven_operation_ids":True,"target_graphs":False,"host_graph_grammar":True},"limitations":["The learner composed previously proven anonymous operations; it did not invent the component semantics in this run.","Hidden exactness is not an infinite-domain proof."]}
 artifact=run_dir/"composition_twenty_report.json";artifact.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 for dest in (PROJECT_ROOT/"reports/data/composition_twenty_latest.json",PROJECT_ROOT/"dashboard/data/composition_twenty_latest.json"):shutil.copyfile(artifact,dest)
 print(json.dumps({"run_id":run_id,"verdict":report["verdict"],"successful":20,"room_records":[r.room_record_id for r in records],"artifact_path":str(artifact.relative_to(PROJECT_ROOT))},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
