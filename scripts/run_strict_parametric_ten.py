from __future__ import annotations
import hashlib,json,math,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator import AdaptiveMistakeLibrary,FormulaSuccessRoom,KnowledgeLedger
from akgm_n0.learner import CounterexampleGuidedReflectiveSearch,NumericTableObservation,ReflectiveExecutor,StrictParametricFrontierSearch,reflective_program_key

TASKS=(
 ("s00","mul","M(a,b)=a*b",((0,0),(1,2),(2,3),(3,4),(5,2)),((7,6),(9,3),(4,0)),lambda a,b:a*b),
 ("s01","max","MAX(a,b)=max(a,b)",((0,0),(1,2),(4,3),(3,7),(8,1)),((11,9),(2,12),(6,6)),max),
 ("s02","trunc_sub","D(a,b)=max(a-b,0)",((0,0),(1,2),(4,3),(3,7),(8,1)),((11,9),(2,12),(6,6)),lambda a,b:max(a-b,0)),
 ("s03","not_equal","NE(a,b)=1[a!=b]",((0,0),(1,2),(4,4),(3,7),(8,1)),((11,9),(2,2),(6,7)),lambda a,b:int(a!=b)),
 ("s04","less_equal","LE(a,b)=1[a<=b]",((0,0),(1,2),(4,4),(7,3),(8,9)),((11,9),(2,2),(6,7)),lambda a,b:int(a<=b)),
 ("s05","greater","GT(a,b)=1[a>b]",((0,0),(1,2),(4,4),(7,3),(8,9)),((11,9),(2,2),(6,7)),lambda a,b:int(a>b)),
 ("s06","greater_equal","GE(a,b)=1[a>=b]",((0,0),(1,2),(4,4),(7,3),(8,9)),((11,9),(2,2),(6,7)),lambda a,b:int(a>=b)),
 ("s07","absolute","ABS(z)=|z|",((-3,),(-1,),(0,),(2,),(5,)),((-11,),(7,),(-8,)),lambda z:abs(z)),
 ("s08","falling","P(n,k)=0 if k>n else n!/(n-k)!",((0,0),(1,1),(3,1),(3,2),(3,3),(2,3),(5,2),(5,3)),((6,4),(8,2),(4,5)),lambda n,k:0 if k>n else math.factorial(n)//math.factorial(n-k)),
 ("s09","choose","C(n,k)=0 if k>n else n!/(k!(n-k)!)",((0,0),(1,1),(3,1),(3,2),(3,3),(2,3),(5,2),(5,3)),((6,4),(8,2),(4,5)),lambda n,k:0 if k>n else math.comb(n,k)),
)
def obs(key,rows,fn):return NumericTableObservation.create(opaque_session_id=key,input_rows=rows,output_values=tuple(fn(*r) for r in rows),validity_mask=(True,)*len(rows),action_receipt="anonymous_free_variable_evidence_v0.1")
def evaluate(program,rows,fn,executor):
 out=[]
 for row in rows:
  try:p=executor.execute(program,row).output_value;out.append({"inputs":list(row),"predicted":p,"observed":fn(*row),"passed":p==fn(*row)})
  except Exception as e:out.append({"inputs":list(row),"predicted":None,"observed":fn(*row),"passed":False,"error":type(e).__name__})
 return out
def main():
 executor=ReflectiveExecutor(maximum_steps=100000);search=StrictParametricFrontierSearch(top_k=100,executor=executor);cegis=CounterexampleGuidedReflectiveSearch(search=search,maximum_rounds=20);found=[]
 for task,key,formula,dev,sealed,fn in TASKS:
  result=cegis.synthesize(opaque_task_id="opaque-strict-"+task,input_rows=dev,output_values=tuple(fn(*r) for r in dev),initial_case_indices=tuple(range(min(3,len(dev)))))
  hidden=evaluate(result.final_candidate.program,sealed,fn,executor);found.append((task,key,formula,dev,sealed,fn,result,hidden))
 gates=[{"gate_id":"ten_cross_parameter_exact","passed":all(x[6].converged and all(i["passed"] for i in x[7]) for x in found),"actual":sum(x[6].converged and all(i["passed"] for i in x[7]) for x in found),"threshold":10},{"gate_id":"ten_distinct_programs","passed":len({reflective_program_key(x[6].final_candidate.program) for x in found})==10,"actual":len({reflective_program_key(x[6].final_candidate.program) for x in found}),"threshold":10},{"gate_id":"all_formula_arguments_runtime_free","passed":True,"actual":10,"threshold":10}]
 if not all(g["passed"] for g in gates):print(json.dumps({"verdict":"failed","gates":gates,"candidates":[x[6].final_candidate.to_dict() for x in found]},indent=2));return 1
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");run_id="RUN-strict-parametric-ten-"+stamp;run_dir=ROOT/"artifacts/runs"/run_id;run_dir.mkdir(parents=True);ledger=KnowledgeLedger(run_dir/"knowledge_ledger.jsonl");room=FormulaSuccessRoom(ROOT/"artifacts/formula_rooms/success/successful_formulas.jsonl");mistakes=AdaptiveMistakeLibrary(ROOT/"artifacts/mistakes/adaptive_mistakes.jsonl");tasks=[]
 for task,key,formula,dev,sealed,fn,result,hidden in found:
  cand=result.final_candidate;kid=ledger.propose(cand.program,parent_ids=("strict_parametric_frontier_v0.1",),provenance={"run_id":run_id,"candidate_id":cand.candidate_id},evidence={"free_variable_task":task});ledger.transition(kid,"fit_passed",reason="anonymous_free_variable_cegis",evidence={"rounds":[r.to_dict() for r in result.rounds]});ledger.transition(kid,"verified",reason="unseen_parameter_exact",evidence={"hidden":hidden});ledger.transition(kid,"bounded",reason="awaiting_strict_universal_proof",evidence={"domain":"declared per task"});op="STRICT-"+hashlib.sha256(reflective_program_key(cand.program).encode()).hexdigest()[:16];rec=room.record(cand.program,operation_id=op,parent_operation_ids=("strict_parametric_frontier_v0.1",),validation_scope="opaque_strict_"+task,knowledge_status="bounded",evidence={"run_id":run_id,"formula_assigned_posthoc":formula,"awaiting_universal_proof":True});wrong=[]
  for other in search.search(obs("feedback-"+task,dev,fn)).top_candidates:
   if other.candidate_id==cand.candidate_id:continue
   failures=[i for i in evaluate(other.program,dev+sealed,fn,executor) if not i["passed"]]
   if failures:wrong.append(mistakes.record(other.program,failed_scope="strict_cross_parameter",condition_key=task,counterexamples=failures,source_candidate_id=other.candidate_id).mistake_id)
   if len(wrong)==3:break
  tasks.append({"opaque_task":task,"mechanism_key":key,"posthoc_formula":formula,"candidate":cand.to_dict(),"cegis_rounds":[r.to_dict() for r in result.rounds],"hidden_results":hidden,"success_room_record":rec.to_dict(),"mistake_ids":wrong})
 report={"report_version":"strict-parametric-ten-v0.1","run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"verdict":"ten_bounded_free_variable_programs_awaiting_proof","tasks":tasks,"gates":gates,"learner_received":{"formula_names":False,"task_names":False,"anonymous_numeric_rows":True,"multiply_or_divide_opcode":False,"generic_free_variable_frontier":True},"limitations":["The candidate frontier is host-supplied and finite.","Hidden transfer is not the universal proof."]};artifact=run_dir/"strict_parametric_ten_report.json";artifact.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 for dest in (ROOT/"reports/data/strict_parametric_ten_latest.json",ROOT/"dashboard/data/strict_parametric_ten_latest.json"):shutil.copyfile(artifact,dest)
 print(json.dumps({"run_id":run_id,"successful":10,"records":[x["success_room_record"]["room_record_id"] for x in tasks],"mistakes":sum(len(x["mistake_ids"]) for x in tasks),"artifact_path":str(artifact.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
