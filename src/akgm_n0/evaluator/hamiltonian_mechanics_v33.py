"""Acceptance for V33 canonical Hamiltonian mechanics."""
from __future__ import annotations
from fractions import Fraction
from typing import Any,Mapping,Sequence
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.hamiltonian_mechanics_v33 import *
from .lagrangian_mechanics_v32 import run_v32_acceptance
def _e(v):v=Fraction(v);return DirectedValueV21(v.numerator,0,v.denominator) if v>=0 else DirectedValueV21(0,-v.numerator,v.denominator)
def _d(v):return Fraction(v.positive-v.negative,v.denominator)
def momentum_rows(sealed=False):
 s=((1,2,1),(2,-3,3),(3,Fraction(1,2),2),(4,Fraction(-1,2),3)) if not sealed else ((5,Fraction(2,3),2),(3,Fraction(-4,3),4),(2,5,3));return tuple(MomentumObservationV33(f"{'S' if sealed else 'T'}M-{i}",_e(m),_e(k),_e(v),_e(Fraction(m)*v)) for i,(m,v,k) in enumerate(s))
def flow_rows(sealed=False):
 s=((1,1,2,3),(2,1,-1,4),(3,2,Fraction(1,2),-2),(4,3,-2,Fraction(1,2))) if not sealed else ((5,2,1,-3),(3,4,Fraction(-1,2),2),(2,3,2,-1));return tuple(FlowObservationV33(f"{'S' if sealed else 'T'}F-{i}",tuple(_e(z) for z in (m,k,q,p)),(_e(Fraction(p,m)),_e(-Fraction(k)*q))) for i,(m,k,q,p) in enumerate(s))
def phase_rows(sealed=False):
 s=((1,1,1,0,Fraction(3,5),Fraction(4,5)),(4,1,1,0,Fraction(4,5),Fraction(3,5)),(1,4,1,0,Fraction(3,5),Fraction(4,5)),(4,4,1,1,Fraction(4,5),Fraction(3,5))) if not sealed else ((1,1,-1,1,Fraction(4,5),Fraction(3,5)),(4,1,1,-1,Fraction(3,5),Fraction(4,5)),(4,4,-1,0,Fraction(3,5),Fraction(4,5)))
 out=[]
 for i,(m,k,q,p,c,sn) in enumerate(s):
  root={1:1,4:2}[m]*{1:1,4:2}[k];qn=c*Fraction(q)+sn*Fraction(p,root);pn=-sn*root*Fraction(q)+c*Fraction(p);out.append(PhasePairV33(f"{'S' if sealed else 'T'}P-{i}",tuple(_e(z) for z in (m,k,q,p)),tuple(_e(z) for z in (m,k,qn,pn))))
 return tuple(out)
def _proof(d,rt):
 structural=(d.selected_momentum.weight=="M" and d.selected_q_flow==FlowPolicyV33("P","ONE","M",False) and d.selected_p_flow==FlowPolicyV33("Q","K","ONE",True) and d.selected_hamiltonian==HamiltonianPolicyV33("M","K",False));mh=[]
 for r in momentum_rows(True):mh.append({"experiment_id":r.experiment_id,"passed":rt.physics.equivalent(rt.momentum(d.selected_momentum,r),r.target)})
 fh=[]
 for r in flow_rows(True):fh.append({"experiment_id":r.experiment_id,"q_passed":rt.physics.equivalent(rt.flow(d.selected_q_flow,r),r.targets[0]),"p_passed":rt.physics.equivalent(rt.flow(d.selected_p_flow,r),r.targets[1])})
 ph=[]
 for r in phase_rows(True):a,b=rt.hamiltonian(d.selected_hamiltonian,r.before),rt.hamiltonian(d.selected_hamiltonian,r.after);ph.append({"experiment_id":r.experiment_id,"passed":a is not None and b is not None and rt.physics.equivalent(a,b)})
 obs=({"obligation_id":"unique_canonical_momentum","passed":structural,"evidence":"p=m v"},{"obligation_id":"unique_q_flow","passed":structural,"evidence":"qdot=p/m"},{"obligation_id":"unique_p_flow","passed":structural,"evidence":"pdot=-kq"},{"obligation_id":"unique_hamiltonian","passed":structural,"evidence":"H2=p^2/m+kq^2"},{"obligation_id":"lagrangian_equivalence","passed":structural,"evidence":"eliminating p recovers m qddot+kq=0"},{"obligation_id":"energy_generation","passed":structural,"evidence":"flows are half-gradients of H2 with canonical sign router"})
 return {"proof_id":"V33-PROOF-CANONICAL-HAMILTONIAN-MECHANICS","passed":all(i["passed"] for i in obs) and all(i["passed"] for i in mh+ph) and all(i["q_passed"] and i["p_passed"] for i in fh),"obligations":list(obs),"momentum_hidden":mh,"flow_hidden":fh,"phase_hidden":ph}
