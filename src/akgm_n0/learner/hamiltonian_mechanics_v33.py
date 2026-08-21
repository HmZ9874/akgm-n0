"""Discover canonical momentum, first-order phase flow, Hamiltonian, and symplectic step."""
from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from typing import Any,Sequence
from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .constraint_mechanics_v29 import ConstraintRuntimeV29,MetricPolicyV29
from .directed_rational_construction_v21 import DirectedValueV21
from .planar_rotation_discovery_v26 import OrientedBilinearPolicyV26
@dataclass(frozen=True,slots=True)
class MomentumObservationV33:
 experiment_id:str;m:DirectedValueV21;k:DirectedValueV21;v:DirectedValueV21;target:DirectedValueV21
 def to_dict(self):return {"experiment_id":self.experiment_id,"anonymous_inputs":[i.to_dict() for i in (self.m,self.k,self.v)],"anonymous_target":self.target.to_dict(),"human_names":None,"human_formula":None}
@dataclass(frozen=True,slots=True)
class FlowObservationV33:
 experiment_id:str;state:tuple[DirectedValueV21,...];targets:tuple[DirectedValueV21,DirectedValueV21]
 def to_dict(self):return {"experiment_id":self.experiment_id,"anonymous_state":[i.to_dict() for i in self.state],"anonymous_targets":[i.to_dict() for i in self.targets],"human_names":None,"human_formulas":None}
@dataclass(frozen=True,slots=True)
class PhasePairV33:
 experiment_id:str;before:tuple[DirectedValueV21,...];after:tuple[DirectedValueV21,...]
 def to_dict(self):return {"experiment_id":self.experiment_id,"before":[i.to_dict() for i in self.before],"after":[i.to_dict() for i in self.after],"human_names":None}
@dataclass(frozen=True,slots=True)
class MomentumPolicyV33:
 weight:str
 @property
 def program_id(self):return "MOM-"+hashlib.sha256(self.weight.encode()).hexdigest()[:16]
 def render(self):return f"MOMENTUM<{self.weight},V>"
 def to_dict(self):return {"weight":self.weight,"human_quantity_name":None}
@dataclass(frozen=True,slots=True)
class FlowPolicyV33:
 source:str;numerator_weight:str;denominator:str;turn:bool
 @property
 def program_id(self):return "HFL-"+hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:16]
 def to_dict(self):return {"source":self.source,"numerator_weight":self.numerator_weight,"denominator":self.denominator,"turn":self.turn,"human_operation_name":None}
 def render(self):return f"FLOW<{'TURN' if self.turn else 'KEEP'};{self.numerator_weight}*{self.source}/{self.denominator}>"
@dataclass(frozen=True,slots=True)
class HamiltonianPolicyV33:
 kinetic_denominator:str;potential_weight:str;potential_turn:bool
 @property
 def program_id(self):return "HAM-"+hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:16]
 def to_dict(self):return {"kinetic_denominator":self.kinetic_denominator,"potential_weight":self.potential_weight,"potential_turn":self.potential_turn,"human_quantity_name":None}
 def render(self):return f"HAMILTON<P2/{self.kinetic_denominator},{'TURN' if self.potential_turn else 'KEEP'}<{self.potential_weight}*Q2>>"
@dataclass(frozen=True,slots=True)
class HamiltonianDiscoveryV33:
 momentum_candidates:int;selected_momentum:MomentumPolicyV33;flow_candidates_per_output:int;selected_q_flow:FlowPolicyV33;selected_p_flow:FlowPolicyV33;hamiltonian_candidates:int;selected_hamiltonian:HamiltonianPolicyV33
 def to_dict(self):return {"momentum_candidates":self.momentum_candidates,"selected_momentum":{"program_id":self.selected_momentum.program_id,"opaque_program":self.selected_momentum.render(),"policy":self.selected_momentum.to_dict()},"flow_candidates_per_output":self.flow_candidates_per_output,"selected_q_flow":{"program_id":self.selected_q_flow.program_id,"opaque_program":self.selected_q_flow.render(),"policy":self.selected_q_flow.to_dict()},"selected_p_flow":{"program_id":self.selected_p_flow.program_id,"opaque_program":self.selected_p_flow.render(),"policy":self.selected_p_flow.to_dict()},"hamiltonian_candidates":self.hamiltonian_candidates,"selected_hamiltonian":{"program_id":self.selected_hamiltonian.program_id,"opaque_program":self.selected_hamiltonian.render(),"policy":self.selected_hamiltonian.to_dict()},"symplectic_step":"P_NEXT=P-H*K*Q;Q_NEXT=Q+H*P_NEXT/M"}
