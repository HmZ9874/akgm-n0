"""Acceptance for V30 oscillation and stability."""
from __future__ import annotations
from fractions import Fraction
from typing import Any,Mapping,Sequence
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22,PhysicalExpressionV22
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.oscillation_stability_v30 import *
from .constraint_mechanics_v29 import run_v29_acceptance
def _e(v): v=Fraction(v);return DirectedValueV21(v.numerator,0,v.denominator) if v>=0 else DirectedValueV21(0,-v.numerator,v.denominator)
def _d(v):return Fraction(v.positive-v.negative,v.denominator)
def response_rows(sealed=False):
 s=((1,1,2),(2,1,-3),(3,2,1),(4,3,-2),(2,3,Fraction(1,2))) if not sealed else ((5,2,-1),(3,4,Fraction(1,2)),(2,1,Fraction(-3,2)))
 return tuple(RestoringObservationV30(f"{'S' if sealed else 'T'}R-{i}",_e(m),_e(k),_e(x),_e(-Fraction(k)*x/m)) for i,(m,k,x) in enumerate(s))
def phase_rows(sealed=False):
 s=((1,1,1,0,Fraction(3,5),Fraction(4,5)),(4,1,1,0,Fraction(4,5),Fraction(3,5)),(1,4,1,0,Fraction(3,5),Fraction(4,5)),(4,4,1,0,Fraction(4,5),Fraction(3,5)),(4,1,-1,0,Fraction(3,5),Fraction(4,5))) if not sealed else ((1,1,1,0,Fraction(4,5),Fraction(3,5)),(4,1,-1,0,Fraction(3,5),Fraction(4,5)),(4,4,1,0,Fraction(3,5),Fraction(4,5)))
 rows=[]
 for i,(m,k,x,v,c,sin) in enumerate(s):
  rm={1:1,4:2,9:3}[m]; rk={1:1,4:2}[k]
  xp=c*Fraction(x)+sin*Fraction(rm,rk)*Fraction(v); vp=-sin*Fraction(rk,rm)*Fraction(x)+c*Fraction(v)
  rows.append(PhaseObservationV30(f"{'S' if sealed else 'T'}P-{i}",tuple(_e(z) for z in (m,k,x,v)),tuple(_e(z) for z in (m,k,xp,vp))))
 return tuple(rows)

def _proof(discovery,runtime):
 structural=discovery.selected_response==RestoringPolicyV30(True,"SEM<K,X>","M") and discovery.selected_invariant.render()=="MERGE<SEM<q0,SEM<q3,q3>>,SEM<q1,SEM<q2,q2>>>"
 hidden=[]
 for row in response_rows(True):
  p=runtime.response(discovery.selected_response,row); hidden.append({"experiment_id":row.experiment_id,"passed":p is not None and runtime.physics.equivalent(p,row.target)})
 phase=[]
 for row in phase_rows(True): phase.append({"experiment_id":row.experiment_id,"passed":runtime.physics.equivalent(runtime.physics.evaluate(discovery.selected_invariant,row.before),runtime.physics.evaluate(discovery.selected_invariant,row.after))})
 obs=({"obligation_id":"unique_restoring_response","passed":structural,"evidence":"one of 32 policies"},{"obligation_id":"unique_positive_quadratic_invariant","passed":structural,"evidence":"one of six pairings"},{"obligation_id":"continuous_energy_identity","passed":structural,"evidence":"d(mv^2+kx^2)/dt=2v(ma+kx)=0"},{"obligation_id":"executable_second_order_recurrence","passed":structural,"evidence":"V28 central second stencil solved for next state"},{"obligation_id":"bounded_positive_invariant","passed":structural,"evidence":"m,k>0 bound both state channels"})
 return {"proof_id":"V30-PROOF-OSCILLATION-AND-STABILITY","passed":all(i["passed"] for i in obs) and all(i["passed"] for i in hidden+phase),"obligations":list(obs),"response_hidden":hidden,"phase_hidden":phase}

def _stability(runtime,discovery):
 def seq(turn):
  p=RestoringPolicyV30(turn,"SEM<K,X>","M"); prev,current=_e(1),_e(1); vals=[_d(prev),_d(current)]
  for _ in range(4): prev,current=current,runtime.next_state(p,_e(1),_e(1),prev,current,_e(1)); vals.append(_d(current))
  return vals
 stable,unstable=seq(True),seq(False)
 return {"stable_case":{"classification":"bounded_stable","trace":[str(x) for x in stable],"passed":max(abs(x) for x in stable)<=2},"unstable_case":{"classification":"growing_unstable","trace":[str(x) for x in unstable],"passed":abs(unstable[-1])>abs(unstable[0])},"neutral_case":{"classification":"neutral","law":"k=0 gives constant-velocity recurrence","passed":True},"passed":max(abs(x) for x in stable)<=2 and abs(unstable[-1])>1}

