"""Discover local continuum fluxes and finite-volume conservation updates."""
from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from typing import Any,Sequence
from .anonymous_physics_discovery_v22 import DirectedPhysicsRuntimeV22
from .directed_rational_construction_v21 import DirectedValueV21
@dataclass(frozen=True,slots=True)
class FluxObservationV34:
 experiment_id:str;rho:DirectedValueV21;u:DirectedValueV21;p:DirectedValueV21;targets:tuple[DirectedValueV21,DirectedValueV21]
 def to_dict(self):return {"experiment_id":self.experiment_id,"anonymous_inputs":[i.to_dict() for i in (self.rho,self.u,self.p)],"anonymous_targets":[i.to_dict() for i in self.targets],"human_names":None,"human_formulas":None}
@dataclass(frozen=True,slots=True)
class BalanceObservationV34:
 experiment_id:str;dx:DirectedValueV21;dt:DirectedValueV21;before:tuple[DirectedValueV21,...];interfaces:tuple[DirectedValueV21,...];after:tuple[DirectedValueV21,...]
 def to_dict(self):return {"experiment_id":self.experiment_id,"dx":self.dx.to_dict(),"dt":self.dt.to_dict(),"before":[i.to_dict() for i in self.before],"interfaces":[i.to_dict() for i in self.interfaces],"after":[i.to_dict() for i in self.after],"human_names":None,"human_formula":None}
@dataclass(frozen=True,slots=True)
class FluxAtomV34:
 factors:tuple[str,...]
 def render(self):return "SEM<"+",".join(self.factors)+">" if len(self.factors)>1 else self.factors[0]
@dataclass(frozen=True,slots=True)
class FluxPolicyV34:
 atoms:tuple[FluxAtomV34,...]
 @property
 def program_id(self):return "CFX-"+hashlib.sha256(self.render().encode()).hexdigest()[:16]
 def render(self):return "MERGE<"+",".join(a.render() for a in self.atoms)+">" if len(self.atoms)>1 else self.atoms[0].render()
 def to_dict(self):return {"atoms":[list(a.factors) for a in self.atoms],"human_quantity_name":None}
@dataclass(frozen=True,slots=True)
class BalancePolicyV34:
 left_turn:bool;right_turn:bool;interval_power:int;divide_dx:bool
 @property
 def program_id(self):return "BAL-"+hashlib.sha256(json.dumps(self.to_dict(),sort_keys=True).encode()).hexdigest()[:16]
 def to_dict(self):return {"left_turn":self.left_turn,"right_turn":self.right_turn,"interval_power":self.interval_power,"divide_dx":self.divide_dx,"human_operation_name":None}
 def render(self):return f"BALANCE<L:{'TURN' if self.left_turn else 'KEEP'};R:{'TURN' if self.right_turn else 'KEEP'};DT^{self.interval_power};DX:{'DIV' if self.divide_dx else 'ONE'}>"
@dataclass(frozen=True,slots=True)
class ContinuumDiscoveryV34:
 mass_flux_candidates:int;selected_mass_flux:FluxPolicyV34;momentum_flux_candidates:int;selected_momentum_flux:FluxPolicyV34;balance_candidates:int;selected_balance:BalancePolicyV34
 def to_dict(self):return {"mass_flux_candidates":self.mass_flux_candidates,"selected_mass_flux":{"program_id":self.selected_mass_flux.program_id,"opaque_program":self.selected_mass_flux.render(),"policy":self.selected_mass_flux.to_dict()},"momentum_flux_candidates":self.momentum_flux_candidates,"selected_momentum_flux":{"program_id":self.selected_momentum_flux.program_id,"opaque_program":self.selected_momentum_flux.render(),"policy":self.selected_momentum_flux.to_dict()},"balance_candidates":self.balance_candidates,"selected_balance":{"program_id":self.selected_balance.program_id,"opaque_program":self.selected_balance.render(),"policy":self.selected_balance.to_dict()},"local_equations":["D_T<RHO>+D_X<RHO*U>=ZERO","D_T<RHO*U>+D_X<RHO*U*U+P>=ZERO"]}
class ContinuumRuntimeV34:
 def __init__(self,physics):self.physics=physics
 def flux(self,policy,row):
  vals={"RHO":row.rho,"U":row.u,"P":row.p,"ONE":self.physics.one};out=self.physics.zero
  for atom in policy.atoms:
   term=self.physics.one
   for f in atom.factors:term=self.mul(term,vals[f])
   out=self.add(out,term)
  return out
 def balance(self,p,row):
  out=[]
  for i,q in enumerate(row.before):
   l,r=row.interfaces[i],row.interfaces[i+1];l=self.inv(l) if p.left_turn else l;r=self.inv(r) if p.right_turn else r;delta=self.add(l,r)
   for _ in range(p.interval_power):delta=self.mul(delta,row.dt)
   if p.divide_dx:
    delta=self.divide(delta,row.dx)
    if delta is None:return None
   out.append(self.add(q,delta))
  return tuple(out)
 def total(self,row,state):
  out=self.physics.zero
  for q in state:out=self.add(out,self.mul(q,row.dx))
  return out
 def divide(self,v,d):
  d=self.physics.normalize(d)
  if d.negative or d.positive<=0:return None
  b=self.physics.directed.base;return self.physics.normalize(DirectedValueV21(b.omega(v.positive,d.denominator),b.omega(v.negative,d.denominator),b.omega(v.denominator,d.positive)))
 def add(self,a,b):return self.physics.normalize(self.physics.directed.execute_binary(self.physics.combine,a,b))
 def mul(self,a,b):return self.physics.normalize(self.physics.directed.execute_binary(self.physics.interact,a,b))
 def inv(self,v):return self.physics.normalize(self.physics.directed.execute_unary(self.physics.inverse,v))
class ContinuumResearchV34:
 def discover(self,flux_rows:Sequence[FluxObservationV34],balance_rows:Sequence[BalanceObservationV34],rt:ContinuumRuntimeV34):
  mass_atoms=tuple(FluxAtomV34(x) for x in (("RHO",),("U",),("P",),("RHO","U"),("RHO","P"),("U","P")));mass=[FluxPolicyV34((a,)) for a in mass_atoms];mg=[p for p in mass if all(rt.physics.equivalent(rt.flux(p,r),r.targets[0]) for r in flux_rows)]
  if len(mg)!=1:raise RuntimeError(f"mass flux {len(mg)}")
  atoms=(FluxAtomV34(("RHO","U","U")),FluxAtomV34(("P",)),FluxAtomV34(("RHO","U")),FluxAtomV34(("U","U")),FluxAtomV34(("RHO","P")),FluxAtomV34(("ONE",)));mom=[FluxPolicyV34((atoms[i],atoms[j])) for i in range(len(atoms)) for j in range(i+1,len(atoms))];pg=[p for p in mom if all(rt.physics.equivalent(rt.flux(p,r),r.targets[1]) for r in flux_rows)]
  if len(pg)!=1:raise RuntimeError(f"momentum flux {len(pg)}")
  bp=tuple(BalancePolicyV34(l,r,t,x) for l,r,t,x in itertools.product((False,True),(False,True),(0,1),(False,True)));bg=[p for p in bp if all((o:=rt.balance(p,row)) is not None and all(rt.physics.equivalent(a,b) for a,b in zip(o,row.after,strict=True)) for row in balance_rows)]
  if len(bg)!=1:raise RuntimeError(f"balance {len(bg)}")
  return ContinuumDiscoveryV34(len(mass),mg[0],len(mom),pg[0],len(bp),bg[0])
