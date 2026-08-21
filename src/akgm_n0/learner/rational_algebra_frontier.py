"""Anonymous binary rational-pair algebra search for dispersion worlds."""
from __future__ import annotations
import hashlib,itertools,json,math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any,Mapping,Sequence
from .foundation_kernel import FoundationRewardPolicy
NUM_CROSS_SUM=0;NUM_CROSS_DIFF=1;NUM_PRODUCT=2;NUM_DIFF_SQUARE=3;NUM_LEFT=4;NUM_RIGHT=5
DEN_PRODUCT=0;DEN_PRODUCT_SQUARE=1;DEN_LEFT=2;DEN_RIGHT=3;DEN_UNIT=4
@dataclass(frozen=True,slots=True)
class RationalProgram:
    program_id:str;numerator_mode:int;denominator_mode:int;normalize:bool
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"numerator_mode":self.numerator_mode,"denominator_mode":self.denominator_mode,"normalize":self.normalize}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"RationalProgram":return cls(str(v["program_id"]),int(v["numerator_mode"]),int(v["denominator_mode"]),bool(v["normalize"]))
@dataclass(frozen=True,slots=True)
class RationalExample:left:tuple[int,int];right:tuple[int,int];expected:tuple[int,int]
@dataclass(frozen=True,slots=True)
class RationalExecution:halted:bool;output:tuple[int,int];primitive_execution_tokens:int
@dataclass(frozen=True,slots=True)
class RationalCandidate:program:RationalProgram;exact:bool;passed_example_count:int;example_count:int;execution_token_cost:int;program_token_cost:int;total_token_cost:int;reward:int
@dataclass(frozen=True,slots=True)
class RationalSearchReport:task_id:str;candidates_evaluated:int;selected:RationalCandidate;candidates:tuple[RationalCandidate,...]
@dataclass(frozen=True,slots=True)
class RationalAlgebraSemantic:
    semantic_id:str;difference_opcode:int;square_opcode:int;difference_program:RationalProgram;square_program:RationalProgram;dependency_semantic_ids:tuple[str,...];source_task_ids:tuple[str,...];invented_dependency_signature:str
    def to_dict(self)->dict[str,Any]:return {"semantic_id":self.semantic_id,"difference_opcode":self.difference_opcode,"square_opcode":self.square_opcode,"difference_program":self.difference_program.to_dict(),"square_program":self.square_program.to_dict(),"dependency_semantic_ids":list(self.dependency_semantic_ids),"source_task_ids":list(self.source_task_ids),"invented_dependency_signature":self.invented_dependency_signature}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"RationalAlgebraSemantic":return cls(str(v["semantic_id"]),int(v["difference_opcode"]),int(v["square_opcode"]),RationalProgram.from_dict(v["difference_program"]),RationalProgram.from_dict(v["square_program"]),tuple(map(str,v["dependency_semantic_ids"])),tuple(map(str,v["source_task_ids"])),str(v["invented_dependency_signature"]))
class RationalExecutor:
    def execute(self,p:RationalProgram,left:tuple[int,int],right:tuple[int,int])->RationalExecution:
        a,b=left;c,d=right
        if b<=0 or d<=0:return RationalExecution(False,(0,0),1)
        num={NUM_CROSS_SUM:a*d+c*b,NUM_CROSS_DIFF:a*d-c*b,NUM_PRODUCT:a*c,NUM_DIFF_SQUARE:(a*d-c*b)**2,NUM_LEFT:a,NUM_RIGHT:c}[p.numerator_mode]
        den={DEN_PRODUCT:b*d,DEN_PRODUCT_SQUARE:(b*d)**2,DEN_LEFT:b,DEN_RIGHT:d,DEN_UNIT:1}[p.denominator_mode]
        tokens=5+abs(a*d)+abs(c*b)+abs(num)+den
        if p.normalize:
            if num==0:out=(0,1)
            else:g=math.gcd(abs(num),den);out=(num//g,den//g)
            tokens+=2+(1 if num==0 else g)
        else:out=(num,den)
        return RationalExecution(True,out,tokens)
class RationalProgramSearch:
    def search(self,task_id:str,examples:Sequence[RationalExample])->RationalSearchReport:
        cs=[]
        for nm,dm,norm in itertools.product(range(6),range(5),(False,True)):
            p=compile_rational_program(nm,dm,norm);passed=0;tokens=0
            for e in examples:r=RationalExecutor().execute(p,e.left,e.right);tokens+=r.primitive_execution_tokens;passed+=r.halted and r.output==e.expected
            exact=passed==len(examples);total,reward=FoundationRewardPolicy().score(exact=exact,passed_example_count=passed,execution_token_cost=tokens,program_token_cost=4);cs.append(RationalCandidate(p,exact,passed,len(examples),tokens,4,total,reward))
        exact=[x for x in cs if x.exact]
        if not exact:raise ValueError(f"no exact rational algebra program for {task_id}")
        exact.sort(key=lambda x:(-x.reward,x.program.program_id));return RationalSearchReport(task_id,len(cs),exact[0],tuple(cs))
class RationalAlgebraInducer:
    def induce(self,d:RationalSearchReport,s:RationalSearchReport,*,difference_opcode:int,square_opcode:int,dependency_semantic_ids:Sequence[str],invented_dependency_signature:str)->RationalAlgebraSemantic:
        payload={"difference_opcode":difference_opcode,"square_opcode":square_opcode,"difference_program":d.selected.program.program_id,"square_program":s.selected.program.program_id,"dependencies":list(dependency_semantic_ids),"source_tasks":[d.task_id,s.task_id],"invented_dependency_signature":invented_dependency_signature}
        return RationalAlgebraSemantic("ZSEM-"+_h(payload),difference_opcode,square_opcode,d.selected.program,s.selected.program,tuple(dependency_semantic_ids),(d.task_id,s.task_id),invented_dependency_signature)
def compile_rational_program(nm:int,dm:int,norm:bool)->RationalProgram:
    p={"numerator_mode":nm,"denominator_mode":dm,"normalize":norm};return RationalProgram("ZAP-"+_h(p),nm,dm,norm)
def fraction_pair(v:Fraction)->tuple[int,int]:v=Fraction(v);return v.numerator,v.denominator
def _h(p:Any)->str:return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:16]
