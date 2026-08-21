"""Discover anonymous central inverse-cube vector response and orbital invariants."""
from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from typing import Any,Sequence
from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .constraint_mechanics_v29 import ConstraintRuntimeV29,MetricPolicyV29
from .directed_rational_construction_v21 import DirectedValueV21
from .planar_rotation_discovery_v26 import OrientedBilinearPolicyV26
Vector=tuple[DirectedValueV21,DirectedValueV21]
@dataclass(frozen=True,slots=True)
class FieldObservationV31:
 experiment_id:str;q0:DirectedValueV21;position:Vector;q3:DirectedValueV21;target:Vector
 def to_dict(self):return {"experiment_id":self.experiment_id,"anonymous_inputs":[self.q0.to_dict(),self.position[0].to_dict(),self.position[1].to_dict(),self.q3.to_dict()],"anonymous_target":[i.to_dict() for i in self.target],"human_names":None,"human_formula":None}
@dataclass(frozen=True,slots=True)
class OrbitPairV31:
 experiment_id:str;before:tuple[DirectedValueV21,...];after:tuple[DirectedValueV21,...]
 def to_dict(self):return {"experiment_id":self.experiment_id,"before":[i.to_dict() for i in self.before],"after":[i.to_dict() for i in self.after],"human_names":None,"human_formulas":None}
@dataclass(frozen=True,slots=True)
class FieldPolicyV31:
 turn:bool;use_q0:bool;radius_power:int
 @property
 def program_id(self):return "FLD-"+hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:16]
 def to_dict(self):return {"turn":self.turn,"use_q0":self.use_q0,"radius_power":self.radius_power,"human_operation_name":None}
 def render(self):return f"FIELD<{'TURN' if self.turn else 'KEEP'};{'SEM<Q0,R>' if self.use_q0 else 'R'};Q3^{self.radius_power}>"
@dataclass(frozen=True,slots=True)
class EnergyPolicyV31:
 potential_route:str;radius_power:int
 @property
 def program_id(self):return "ENE-"+hashlib.sha256((self.potential_route+str(self.radius_power)).encode()).hexdigest()[:16]
 def to_dict(self):return {"potential_route":self.potential_route,"radius_power":self.radius_power,"human_quantity_name":None}
 def render(self):return f"ENERGY<MET<V,V>,{self.potential_route}<Q0/Q3^{self.radius_power}>>"
@dataclass(frozen=True,slots=True)
class GravityDiscoveryV31:
 field_candidates_generated:int;selected_field:FieldPolicyV31;energy_candidates_generated:int;selected_energy:EnergyPolicyV31;training_field_cases:int;training_orbit_pairs:int
 def to_dict(self):return {"field_candidates_generated":self.field_candidates_generated,"selected_field":{"program_id":self.selected_field.program_id,"opaque_program":self.selected_field.render(),"policy":self.selected_field.to_dict()},"energy_candidates_generated":self.energy_candidates_generated,"selected_energy":{"program_id":self.selected_energy.program_id,"opaque_program":self.selected_energy.render(),"policy":self.selected_energy.to_dict()},"angular_invariant":"ORB<R,V>","training_field_cases":self.training_field_cases,"training_orbit_pairs":self.training_orbit_pairs,"executable_step":"V28_SECOND_STENCIL_WITH_SELECTED_FIELD"}
class GravityRuntimeV31:
 POT=("ZERO","KEEP","TURN","DOUBLE","TURN_DOUBLE")
 def __init__(self,physics):
  self.physics=physics;self.metric_policy=MetricPolicyV29(("KEEP","ZERO","ZERO","KEEP"));self.orb_policy=OrientedBilinearPolicyV26(("ZERO","KEEP","TURN","ZERO"));self.constraints=ConstraintRuntimeV29(physics,self.orb_policy)
 def field(self,p,row):
  scalar=row.q0 if p.use_q0 else self.physics.one
  divisor=self.power(row.q3,p.radius_power);scale=self.divide(scalar,divisor)
  if scale is None:return None
  out=(self.mul(row.position[0],scale),self.mul(row.position[1],scale));return (self.inv(out[0]),self.inv(out[1])) if p.turn else out
 def angular(self,state):return self.constraints.oriented.bilinear(self.orb_policy,(state[1],state[2]),(state[4],state[5]))
 def energy(self,p,state):
  mu,rho=state[0],state[3];kin=self.constraints.metric(self.metric_policy,(state[4],state[5]),(state[4],state[5]));base=self.divide(mu,self.power(rho,p.radius_power))
  if base is None:return None
  term={"ZERO":self.physics.zero,"KEEP":base,"TURN":self.inv(base),"DOUBLE":self.add(base,base),"TURN_DOUBLE":self.inv(self.add(base,base))}[p.potential_route]
  return self.add(kin,term)
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
class GravityResearchV31:
 def discover(self,fields:Sequence[FieldObservationV31],orbits:Sequence[OrbitPairV31],runtime:GravityRuntimeV31):
  fp=tuple(FieldPolicyV31(t,u,p) for t,u,p in itertools.product((False,True),(False,True),range(5)));passing=[p for p in fp if all((o:=runtime.field(p,r)) is not None and all(runtime.physics.equivalent(a,b) for a,b in zip(o,r.target,strict=True)) for r in fields)]
  if len(passing)!=1:raise RuntimeError(f"field {len(passing)}")
  ep=tuple(EnergyPolicyV31(r,p) for r,p in itertools.product(runtime.POT,range(3)));conserved=[p for p in ep if all((a:=runtime.energy(p,r.before)) is not None and (b:=runtime.energy(p,r.after)) is not None and runtime.physics.equivalent(a,b) for r in orbits)]
  if len(conserved)!=1:raise RuntimeError(f"energy {len(conserved)}")
  if not all(runtime.physics.equivalent(runtime.angular(r.before),runtime.angular(r.after)) for r in orbits):raise RuntimeError("angular invariant failed")
  return GravityDiscoveryV31(len(fp),passing[0],len(ep),conserved[0],len(fields),len(orbits))
