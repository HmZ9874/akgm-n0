"""Discover restoring response, executable oscillation recurrence, and quadratic phase invariant."""
from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from typing import Any,Sequence
from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22,PhysicalExpressionV22
from .directed_rational_construction_v21 import DirectedValueV21

@dataclass(frozen=True,slots=True)
class RestoringObservationV30:
 experiment_id:str; q0:DirectedValueV21; q1:DirectedValueV21; q2:DirectedValueV21; target:DirectedValueV21
 def to_dict(self): return {"experiment_id":self.experiment_id,"anonymous_inputs":[self.q0.to_dict(),self.q1.to_dict(),self.q2.to_dict()],"anonymous_target":self.target.to_dict(),"human_names":None,"human_formula":None}
@dataclass(frozen=True,slots=True)
class PhaseObservationV30:
 experiment_id:str; before:tuple[DirectedValueV21,...]; after:tuple[DirectedValueV21,...]
 def to_dict(self): return {"experiment_id":self.experiment_id,"before":[i.to_dict() for i in self.before],"after":[i.to_dict() for i in self.after],"human_names":None,"human_formula":None}
@dataclass(frozen=True,slots=True)
class RestoringPolicyV30:
 turn:bool; numerator_route:str; denominator_route:str
 @property
 def program_id(self): return "RST-"+hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:16]
 def to_dict(self): return {"turn":self.turn,"numerator_route":self.numerator_route,"denominator_route":self.denominator_route,"human_operation_name":None}
 def render(self): return f"RESTORE<{'TURN' if self.turn else 'KEEP'};NUM:{self.numerator_route};DEN:{self.denominator_route}>"
@dataclass(frozen=True,slots=True)
class OscillationDiscoveryV30:
 response_candidates_generated:int; selected_response:RestoringPolicyV30; invariant_candidates_generated:int; selected_invariant:PhysicalExpressionV22; training_response_cases:int; training_phase_cases:int
 def to_dict(self): return {"response_candidates_generated":self.response_candidates_generated,"selected_response":{"program_id":self.selected_response.program_id,"opaque_program":self.selected_response.render(),"policy":self.selected_response.to_dict()},"invariant_candidates_generated":self.invariant_candidates_generated,"selected_invariant":{"program_id":self.selected_invariant.expression_id,"opaque_program":self.selected_invariant.render(),"expression":self.selected_invariant.to_dict(),"human_quantity_name":None},"training_response_cases":self.training_response_cases,"training_phase_cases":self.training_phase_cases,"recurrence_program":"X_NEXT=MERGE<DOUBLE<X>,TURN<X_PREV>,SEM<H,H,A>>"}

class OscillationRuntimeV30:
 NUM=("X","SEM<K,X>","SEM<M,X>","SEM<M,SEM<K,X>>"); DEN=("ONE","M","K","SEM<M,K>")
 def __init__(self,physics): self.physics=physics
 def response(self,p,row):
  m,k,x=row.q0,row.q1,row.q2
  numerator={"X":x,"SEM<K,X>":self.mul(k,x),"SEM<M,X>":self.mul(m,x),"SEM<M,SEM<K,X>>":self.mul(m,self.mul(k,x))}[p.numerator_route]
  divisor={"ONE":self.physics.one,"M":m,"K":k,"SEM<M,K>":self.mul(m,k)}[p.denominator_route]
  out=self.divide(numerator,divisor)
  return None if out is None else self.inv(out) if p.turn else out
 def next_state(self,policy,m,k,previous,current,h):
  row=RestoringObservationV30("runtime",m,k,current,self.physics.zero); acc=self.response(policy,row)
  if acc is None:return None
  return self.add(self.add(current,current),self.add(self.inv(previous),self.mul(self.mul(h,h),acc)))
 def divide(self,v,d):
  d=self.physics.normalize(d)
  if d.negative or d.positive<=0:return None
  b=self.physics.directed.base
  return self.physics.normalize(DirectedValueV21(b.omega(v.positive,d.denominator),b.omega(v.negative,d.denominator),b.omega(v.denominator,d.positive)))
 def add(self,a,b): return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine,a,b))
 def mul(self,a,b): return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact,a,b))
 def inv(self,v): return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse,v))

class OscillationResearchV30:
 def discover(self,response_rows:Sequence[RestoringObservationV30],phase_rows:Sequence[PhaseObservationV30],runtime:OscillationRuntimeV30):
  policies=tuple(RestoringPolicyV30(t,n,d) for t,n,d in itertools.product((False,True),runtime.NUM,runtime.DEN))
  passing=[p for p in policies if all((o:=runtime.response(p,r)) is not None and runtime.physics.equivalent(o,r.target) for r in response_rows)]
  if len(passing)!=1: raise RuntimeError(f"expected one restoring policy, found {len(passing)}")
  atoms=self._atoms(); candidates=tuple(PhysicalExpressionV22("combine",(atoms[i],atoms[j])) for i in range(4) for j in range(i+1,4))
  conserved=[e for e in candidates if all(runtime.physics.equivalent(runtime.physics.evaluate(e,r.before),runtime.physics.evaluate(e,r.after)) for r in phase_rows)]
  if len(conserved)!=1: raise RuntimeError(f"expected one phase invariant, found {len(conserved)}")
  return OscillationDiscoveryV30(len(policies),passing[0],len(candidates),conserved[0],len(response_rows),len(phase_rows))
 @staticmethod
 def _atoms():
  r=lambda i:PhysicalExpressionV22("read",channel=i); sq=lambda i:PhysicalExpressionV22("interact",(r(i),r(i)))
  return (PhysicalExpressionV22("interact",(r(0),sq(3))),PhysicalExpressionV22("interact",(r(1),sq(2))),PhysicalExpressionV22("interact",(r(0),sq(2))),PhysicalExpressionV22("interact",(r(1),sq(3))))