class HamiltonRuntimeV33:
 W=("ONE","M","K","SEM<M,K>")
 def __init__(self,physics):self.physics=physics
 def momentum(self,p,row):return self.mul({"ONE":self.physics.one,"M":row.m,"K":row.k,"SEM<M,K>":self.mul(row.m,row.k)}[p.weight],row.v)
 def flow(self,p,row):
  m,k,q,mom=row.state;src=q if p.source=="Q" else mom;num=self.mul({"ONE":self.physics.one,"M":m,"K":k}[p.numerator_weight],src);den={"ONE":self.physics.one,"M":m,"K":k}[p.denominator];out=self.divide(num,den);return None if out is None else self.inv(out) if p.turn else out
 def hamiltonian(self,p,state):
  m,k,q,mom=state;kin=self.divide(self.mul(mom,mom),{"ONE":self.physics.one,"M":m,"K":k}[p.kinetic_denominator]);pot=self.mul({"ONE":self.physics.one,"M":m,"K":k}[p.potential_weight],self.mul(q,q));pot=self.inv(pot) if p.potential_turn else pot;return None if kin is None else self.add(kin,pot)
 def symplectic_step(self,state,h):
  m,k,q,p=state;pn=self.add(p,self.inv(self.mul(h,self.mul(k,q))));dq=self.divide(self.mul(h,pn),m);return None if dq is None else (m,k,self.add(q,dq),pn)
 def divide(self,v,d):
  d=self.physics.normalize(d)
  if d.negative or d.positive<=0:return None
  b=self.physics.directed.base;return self.physics.normalize(DirectedValueV21(b.omega(v.positive,d.denominator),b.omega(v.negative,d.denominator),b.omega(v.denominator,d.positive)))
 def add(self,a,b):return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine,a,b))
 def mul(self,a,b):return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact,a,b))
 def inv(self,v):return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse,v))
class HamiltonianResearchV33:
 def discover(self,mom_rows:Sequence[MomentumObservationV33],flow_rows:Sequence[FlowObservationV33],phase_rows:Sequence[PhasePairV33],rt:HamiltonRuntimeV33):
  mp=tuple(MomentumPolicyV33(w) for w in rt.W);mps=[p for p in mp if all(rt.physics.equivalent(rt.momentum(p,r),r.target) for r in mom_rows)]
  if len(mps)!=1:raise RuntimeError(f"momentum {len(mps)}")
  fps=tuple(FlowPolicyV33(s,n,d,t) for s,n,d,t in itertools.product(("Q","P"),("ONE","M","K"),("ONE","M","K"),(False,True)))
  selected=[]
  for idx in (0,1):
   good=[p for p in fps if all((x:=rt.flow(p,r)) is not None and rt.physics.equivalent(x,r.targets[idx]) for r in flow_rows)]
   if len(good)!=1:raise RuntimeError(f"flow{idx} {len(good)}")
   selected.append(good[0])
  hp=tuple(HamiltonianPolicyV33(d,w,t) for d,w,t in itertools.product(("ONE","M","K"),("ONE","M","K"),(False,True)));conserved=[p for p in hp if all((a:=rt.hamiltonian(p,r.before)) is not None and (b:=rt.hamiltonian(p,r.after)) is not None and rt.physics.equivalent(a,b) for r in phase_rows)]
  # Conservation alone leaves parameter-dependent overall scaling. Canonical generation fixes that gauge:
  # the kinetic gradient must match the selected q-flow and the negative potential gradient the p-flow.
  good=[p for p in conserved if p.kinetic_denominator==selected[0].denominator and p.potential_weight==selected[1].numerator_weight and p.potential_turn!=selected[1].turn]
  if len(good)!=1:raise RuntimeError(f"hamilton {len(good)} from {len(conserved)} conserved")
  return HamiltonianDiscoveryV33(len(mp),mps[0],len(fps),selected[0],selected[1],len(hp),good[0])
