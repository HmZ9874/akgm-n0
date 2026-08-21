"""Anonymous searches for quotient, norm composition, inverse search, and limits."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Sequence


def _pair(value: Fraction) -> tuple[int, int]:
    exact = Fraction(value)
    return exact.numerator, exact.denominator


def _id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return prefix + hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class QuotientProgram:
    program_id: str
    numerator_term: int
    denominator_term: int
    normalize_sign: bool

    def execute(self, left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
        a, b = left; c, d = right
        if b == 0 or d == 0 or c == 0:
            raise ValueError("undefined pair quotient")
        terms = (a*c, a*d, b*c, b*d, a, b, c, d)
        numerator, denominator = terms[self.numerator_term], terms[self.denominator_term]
        if denominator == 0:
            raise ValueError("zero denominator")
        if self.normalize_sign and denominator < 0:
            numerator, denominator = -numerator, -denominator
        common = math.gcd(abs(numerator), abs(denominator))
        return (0, 1) if numerator == 0 else (numerator // common, denominator // common)

    def to_dict(self) -> dict[str, Any]:
        return {"program_id":self.program_id,"numerator_term":self.numerator_term,"denominator_term":self.denominator_term,"normalize_sign":self.normalize_sign}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuotientProgram":
        program = compile_quotient_program(int(value["numerator_term"]), int(value["denominator_term"]), bool(value["normalize_sign"]))
        if value.get("program_id") != program.program_id: raise ValueError("quotient digest mismatch")
        return program


def compile_quotient_program(numerator_term: int, denominator_term: int, normalize_sign: bool) -> QuotientProgram:
    payload = {"n":numerator_term,"d":denominator_term,"s":normalize_sign}
    return QuotientProgram(_id("Q17-",payload),numerator_term,denominator_term,normalize_sign)


@dataclass(frozen=True, slots=True)
class QuotientExample:
    left: tuple[int,int]; right: tuple[int,int]; expected: tuple[int,int]


class QuotientSearch:
    def search(self, examples: Sequence[QuotientExample]) -> tuple[QuotientProgram,int,int]:
        exact=[]
        for n,d,s in itertools.product(range(8),range(8),(False,True)):
            program=compile_quotient_program(n,d,s)
            try: passed=all(program.execute(e.left,e.right)==e.expected for e in examples)
            except ValueError: passed=False
            if passed: exact.append(program)
        if not exact: raise ValueError("no quotient program")
        exact.sort(key=lambda p:p.program_id)
        return exact[0],128,len(exact)


@dataclass(frozen=True, slots=True)
class BilinearNormProgram:
    program_id: str
    first_coefficients: tuple[int,int,int,int]
    second_coefficients: tuple[int,int,int,int]

    def execute(self, left: tuple[Fraction,Fraction], right: tuple[Fraction,Fraction]) -> tuple[Fraction,Fraction]:
        a,b=map(Fraction,left);c,d=map(Fraction,right); terms=(a*c,a*d,b*c,b*d)
        return (
            sum(Fraction(k)*v for k,v in zip(self.first_coefficients,terms,strict=True)),
            sum(Fraction(k)*v for k,v in zip(self.second_coefficients,terms,strict=True)),
        )

    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"first_coefficients":list(self.first_coefficients),"second_coefficients":list(self.second_coefficients)}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"BilinearNormProgram":
        p=compile_bilinear_program(v["first_coefficients"],v["second_coefficients"])
        if v.get("program_id")!=p.program_id:raise ValueError("bilinear digest mismatch")
        return p


def compile_bilinear_program(first:Sequence[int],second:Sequence[int])->BilinearNormProgram:
    f=tuple(map(int,first));s=tuple(map(int,second));payload={"f":f,"s":s}
    return BilinearNormProgram(_id("N18-",payload),f,s)


@dataclass(frozen=True, slots=True)
class BilinearExample:
    left:tuple[Fraction,Fraction];right:tuple[Fraction,Fraction];expected:tuple[Fraction,Fraction]


class BilinearNormSearch:
    def search(self,examples:Sequence[BilinearExample])->tuple[BilinearNormProgram,int,int]:
        exact=[]
        vectors=tuple(itertools.product((-1,0,1),repeat=4))
        for first in vectors:
            for second in vectors:
                p=compile_bilinear_program(first,second)
                if all(p.execute(e.left,e.right)==e.expected for e in examples):exact.append(p)
        if not exact:raise ValueError("no bilinear composition")
        exact.sort(key=lambda p:(sum(v!=0 for v in p.first_coefficients+p.second_coefficients),p.program_id))
        return exact[0],len(vectors)**2,len(exact)


@dataclass(frozen=True, slots=True)
class InverseSearchProgram:
    program_id:str;seed_mode:int;update_mode:int;stop_mode:int;output_offset:int
    def execute(self,base:int,value:int)->tuple[bool,int]:
        if base<=1 or value<1:return False,0
        current=(0,1,base)[self.seed_mode]; exponent=(0,0,1)[self.seed_mode]
        for _ in range(10000):
            if current==value:return True,exponent+self.output_offset
            if self.stop_mode==0 and current>value:return False,0
            if self.stop_mode==1 and current>=value:return False,0
            if self.update_mode==0:current+=base
            elif self.update_mode==1:current*=base
            elif self.update_mode==2:current+=current
            else:current=current*current if current not in (0,1) else current+base
            exponent+=1
            if abs(current)>10**100:return False,0
        return False,0
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"seed_mode":self.seed_mode,"update_mode":self.update_mode,"stop_mode":self.stop_mode,"output_offset":self.output_offset}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"InverseSearchProgram":
        p=compile_inverse_program(int(v["seed_mode"]),int(v["update_mode"]),int(v["stop_mode"]),int(v["output_offset"]))
        if v.get("program_id")!=p.program_id:raise ValueError("inverse digest mismatch")
        return p


def compile_inverse_program(seed:int,update:int,stop:int,offset:int)->InverseSearchProgram:
    payload={"seed":seed,"update":update,"stop":stop,"offset":offset}
    return InverseSearchProgram(_id("I19-",payload),seed,update,stop,offset)


@dataclass(frozen=True, slots=True)
class InverseExample:
    base:int;value:int;expected_halted:bool;expected_output:int


class InverseSearch:
    def search(self,examples:Sequence[InverseExample])->tuple[InverseSearchProgram,int,int]:
        exact=[]
        for seed,update,stop,offset in itertools.product(range(3),range(4),range(2),(-1,0,1)):
            p=compile_inverse_program(seed,update,stop,offset)
            if all(p.execute(e.base,e.value)==(e.expected_halted,e.expected_output) for e in examples):exact.append(p)
        if not exact:raise ValueError("no inverse search program")
        exact.sort(key=lambda p:p.program_id)
        return exact[0],72,len(exact)


@dataclass(frozen=True, slots=True)
class ContractionLimitProgram:
    program_id:str;limit_mode:int;bound_mode:int
    def execute(self,p:Fraction,q:Fraction,x0:Fraction,steps:int)->tuple[Fraction,Fraction,Fraction]:
        p,q,x0=Fraction(p),Fraction(q),Fraction(x0)
        if abs(p)>=1 or steps<0:raise ValueError("not a certified contraction")
        limits=(q/(1-p),q/(1+p),(q-p)/(1-p),q, p+q)
        limit=limits[self.limit_mode]
        current=x0
        for _ in range(steps):current=p*current+q
        raw=abs(x0-limit)*(abs(p)**steps)
        bounds=(raw,abs(x0-limit)*(abs(p)**max(0,steps-1)),abs(current-limit))
        return limit,current,bounds[self.bound_mode]
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"limit_mode":self.limit_mode,"bound_mode":self.bound_mode}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"ContractionLimitProgram":
        p=compile_contraction_program(int(v["limit_mode"]),int(v["bound_mode"]))
        if v.get("program_id")!=p.program_id:raise ValueError("contraction digest mismatch")
        return p


def compile_contraction_program(limit_mode:int,bound_mode:int)->ContractionLimitProgram:
    payload={"limit":limit_mode,"bound":bound_mode}
    return ContractionLimitProgram(_id("L20-",payload),limit_mode,bound_mode)


@dataclass(frozen=True, slots=True)
class ContractionExample:
    p:Fraction;q:Fraction;x0:Fraction;steps:int;expected:tuple[Fraction,Fraction,Fraction]


class ContractionLimitSearch:
    def search(self,examples:Sequence[ContractionExample])->tuple[ContractionLimitProgram,int,int]:
        exact=[]
        for lm,bm in itertools.product(range(5),range(3)):
            program=compile_contraction_program(lm,bm)
            if all(program.execute(e.p,e.q,e.x0,e.steps)==e.expected for e in examples):exact.append(program)
        if not exact:raise ValueError("no contraction limit certificate")
        exact.sort(key=lambda p:p.program_id)
        return exact[0],15,len(exact)


@dataclass(frozen=True, slots=True)
class FoundationExpansionV8:
    quotient:QuotientProgram;norm_composition:BilinearNormProgram;inverse_search:InverseSearchProgram;contraction_limit:ContractionLimitProgram
    candidate_counts:tuple[int,int,int,int];exact_counts:tuple[int,int,int,int]
    def to_dict(self)->dict[str,Any]:return {"quotient":self.quotient.to_dict(),"norm_composition":self.norm_composition.to_dict(),"inverse_search":self.inverse_search.to_dict(),"contraction_limit":self.contraction_limit.to_dict(),"candidate_counts":list(self.candidate_counts),"exact_counts":list(self.exact_counts)}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"FoundationExpansionV8":return cls(QuotientProgram.from_dict(v["quotient"]),BilinearNormProgram.from_dict(v["norm_composition"]),InverseSearchProgram.from_dict(v["inverse_search"]),ContractionLimitProgram.from_dict(v["contraction_limit"]),tuple(map(int,v["candidate_counts"])),tuple(map(int,v["exact_counts"])))


def discover_foundation_expansion_v8(
    quotient_examples:Sequence[QuotientExample],bilinear_examples:Sequence[BilinearExample],
    inverse_examples:Sequence[InverseExample],contraction_examples:Sequence[ContractionExample],
)->FoundationExpansionV8:
    q,qc,qe=QuotientSearch().search(quotient_examples)
    n,nc,ne=BilinearNormSearch().search(bilinear_examples)
    i,ic,ie=InverseSearch().search(inverse_examples)
    l,lc,le=ContractionLimitSearch().search(contraction_examples)
    return FoundationExpansionV8(q,n,i,l,(qc,nc,ic,lc),(qe,ne,ie,le))