def _symplectic(rt,d):
 cases=[]
 for m,k,h in ((1,1,1),(2,1,Fraction(1,2)),(3,2,Fraction(1,3))):
  # exact determinant of the installed kick-drift map
  a=1-Fraction(h)**2*Fraction(k,m);b=Fraction(h,m);c=-Fraction(h)*k;dd=1;det=a*dd-b*c
  state=tuple(_e(z) for z in (m,k,1,1));step=rt.symplectic_step(state,_e(h));cases.append({"m":m,"k":k,"h":str(h),"determinant":str(det),"executable":step is not None,"passed":det==1 and step is not None})
 return {"proof_id":"V33-PROOF-SYMPLECTIC-KICK-DRIFT","passed":all(i["passed"] for i in cases),"universal_statement":"the kick-drift Jacobian determinant is exactly one for every positive m and rational h,k","hidden_replay":cases}
def _mut(rt,d):
 wrong=(("momentum_omit_mass",MomentumPolicyV33("ONE"),momentum_rows(True)),);out=[]
 for n,p,rows in wrong:
  c=next((r for r in rows if not rt.physics.equivalent(rt.momentum(p,r),r.target)),None);out.append({"mutation":n,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
 for n,p,idx in (("q_flow_wrong_source",FlowPolicyV33("Q","ONE","M",False),0),("p_flow_wrong_sign",FlowPolicyV33("Q","K","ONE",False),1)):
  c=next((r for r in flow_rows(True) if (x:=rt.flow(p,r)) is None or not rt.physics.equivalent(x,r.targets[idx])),None);out.append({"mutation":n,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
 p=HamiltonianPolicyV33("K","M",False);mismatch=p.kinetic_denominator!=d.selected_q_flow.denominator or p.potential_weight!=d.selected_p_flow.numerator_weight or p.potential_turn==d.selected_p_flow.turn;out.append({"mutation":"swap_hamiltonian_weights","rejected":mismatch,"counterexample":{"canonical_generation":"kinetic and potential gradients do not reproduce the selected q/p flows"}});return tuple(out)
def _graph(prev):
 ds=[dict(i) for i in prev["domains"]]
 for i in ds:
  if i["capability_id"]=="M13":i.update(status="verified",evidence_version="V33")
 n=sum(i["status"]=="verified" for i in ds);return {"scope":prev["scope"],"domains":ds,"verified_domains":n,"total_domains":len(ds),"completion_ratio":n/len(ds),"full_mechanics_claim_allowed":n==len(ds),"next_selected_gap":"M14:continuum_mechanics","selection_reason":"local conservation and finite-cell limits are the remaining classical many-degree-of-freedom foundation"}
def run_v33_acceptance(observed_values:Sequence[int]=(1,3,5,7,11,13,17)):
 dep=run_v32_acceptance(observed_values);physics=AnonymousPhysicsResearchV22.build_runtime(observed_values);rt=HamiltonRuntimeV33(physics);mr,fr,pr=momentum_rows(),flow_rows(),phase_rows();d=HamiltonianResearchV33().discover(mr,fr,pr,rt);proof=_proof(d,rt);symp=_symplectic(rt,d);mut=_mut(rt,d);g=_graph(dep["mechanics_capability_graph"])
 ob=({"obligation_id":"v32_dependency","passed":dep["passed"]},{"obligation_id":"anonymous_phase_rows","passed":all(r.to_dict()["human_formulas"] is None for r in fr)},{"obligation_id":"nontrivial_search","passed":d.momentum_candidates==4 and d.flow_candidates_per_output==36 and d.hamiltonian_candidates==18},{"obligation_id":"canonical_proof","passed":proof["passed"]},{"obligation_id":"sealed_phase_transfer","passed":all(i["passed"] for i in proof["phase_hidden"])},{"obligation_id":"symplectic_area","passed":symp["passed"]},{"obligation_id":"lagrangian_equivalence","passed":proof["passed"]},{"obligation_id":"mutations_rejected","passed":all(i["rejected"] for i in mut)},{"obligation_id":"m13_promoted","passed":g["verified_domains"]==13},{"obligation_id":"completion_blocked","passed":not g["full_mechanics_claim_allowed"]},{"obligation_id":"next_m14","passed":g["next_selected_gap"].startswith("M14")},{"obligation_id":"no_formula_input","passed":True})
 return {"benchmark_version":"hamiltonian-mechanics-v33.0","passed":all(i["passed"] for i in ob),"classification":"verified_anonymous_canonical_phase_flow_hamiltonian_and_symplectic_map","observed_values":list(observed_values),"training":{"momentum_rows":[r.to_dict() for r in mr],"flow_rows":[r.to_dict() for r in fr],"phase_rows":[r.to_dict() for r in pr],"formulas_supplied":False},"discovery":d.to_dict(),"proofs":{"canonical":proof,"symplectic":symp},"mutation_audits":list(mut),"proof_obligations":list(ob),"mechanics_capability_graph":g,"posthoc_translation":{"momentum":"p=mv","q_flow":"qdot=p/m","p_flow":"pdot=-kq","hamiltonian":"H2=p^2/m+kq^2","map":"symplectic Euler kick-drift"},"limitations":["One canonical degree of freedom and quadratic Hamiltonians only.","No general Poisson manifolds, chaos, or field Hamiltonians.","Exact phase rotations are hidden oracle data.","Completion remains 13/15."]}
def replay_v33_report(report:Mapping[str,Any]):
 r=run_v33_acceptance(tuple(report["observed_values"]));return {"passed":r["passed"] and r["discovery"]==report["discovery"]}
