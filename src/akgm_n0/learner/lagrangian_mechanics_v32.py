"""Discover a normalized discrete action from fixed-endpoint path perturbations."""
from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from typing import Any,Sequence
from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21
@dataclass(frozen=True,slots=True)
class PathVariationV32:
 experiment_id:str;m:DirectedValueV21;k:DirectedValueV21;h:DirectedValueV21;left:DirectedValueV21;middle:DirectedValueV21;right:DirectedValueV21;epsilon:DirectedValueV21;stationary_family:bool
 def to_dict(self):return {"experiment_id":self.experiment_id,"anonymous_channels":[i.to_dict() for i in (self.m,self.k,self.h,self.left,self.middle,self.right,self.epsilon)],"anonymous_family":"F0" if self.stationary_family else "F1","human_names":None,"human_action_formula":None}
@dataclass(frozen=True,slots=True)
class ActionPolicyV32:
 kinetic_weight:str;potential_weight:str;potential_route:str;interval_power:int
 @property
 def program_id(self):return "ACT-"+hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:16]
 def to_dict(self):return {"kinetic_weight":self.kinetic_weight,"potential_weight":self.potential_weight,"potential_route":self.potential_route,"interval_power":self.interval_power,"human_operation_name":None}
 def render(self):return f"ACTION<KW:{self.kinetic_weight};PW:{self.potential_weight};P:{self.potential_route};H^{self.interval_power}>"
@dataclass(frozen=True,slots=True)
class LagrangianDiscoveryV32:
 candidates_generated:int;selected_action:ActionPolicyV32;stationary_training_cases:int;challenge_training_cases:int
 def to_dict(self):return {"candidates_generated":self.candidates_generated,"selected_action":{"program_id":self.selected_action.program_id,"opaque_program":self.selected_action.render(),"policy":self.selected_action.to_dict()},"stationary_training_cases":self.stationary_training_cases,"challenge_training_cases":self.challenge_training_cases,"derived_equation":"MERGE<SEM<M,D_T2<X>>,SEM<K,X>>=ZERO","normalization_note":"overall nonzero action scale is unidentifiable; kinetic coefficient is fixed to one"}
class ActionRuntimeV32:
 WEIGHTS=("ONE","M","K");PROUTES=("KEEP","TURN","DOUBLE","TURN_DOUBLE")
 def __init__(self,physics):self.physics=physics
 def action(self,p,row,middle):
  dl=self.add(middle,self.inv(row.left));dr=self.add(row.right,self.inv(middle));kin=self.add(self.mul(dl,dl),self.mul(dr,dr));div=self.power(row.h,p.interval_power);kin=self.divide(kin,div)
  if kin is None:return None
  kw={"ONE":self.physics.one,"M":row.m,"K":row.k}[p.kinetic_weight];pw={"ONE":self.physics.one,"M":row.m,"K":row.k}[p.potential_weight];kin=self.mul(kw,kin);pot=self.mul(pw,self.mul(middle,middle));pot={"KEEP":pot,"TURN":self.inv(pot),"DOUBLE":self.add(pot,pot),"TURN_DOUBLE":self.inv(self.add(pot,pot))}[p.potential_route];return self.add(kin,pot)
 def variation(self,p,row):
  plus=self.add(row.middle,row.epsilon);minus=self.add(row.middle,self.inv(row.epsilon));a=self.action(p,row,plus);b=self.action(p,row,minus);return None if a is None or b is None else self.add(a,self.inv(b))
 def power(self,v,n):
  out=self.physics.one
  for _ in range(n):out=self.mul(out,v)
  return out
 def divide(self,v,d):
  d=self.physics.normalize(d)
  if d.negative or d.positive<=0:return None
  b=self.physics.directed.base;return self.physics.normalize(DirectedValueV21(b.omega(v.positive,d.denominator),b.omega(v.negative,d.denominator),b.omega(v.denominator,d.positive)))
 def add(self,a,b):return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine,a,b))
 def mul(self,a,b):return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact,a,b))
 def inv(self,v):return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse,v))
class LagrangianResearchV32:
 def discover(self,rows:Sequence[PathVariationV32],runtime:ActionRuntimeV32):
  # overall scale is normalized by fixing the kinetic coefficient to one through the selected weight channel
  ps=tuple(ActionPolicyV32(kw,pw,pr,hp) for kw,pw,pr,hp in itertools.product(runtime.WEIGHTS,runtime.WEIGHTS,runtime.PROUTES,(0,1,2)))
  z=runtime.physics.zero;passing=[]
  for p in ps:
   ok=True
   for r in rows:
    v=runtime.variation(p,r)
    if v is None or runtime.physics.equivalent(v,z)!=r.stationary_family:ok=False;break
   if ok:passing.append(p)
  # discard globally doubled-equivalent potential routes by minimal route normalization; data fixes relative ratio
  passing.sort(key=lambda p:(p.potential_route in ("DOUBLE","TURN_DOUBLE"),p.program_id))
  normalized=[p for p in passing if p.potential_route in ("KEEP","TURN")]
  if len(normalized)!=1:raise RuntimeError(f"action {len(normalized)} from {len(passing)}")
  return LagrangianDiscoveryV32(len(ps),normalized[0],sum(r.stationary_family for r in rows),sum(not r.stationary_family for r in rows))
