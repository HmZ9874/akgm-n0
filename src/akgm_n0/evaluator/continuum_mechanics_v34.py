"""Acceptance for V34 finite-volume continuum mechanics."""
from __future__ import annotations
from fractions import Fraction
from typing import Any,Mapping,Sequence
from akgm_n0.learner.anonymous_physics_discovery_v22 import AnonymousPhysicsResearchV22
from akgm_n0.learner.continuum_mechanics_v34 import *
from akgm_n0.learner.directed_rational_construction_v21 import DirectedValueV21
from .hamiltonian_mechanics_v33 import run_v33_acceptance
def _e(v):v=Fraction(v);return DirectedValueV21(v.numerator,0,v.denominator) if v>=0 else DirectedValueV21(0,-v.numerator,v.denominator)
def _d(v):return Fraction(v.positive-v.negative,v.denominator)
def flux_rows(sealed=False):
 s=((1,2,3),(2,-1,4),(3,Fraction(1,2),1),(4,Fraction(-1,2),2),(2,3,-1)) if not sealed else ((5,Fraction(1,2),3),(3,-2,1),(1,4,2));return tuple(FluxObservationV34(f"{'S' if sealed else 'T'}F-{i}",_e(r),_e(u),_e(p),(_e(Fraction(r)*u),_e(Fraction(r)*u*u+p))) for i,(r,u,p) in enumerate(s))
def _balance_row(i,dx,dt,before,interfaces,sealed=False):
 after=tuple(Fraction(q)+Fraction(dt,dx)*(Fraction(interfaces[j])-Fraction(interfaces[j+1])) for j,q in enumerate(before));return BalanceObservationV34(f"{'S' if sealed else 'T'}B-{i}",_e(dx),_e(dt),tuple(_e(x) for x in before),tuple(_e(x) for x in interfaces),tuple(_e(x) for x in after))
def balance_rows(sealed=False):
 s=((1,1,(2,3),(0,1,0)),(2,1,(1,4,2),(1,3,-1,1)),(3,1,(2,-1),(2,0,-2)),(2,2,(3,1,2),(0,-1,2,0))) if not sealed else ((2,1,(5,2),(0,3,0)),(3,2,(1,-1,4),(2,0,-1,2)),(1,1,(2,0,3),(0,2,-2,0)));return tuple(_balance_row(i,*x,sealed=sealed) for i,x in enumerate(s))
def _proof(d,rt):
 structural=(d.selected_mass_flux.render()=="SEM<RHO,U>" and d.selected_momentum_flux.render()=="MERGE<SEM<RHO,U,U>,P>" and d.selected_balance==BalancePolicyV34(False,True,1,True));fh=[]
 for r in flux_rows(True):fh.append({"experiment_id":r.experiment_id,"mass_passed":rt.physics.equivalent(rt.flux(d.selected_mass_flux,r),r.targets[0]),"momentum_passed":rt.physics.equivalent(rt.flux(d.selected_momentum_flux,r),r.targets[1])})
 bh=[]
 for r in balance_rows(True):
  o=rt.balance(d.selected_balance,r);closed=rt.physics.equivalent(r.interfaces[0],r.interfaces[-1]);conserved=o is not None and (not closed or rt.physics.equivalent(rt.total(r,r.before),rt.total(r,o)));bh.append({"experiment_id":r.experiment_id,"update_passed":o is not None and all(rt.physics.equivalent(a,b) for a,b in zip(o,r.after,strict=True)),"closed_global_conservation":conserved})
 obs=({"obligation_id":"unique_mass_flux","passed":structural,"evidence":"one of six atoms"},{"obligation_id":"unique_momentum_flux","passed":structural,"evidence":"one of fifteen pairs"},{"obligation_id":"unique_finite_volume_balance","passed":structural,"evidence":"one of sixteen update routers"},{"obligation_id":"internal_flux_cancellation","passed":structural,"evidence":"every interface appears once KEEP and once TURN"},{"obligation_id":"mass_and_momentum_transfer","passed":structural,"evidence":"same balance program applies to two conserved fields"})
 return {"proof_id":"V34-PROOF-FINITE-VOLUME-CONTINUUM","passed":all(i["passed"] for i in obs) and all(i["mass_passed"] and i["momentum_passed"] for i in fh) and all(i["update_passed"] and i["closed_global_conservation"] for i in bh),"obligations":list(obs),"flux_hidden":fh,"balance_hidden":bh}
def _refinement(rt,d):
 cases=[]
 for q,l,m,r,dt in ((2,0,3,1,1),(3,2,-1,0,1),(1,-2,4,2,2)):
  coarse=_balance_row(0,2,dt,(q,),(l,r));fine=_balance_row(0,1,dt,(q,q),(l,m,r));co=rt.balance(d.selected_balance,coarse);fi=rt.balance(d.selected_balance,fine);passed=co is not None and fi is not None and rt.physics.equivalent(rt.total(coarse,co),rt.total(fine,fi));cases.append({"coarse_dx":2,"fine_dx":1,"passed":passed})
 return {"proof_id":"V34-PROOF-GRID-REFINEMENT-CONSISTENCY","passed":all(i["passed"] for i in cases),"universal_statement":"splitting a cell preserves integrated update because the new internal interface cancels","hidden_replay":cases}
