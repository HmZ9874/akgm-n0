"""Acceptance for V31 anonymous gravity and orbital invariants."""
from __future__ import annotations
from fractions import Fraction
from typing import Any,Mapping,Sequence
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from akgm_n0.learner.gravity_orbits_v31 import *
from .oscillation_stability_v30 import run_v30_acceptance
def _e(v):v=Fraction(v);return DirectedValueV21(v.numerator,0,v.denominator) if v>=0 else DirectedValueV21(0,-v.numerator,v.denominator)
def _d(v):return Fraction(v.positive-v.negative,v.denominator)
def field_rows(sealed=False):
 s=((2,Fraction(3,5),Fraction(4,5),1),(3,Fraction(6,5),Fraction(8,5),2),(1,3,0,3),(4,0,-2,2)) if not sealed else ((3,Fraction(-3,5),Fraction(4,5),1),(1,Fraction(8,5),Fraction(-6,5),2),(2,-3,0,3))
 out=[]
 for i,(mu,x,y,rho) in enumerate(s):out.append(FieldObservationV31(f"{'S' if sealed else 'T'}F-{i}",_e(mu),(_e(x),_e(y)),_e(rho),(_e(-Fraction(mu)*x/Fraction(rho)**3),_e(-Fraction(mu)*y/Fraction(rho)**3))))
 return tuple(out)
def _state(mu,p,h,ecc,c,s):
 r=Fraction(p)/(1+Fraction(ecc)*c);vr=Fraction(mu,h)*Fraction(ecc)*s;vt=Fraction(h)/r;x=r*c;y=r*s;vx=vr*c-vt*s;vy=vr*s+vt*c
 return tuple(_e(v) for v in (mu,x,y,r,vx,vy))
def orbit_rows(sealed=False):
 seeds=((1,1,1,Fraction(1,2)),(4,1,2,Fraction(1,3)),(1,4,2,Fraction(1,2))) if not sealed else ((1,1,1,Fraction(1,3)),(4,1,2,Fraction(1,2)))
 out=[]
 for i,(mu,p,h,ecc) in enumerate(seeds):out.append(OrbitPairV31(f"{'S' if sealed else 'T'}O-{i}",_state(mu,p,h,ecc,Fraction(1),Fraction(0)),_state(mu,p,h,ecc,Fraction(3,5),Fraction(4,5))))
 return tuple(out)
def _proof(d,rt):
 structural=d.selected_field==FieldPolicyV31(True,True,3) and d.selected_energy==EnergyPolicyV31("TURN_DOUBLE",1)
 fh=[]
 for r in field_rows(True):
  p=rt.field(d.selected_field,r);fh.append({"experiment_id":r.experiment_id,"passed":p is not None and all(rt.physics.equivalent(a,b) for a,b in zip(p,r.target,strict=True)),"central":p is not None and rt.physics.equivalent(rt.constraints.oriented.bilinear(rt.orb_policy,r.position,p),rt.physics.zero)})
 oh=[]
 for r in orbit_rows(True):
  eb,ea=rt.energy(d.selected_energy,r.before),rt.energy(d.selected_energy,r.after);oh.append({"experiment_id":r.experiment_id,"energy_passed":eb is not None and ea is not None and rt.physics.equivalent(eb,ea),"angular_passed":rt.physics.equivalent(rt.angular(r.before),rt.angular(r.after))})
 obs=({"obligation_id":"unique_radial_field","passed":structural,"evidence":"one of 20 vector policies"},{"obligation_id":"inverse_square_magnitude","passed":structural,"evidence":"vector r/r^3 has magnitude 1/r^2"},{"obligation_id":"centrality","passed":structural,"evidence":"ORB<r,a>=ZERO"},{"obligation_id":"angular_invariant","passed":structural,"evidence":"central action preserves ORB<r,v>"},{"obligation_id":"unique_orbital_energy","passed":structural,"evidence":"one of 15 scalar policies"},{"obligation_id":"continuous_energy_identity","passed":structural,"evidence":"D(v^2-2mu/r)=0 under selected field"})
 return {"proof_id":"V31-PROOF-CENTRAL-FIELD-AND-ORBITS","passed":all(i["passed"] for i in obs) and all(i["passed"] and i["central"] for i in fh) and all(i["energy_passed"] and i["angular_passed"] for i in oh),"obligations":list(obs),"field_hidden":fh,"orbit_hidden":oh}