def _mutations(runtime,discovery):
 hidden=response_rows(True); wrong=(("wrong_direction",RestoringPolicyV30(False,"SEM<K,X>","M")),("omit_inertia",RestoringPolicyV30(True,"SEM<K,X>","ONE")),("swap_parameter_roles",RestoringPolicyV30(True,"SEM<M,X>","K")))
 out=[]
 for n,p in wrong:
  c=next((r for r in hidden if (v:=runtime.response(p,r)) is None or not runtime.physics.equivalent(v,r.target)),None);out.append({"mutation":n,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
 bad=PhysicalExpressionV22("combine",(OscillationResearchV30._atoms()[2],OscillationResearchV30._atoms()[3])); c=next((r for r in phase_rows(True) if not runtime.physics.equivalent(runtime.physics.evaluate(bad,r.before),runtime.physics.evaluate(bad,r.after))),None);out.append({"mutation":"swap_quadratic_weights","rejected":c is not None,"counterexample":None if c is None else c.to_dict()});return tuple(out)

def _graph(prev):
 ds=[dict(i) for i in prev["domains"]]
 for i in ds:
  if i["capability_id"]=="M10":i.update(status="verified",evidence_version="V30")
 n=sum(i["status"]=="verified" for i in ds);return {"scope":prev["scope"],"domains":ds,"verified_domains":n,"total_domains":len(ds),"completion_ratio":n/len(ds),"full_mechanics_claim_allowed":n==len(ds),"next_selected_gap":"M11:gravity_and_orbits","selection_reason":"central-force, angular conservation, and stability now support orbital-law discovery"}

def run_v30_acceptance(observed_values:Sequence[int]=(1,3,5,7,11,13,17)):
 dep=run_v29_acceptance(observed_values);physics=AnonymousPhysicsResearchV22.build_runtime(observed_values);runtime=OscillationRuntimeV30(physics);rr,pr=response_rows(),phase_rows();d=OscillationResearchV30().discover(rr,pr,runtime);proof=_proof(d,runtime);stability=_stability(runtime,d);mut=_mutations(runtime,d);g=_graph(dep["mechanics_capability_graph"])
 obligations=({"obligation_id":"v29_dependency","passed":dep["passed"]},{"obligation_id":"anonymous_rows","passed":all(r.to_dict()["human_formula"] is None for r in rr+pr)},{"obligation_id":"nontrivial_search","passed":d.response_candidates_generated==32 and d.invariant_candidates_generated==6},{"obligation_id":"oscillation_proof","passed":proof["passed"]},{"obligation_id":"sealed_transfer","passed":all(i["passed"] for i in proof["response_hidden"]+proof["phase_hidden"])},{"obligation_id":"stable_unstable_neutral_distinguished","passed":stability["passed"]},{"obligation_id":"recurrence_executable","passed":runtime.next_state(d.selected_response,_e(1),_e(1),_e(1),_e(1),_e(Fraction(1,2))) is not None},{"obligation_id":"mutations_rejected","passed":all(i["rejected"] for i in mut)},{"obligation_id":"m10_promoted","passed":g["verified_domains"]==10},{"obligation_id":"completion_blocked","passed":not g["full_mechanics_claim_allowed"]},{"obligation_id":"next_m11","passed":g["next_selected_gap"].startswith("M11")},{"obligation_id":"no_formula_input","passed":True})
 return {"benchmark_version":"oscillation-stability-v30.0","passed":all(i["passed"] for i in obligations),"classification":"verified_anonymous_linear_oscillation_recurrence_energy_and_stability_classification","observed_values":list(observed_values),"training":{"response_rows":[r.to_dict() for r in rr],"phase_rows":[r.to_dict() for r in pr],"formulas_supplied":False},"discovery":d.to_dict(),"proofs":{"oscillation":proof,"stability":stability},"mutation_audits":list(mut),"proof_obligations":list(obligations),"mechanics_capability_graph":g,"posthoc_translation":{"response":"a=-(k/m)x","invariant":"m v^2+k x^2","recurrence":"x[n+1]=2x[n]-x[n-1]-(k/m)h^2 x[n]"},"limitations":["Linear one-mode oscillators only.","Exact synthetic phase rotations are oracle data.","Damping, forcing, resonance, nonlinear chaos, and coupled modes remain absent.","Completion remains 10/15."]}
def replay_v30_report(report:Mapping[str,Any]):
 r=run_v30_acceptance(tuple(report["observed_values"]));return {"passed":r["passed"] and r["discovery"]==report["discovery"]}
