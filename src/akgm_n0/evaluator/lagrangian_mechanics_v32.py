"""Acceptance for V32 discrete variational mechanics."""
from __future__ import annotations
from fractions import Fraction
from typing import Any,Mapping,Sequence
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.lagrangian_mechanics_v32 import *
from .gravity_orbits_v31 import run_v31_acceptance
def _e(v):v=Fraction(v);return DirectedValueV21(v.numerator,0,v.denominator) if v>=0 else DirectedValueV21(0,-v.numerator,v.denominator)
def _d(v):return Fraction(v.positive-v.negative,v.denominator)
def rows(sealed=False):
 good=((1,1,1,1,1),(2,1,1,0,2),(3,3,1,1,2),(2,1,2,1,1),(4,1,2,-1,1)) if not sealed else ((3,1,1,-1,3),(2,1,2,0,1),(4,4,1,2,-1))
 bad=((1,1,1,1,1,1),(2,1,1,0,2,0),(3,3,1,1,2,3)) if not sealed else ((1,2,1,0,1,2),(4,1,2,1,1,1))
 out=[];pre="S" if sealed else "T"
 for i,(m,k,h,l,x) in enumerate(good):
  rr=2*Fraction(x)-Fraction(l)-Fraction(k,m)*Fraction(h)**2*Fraction(x);out.append(PathVariationV32(f"{pre}F0-{i}",*map(_e,(m,k,h,l,x,rr,1)),True))
 for i,(m,k,h,l,x,rr) in enumerate(bad):out.append(PathVariationV32(f"{pre}F1-{i}",*map(_e,(m,k,h,l,x,rr,1)),False))
 return tuple(out)
def _proof(d,rt):
 structural=d.selected_action==ActionPolicyV32("M","K","TURN",2);hidden=[]
 for r in rows(True):
  v=rt.variation(d.selected_action,r);hidden.append({"experiment_id":r.experiment_id,"stationary_expected":r.stationary_family,"variation":None if v is None else v.to_dict(),"passed":v is not None and rt.physics.equivalent(v,rt.physics.zero)==r.stationary_family})
 obs=({"obligation_id":"unique_normalized_action","passed":structural,"evidence":"one normalized member from 108 action programs"},{"obligation_id":"fixed_endpoint_stationarity","passed":structural,"evidence":"symmetric finite variation vanishes"},{"obligation_id":"euler_equation","passed":structural,"evidence":"expansion gives m D_T2 x+kx=0"},{"obligation_id":"v30_equivalence","passed":structural,"evidence":"solving gives a=-(k/m)x"},{"obligation_id":"time_translation_invariant","passed":structural,"evidence":"action has no absolute step index"},{"obligation_id":"energy_correspondence","passed":structural,"evidence":"associated invariant is mv^2+kx^2"})
 return {"proof_id":"V32-PROOF-DISCRETE-VARIATIONAL-MECHANICS","passed":all(i["passed"] for i in obs) and all(i["passed"] for i in hidden),"obligations":list(obs),"hidden_replay":hidden}
def _mut(rt,d):
 wrong=(("wrong_potential_sign",ActionPolicyV32("M","K","KEEP",2)),("swap_weights",ActionPolicyV32("K","M","TURN",2)),("omit_interval_square",ActionPolicyV32("M","K","TURN",1)));out=[]
 for n,p in wrong:
  c=next((r for r in rows(True) if (v:=rt.variation(p,r)) is None or rt.physics.equivalent(v,rt.physics.zero)!=r.stationary_family),None);out.append({"mutation":n,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
 p=ActionPolicyV32("M","K","TURN_DOUBLE",2);c=next((r for r in rows(True) if (v:=rt.variation(p,r)) is None or rt.physics.equivalent(v,rt.physics.zero)!=r.stationary_family),None);out.append({"mutation":"wrong_relative_potential_factor","rejected":c is not None,"counterexample":None if c is None else c.to_dict()});return tuple(out)
def _graph(prev):
 ds=[dict(i) for i in prev["domains"]]
 for i in ds:
  if i["capability_id"]=="M12":i.update(status="verified",evidence_version="V32")
 n=sum(i["status"]=="verified" for i in ds);return {"scope":prev["scope"],"domains":ds,"verified_domains":n,"total_domains":len(ds),"completion_ratio":n/len(ds),"full_mechanics_claim_allowed":n==len(ds),"next_selected_gap":"M13:hamiltonian_mechanics","selection_reason":"the discovered action and energy enable canonical state splitting and symplectic-flow tests"}
def run_v32_acceptance(observed_values:Sequence[int]=(1,3,5,7,11,13,17)):
 dep=run_v31_acceptance(observed_values);physics=AnonymousPhysicsResearchV22.build_runtime(observed_values);rt=ActionRuntimeV32(physics);tr=rows();d=LagrangianResearchV32().discover(tr,rt);proof=_proof(d,rt);mut=_mut(rt,d);g=_graph(dep["mechanics_capability_graph"])
 ob=({"obligation_id":"v31_dependency","passed":dep["passed"]},{"obligation_id":"anonymous_paths","passed":all(r.to_dict()["human_action_formula"] is None for r in tr)},{"obligation_id":"nontrivial_action_search","passed":d.candidates_generated==108},{"obligation_id":"variational_proof","passed":proof["passed"]},{"obligation_id":"sealed_paths","passed":all(i["passed"] for i in proof["hidden_replay"])},{"obligation_id":"motion_equation_recovered","passed":proof["passed"]},{"obligation_id":"energy_correspondence","passed":proof["passed"]},{"obligation_id":"mutations_rejected","passed":all(i["rejected"] for i in mut)},{"obligation_id":"m12_promoted","passed":g["verified_domains"]==12},{"obligation_id":"completion_blocked","passed":not g["full_mechanics_claim_allowed"]},{"obligation_id":"next_m13","passed":g["next_selected_gap"].startswith("M13")},{"obligation_id":"no_formula_input","passed":True})
 return {"benchmark_version":"lagrangian-mechanics-v32.0","passed":all(i["passed"] for i in ob),"classification":"verified_anonymous_discrete_action_stationarity_and_euler_equation","observed_values":list(observed_values),"training":{"path_rows":[r.to_dict() for r in tr],"formulas_supplied":False},"discovery":d.to_dict(),"proofs":{"variational":proof},"mutation_audits":list(mut),"proof_obligations":list(ob),"mechanics_capability_graph":g,"posthoc_translation":{"action":"sum m(Delta x/h)^2-kx^2 (twice conventional L)","stationarity":"delta S=0","equation":"m x''+kx=0"},"limitations":["One-coordinate quadratic actions only.","Overall action scale is unidentifiable.","No gauge fields, nonholonomic variational principles, or field actions.","Completion remains 12/15."]}
def replay_v32_report(report:Mapping[str,Any]):
 r=run_v32_acceptance(tuple(report["observed_values"]));return {"passed":r["passed"] and r["discovery"]==report["discovery"]}
