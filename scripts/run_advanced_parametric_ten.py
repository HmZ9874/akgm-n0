from __future__ import annotations
import hashlib,json,math,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from akgm_n0.evaluator import AdaptiveMistakeLibrary,FormulaSuccessRoom,KnowledgeLedger
from akgm_n0.learner import AdvancedParametricFrontierSearch,CounterexampleGuidedReflectiveSearch,NumericTableObservation,ReflectiveExecutor,reflective_program_key
def fib(a,b,n):
 for _ in range(n):a,b=b,a+b
 return a
def digit(x,b):
 c=0
 while x:c+=1;x//=b
 return c
def flog(x,b):return digit(x,b)-1
def asum(a,d,n):return sum(a+i*d for i in range(n))
def rising(a,k):return math.prod(a+i for i in range(k))
def geo(a,n):return sum(a**i for i in range(n+1))
def second(a,d,e,n):return a+n*d+(n*(n-1)//2)*e
TASKS=(
 ("a00","affine","A(a,d,n)=a+n*d",((1,2,0),(1,2,1),(2,3,4),(5,1,3),(0,4,2)),((7,5,4),(9,0,6),(3,8,2)),lambda a,d,n:a+n*d),
 ("a01","arithmetic_sum","S(a,d,n)=sum(i=0..n-1,a+i*d)",((1,2,0),(1,2,1),(1,2,3),(2,3,4),(5,1,3)),((7,5,4),(9,0,6),(3,8,2)),asum),
 ("a02","rising","R(a,k)=product(i=0..k-1,a+i)",((0,0),(1,1),(2,2),(3,3),(4,2)),((5,4),(2,5),(7,3)),rising),
 ("a03","generalized_fibonacci","F(a,b,n): F0=a,F1=b,F(t+2)=F(t)+F(t+1)",((0,1,0),(0,1,1),(0,1,5),(2,3,4),(4,1,3)),((5,7,6),(3,9,5),(8,2,4)),fib),
 ("a04","digit_length","L(x,b)=digits of x in base b",((0,2),(1,2),(2,2),(8,2),(9,3),(100,10)),((63,4),(80,3),(999,10)),digit),
 ("a05","floor_log","LOG(x,b)=floor(log_b(x))",((1,2),(2,2),(8,2),(9,3),(100,10)),((63,4),(80,3),(999,10)),flog),
 ("a06","lcm","LCM(a,b)=least common multiple",((0,0),(0,4),(1,5),(2,3),(6,8),(9,6)),((7,5),(12,18),(8,20)),math.lcm),
 ("a07","mod_power","MP(a,n,m)=a^n mod m",((2,0,3),(2,1,3),(2,3,5),(3,4,5),(7,2,4),(5,3,1)),((8,5,7),(11,4,9),(4,6,5)),pow),
 ("a08","geometric_sum","G(a,n)=sum(i=0..n,a^i)",((0,0),(1,0),(2,1),(2,3),(3,2)),((4,3),(5,2),(2,6)),geo),
 ("a09","second_difference","Q(a,d,e,n)=a+n*d+C(n,2)*e",((1,2,3,0),(1,2,3,1),(1,2,3,3),(2,1,4,4),(5,0,2,3)),((7,5,3,4),(9,0,1,6),(3,8,2,2)),second),
)
def obs(k,rows,fn):return NumericTableObservation.create(opaque_session_id=k,input_rows=rows,output_values=tuple(fn(*r) for r in rows),validity_mask=(True,)*len(rows),action_receipt="anonymous_advanced_free_variable_evidence_v0.1")
def evaluate(p,rows,fn,e):
 out=[]
 for r in rows:
  try:v=e.execute(p,r).output_value;out.append({"inputs":list(r),"predicted":v,"observed":fn(*r),"passed":v==fn(*r)})
  except Exception as x:out.append({"inputs":list(r),"predicted":None,"observed":fn(*r),"passed":False,"error":type(x).__name__})
 return out
def main():
 e=ReflectiveExecutor(maximum_steps=200000);search=AdvancedParametricFrontierSearch(executor=e);cegis=CounterexampleGuidedReflectiveSearch(search=search,maximum_rounds=20);found=[]
 for task,key,formula,dev,sealed,fn in TASKS:
  result=cegis.synthesize(opaque_task_id="opaque-advanced-"+task,input_rows=dev,output_values=tuple(fn(*r) for r in dev),initial_case_indices=tuple(range(min(3,len(dev)))));hidden=evaluate(result.final_candidate.program,sealed,fn,e);found.append((task,key,formula,dev,sealed,fn,result,hidden))
 gates=[{"gate_id":"ten_advanced_exact","passed":all(x[6].converged and all(i["passed"] for i in x[7]) for x in found),"actual":sum(x[6].converged and all(i["passed"] for i in x[7]) for x in found),"threshold":10},{"gate_id":"ten_distinct_programs","passed":len({reflective_program_key(x[6].final_candidate.program) for x in found})==10,"actual":len({reflective_program_key(x[6].final_candidate.program) for x in found}),"threshold":10}]
 if not all(g["passed"] for g in gates):print(json.dumps({"verdict":"failed","gates":gates,"candidates":[x[6].final_candidate.to_dict() for x in found]},indent=2));return 1
 stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ");run_id="RUN-advanced-parametric-ten-"+stamp;rd=ROOT/"artifacts/runs"/run_id;rd.mkdir(parents=True);ledger=KnowledgeLedger(rd/"knowledge_ledger.jsonl");room=FormulaSuccessRoom(ROOT/"artifacts/formula_rooms/success/successful_formulas.jsonl");mistakes=AdaptiveMistakeLibrary(ROOT/"artifacts/mistakes/adaptive_mistakes.jsonl");tasks=[]
 for task,key,formula,dev,sealed,fn,result,hidden in found:
  c=result.final_candidate;kid=ledger.propose(c.program,parent_ids=("advanced_parametric_frontier_v0.1",),provenance={"run_id":run_id,"candidate_id":c.candidate_id},evidence={"task":task});ledger.transition(kid,"fit_passed",reason="anonymous_advanced_cegis",evidence={"rounds":[r.to_dict() for r in result.rounds]});ledger.transition(kid,"verified",reason="unseen_parameters_exact",evidence={"hidden":hidden});ledger.transition(kid,"bounded",reason="awaiting_advanced_universal_proof",evidence={"runtime_parameters":len(dev[0])});op="ADV-"+hashlib.sha256(reflective_program_key(c.program).encode()).hexdigest()[:16];rec=room.record(c.program,operation_id=op,parent_operation_ids=("advanced_parametric_frontier_v0.1",),validation_scope="opaque_advanced_"+task,knowledge_status="bounded",evidence={"run_id":run_id,"posthoc_formula":formula,"awaiting_universal_proof":True});wrong=[]
  for other in search.search(obs("feedback-"+task,dev,fn)).top_candidates:
   if other.candidate_id==c.candidate_id:continue
   failures=[i for i in evaluate(other.program,dev+sealed,fn,e) if not i["passed"]]
   if failures:wrong.append(mistakes.record(other.program,failed_scope="advanced_cross_parameter",condition_key=task,counterexamples=failures,source_candidate_id=other.candidate_id).mistake_id)
   if len(wrong)==3:break
  tasks.append({"opaque_task":task,"mechanism_key":key,"posthoc_formula":formula,"candidate":c.to_dict(),"cegis_rounds":[r.to_dict() for r in result.rounds],"hidden_results":hidden,"success_room_record":rec.to_dict(),"mistake_ids":wrong})
 report={"report_version":"advanced-parametric-ten-v0.1","run_id":run_id,"created_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"verdict":"ten_advanced_bounded_programs_awaiting_proof","tasks":tasks,"gates":gates,"learner_received":{"formula_names":False,"anonymous_numeric_rows":True,"multiply_divide_power_opcodes":False,"finite_advanced_frontier":True},"limitations":["The advanced candidate frontier remains host-supplied.","Hidden tests are not universal proofs."]};art=rd/"advanced_parametric_ten_report.json";art.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 for d in (ROOT/"reports/data/advanced_parametric_ten_latest.json",ROOT/"dashboard/data/advanced_parametric_ten_latest.json"):shutil.copyfile(art,d)
 print(json.dumps({"run_id":run_id,"successful":10,"mistakes":sum(len(t["mistake_ids"]) for t in tasks),"records":[t["success_room_record"]["room_record_id"] for t in tasks],"artifact_path":str(art.relative_to(ROOT))},ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