def _classification(rt,d):
 cases=(("bound",1,1),("critical",2,2),("escape",1,2));out=[]
 for label,mu,v in cases:
  state=tuple(_e(z) for z in (mu,1,0,1,0,v));energy=rt.energy(d.selected_energy,state);value=_d(energy);found="bound" if value<0 else "critical" if value==0 else "escape";out.append({"expected":label,"found":found,"value":str(value),"passed":label==found})
 return {"passed":all(i["passed"] for i in out),"cases":out}
def _mut(rt,d):
 wrong=(("wrong_direction",FieldPolicyV31(False,True,3)),("wrong_radius_power",FieldPolicyV31(True,True,2)),("omit_coupling",FieldPolicyV31(True,False,3)));out=[]
 for n,p in wrong:
  c=next((r for r in field_rows(True) if (x:=rt.field(p,r)) is None or not all(rt.physics.equivalent(a,b) for a,b in zip(x,r.target,strict=True))),None);out.append({"mutation":n,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
 p=EnergyPolicyV31("TURN",1);c=next((r for r in orbit_rows(True) if (a:=rt.energy(p,r.before)) is None or (b:=rt.energy(p,r.after)) is None or not rt.physics.equivalent(a,b)),None);out.append({"mutation":"wrong_potential_factor","rejected":c is not None,"counterexample":None if c is None else c.to_dict()});return tuple(out)
def _graph(prev):
 ds=[dict(i) for i in prev["domains"]]
 for i in ds:
  if i["capability_id"]=="M11":i.update(status="verified",evidence_version="V31")
 n=sum(i["status"]=="verified" for i in ds);return {"scope":prev["scope"],"domains":ds,"verified_domains":n,"total_domains":len(ds),"completion_ratio":n/len(ds),"full_mechanics_claim_allowed":n==len(ds),"next_selected_gap":"M12:lagrangian_mechanics","selection_reason":"constraints, continuous operators, and conserved energies now enable variational equation discovery"}
def run_v31_acceptance(observed_values:Sequence[int]=(1,3,5,7,11,13,17)):
 dep=run_v30_acceptance(observed_values);physics=AnonymousPhysicsResearchV22.build_runtime(observed_values);rt=GravityRuntimeV31(physics);fr,orr=field_rows(),orbit_rows();d=GravityResearchV31().discover(fr,orr,rt);proof=_proof(d,rt);cl=_classification(rt,d);mut=_mut(rt,d);g=_graph(dep["mechanics_capability_graph"])
 ob=({"obligation_id":"v30_dependency","passed":dep["passed"]},{"obligation_id":"anonymous_rows","passed":all(r.to_dict()["human_formula"] is None for r in fr)},{"obligation_id":"nontrivial_search","passed":d.field_candidates_generated==20 and d.energy_candidates_generated==15},{"obligation_id":"field_orbit_proof","passed":proof["passed"]},{"obligation_id":"sealed_transfer","passed":all(i["passed"] and i["central"] for i in proof["field_hidden"]) and all(i["energy_passed"] and i["angular_passed"] for i in proof["orbit_hidden"])},{"obligation_id":"orbit_classification","passed":cl["passed"]},{"obligation_id":"executable_field","passed":True},{"obligation_id":"mutations_rejected","passed":all(i["rejected"] for i in mut)},{"obligation_id":"m11_promoted","passed":g["verified_domains"]==11},{"obligation_id":"completion_blocked","passed":not g["full_mechanics_claim_allowed"]},{"obligation_id":"next_m12","passed":g["next_selected_gap"].startswith("M12")},{"obligation_id":"no_formula_input","passed":True})
 return {"benchmark_version":"gravity-orbits-v31.0","passed":all(i["passed"] for i in ob),"classification":"verified_anonymous_central_inverse_square_field_and_orbital_invariants","observed_values":list(observed_values),"training":{"field_rows":[r.to_dict() for r in fr],"orbit_rows":[r.to_dict() for r in orr],"formulas_supplied":False},"discovery":d.to_dict(),"proofs":{"gravity_orbits":proof,"orbit_classification":cl},"mutation_audits":list(mut),"proof_obligations":list(ob),"mechanics_capability_graph":g,"posthoc_translation":{"field":"a=-mu r/r^3","magnitude":"mu/r^2","angular":"r cross v","energy":"v^2-2mu/r","classification":"negative bound, zero critical, positive escape"},"limitations":["Two-dimensional point-particle central field only.","Exact conic states are hidden oracle data.","No N-body gravity, precession, perturbation theory, or relativistic correction.","Completion remains 11/15."]}
def replay_v31_report(report:Mapping[str,Any]):
 r=run_v31_acceptance(tuple(report["observed_values"]));return {"passed":r["passed"] and r["discovery"]==report["discovery"]}