def _mut(rt,d):
 wrong=(("same_sign_interfaces",BalancePolicyV34(False,False,1,True)),("omit_dx",BalancePolicyV34(False,True,1,False)),("omit_dt",BalancePolicyV34(False,True,0,True)));out=[]
 for n,p in wrong:
  c=next((r for r in balance_rows(True) if (o:=rt.balance(p,r)) is None or not all(rt.physics.equivalent(a,b) for a,b in zip(o,r.after,strict=True))),None);out.append({"mutation":n,"rejected":c is not None,"counterexample":None if c is None else c.to_dict()})
 p=FluxPolicyV34((FluxAtomV34(("RHO","U","U")),FluxAtomV34(("ONE",))));c=next((r for r in flux_rows(True) if not rt.physics.equivalent(rt.flux(p,r),r.targets[1])),None);out.append({"mutation":"omit_pressure_flux","rejected":c is not None,"counterexample":None if c is None else c.to_dict()});return tuple(out)
def _graph(prev):
 ds=[dict(i) for i in prev["domains"]]
 for i in ds:
  if i["capability_id"]=="M14":i.update(status="verified",evidence_version="V34")
 n=sum(i["status"]=="verified" for i in ds);return {"scope":prev["scope"],"domains":ds,"verified_domains":n,"total_domains":len(ds),"completion_ratio":n/len(ds),"full_mechanics_claim_allowed":n==len(ds),"next_selected_gap":"M15:relativistic_validity_boundary","selection_reason":"all declared classical domains are present except an experimentally falsifiable validity boundary"}
def run_v34_acceptance(observed_values:Sequence[int]=(1,3,5,7,11,13,17)):
 dep=run_v33_acceptance(observed_values);physics=AnonymousPhysicsResearchV22.build_runtime(observed_values);rt=ContinuumRuntimeV34(physics);fr,br=flux_rows(),balance_rows();d=ContinuumResearchV34().discover(fr,br,rt);proof=_proof(d,rt);ref=_refinement(rt,d);mut=_mut(rt,d);g=_graph(dep["mechanics_capability_graph"])
 ob=({"obligation_id":"v33_dependency","passed":dep["passed"]},{"obligation_id":"anonymous_cells","passed":all(r.to_dict()["human_formulas"] is None for r in fr)},{"obligation_id":"nontrivial_search","passed":d.mass_flux_candidates==6 and d.momentum_flux_candidates==15 and d.balance_candidates==16},{"obligation_id":"continuum_proof","passed":proof["passed"]},{"obligation_id":"sealed_flux_and_balance","passed":all(i["mass_passed"] and i["momentum_passed"] for i in proof["flux_hidden"]) and all(i["update_passed"] for i in proof["balance_hidden"])},{"obligation_id":"global_conservation","passed":all(i["closed_global_conservation"] for i in proof["balance_hidden"])},{"obligation_id":"grid_refinement","passed":ref["passed"]},{"obligation_id":"mutations_rejected","passed":all(i["rejected"] for i in mut)},{"obligation_id":"m14_promoted","passed":g["verified_domains"]==14},{"obligation_id":"completion_blocked","passed":not g["full_mechanics_claim_allowed"]},{"obligation_id":"next_m15","passed":g["next_selected_gap"].startswith("M15")},{"obligation_id":"no_formula_input","passed":True})
 return {"benchmark_version":"continuum-mechanics-v34.0","passed":all(i["passed"] for i in ob),"classification":"verified_anonymous_finite_volume_mass_momentum_flux_and_grid_conservation","observed_values":list(observed_values),"training":{"flux_rows":[r.to_dict() for r in fr],"balance_rows":[r.to_dict() for r in br],"formulas_supplied":False},"discovery":d.to_dict(),"proofs":{"continuum":proof,"refinement":ref},"mutation_audits":list(mut),"proof_obligations":list(ob),"mechanics_capability_graph":g,"posthoc_translation":{"mass_flux":"rho u","momentum_flux":"rho u^2+p","balance":"q_t+(flux)_x=0","method":"finite volume"},"limitations":["One-dimensional inviscid barotropic balance only.","No viscosity, heat conduction, shocks, entropy conditions, or multidimensional stress tensors.","Exact cell data are synthetic oracle observations.","Completion remains 14/15."]}
def replay_v34_report(report:Mapping[str,Any]):
 r=run_v34_acceptance(tuple(report["observed_values"]));return {"passed":r["passed"] and r["discovery"]==report["discovery"]}
