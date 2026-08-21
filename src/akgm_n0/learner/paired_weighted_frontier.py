from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any,Mapping,Sequence
from .foundation_kernel import FoundationRewardPolicy
TERM_PRODUCT=0;TERM_LEFT=1;TERM_RIGHT=2;TERM_SUM=3
DEN_WEIGHTS=0;DEN_RECORDS=1;DEN_UNIT=2
@dataclass(frozen=True,slots=True)
class PairedProgram:
    program_id:str;term_mode:int;denominator_mode:int;normalize:bool
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"term_mode":self.term_mode,"denominator_mode":self.denominator_mode,"normalize":self.normalize}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"PairedProgram":return cls(str(v["program_id"]),int(v["term_mode"]),int(v["denominator_mode"]),bool(v["normalize"]))
@dataclass(frozen=True,slots=True)
class PairedExample:records:tuple[tuple[tuple[int,int],tuple[int,int],int],...];expected:tuple[int,int]
@dataclass(frozen=True,slots=True)
class PairedExecution:halted:bool;output:tuple[int,int];primitive_execution_tokens:int
@dataclass(frozen=True,slots=True)
class PairedCandidate:program:PairedProgram;exact:bool;passed_example_count:int;example_count:int;execution_token_cost:int;program_token_cost:int;total_token_cost:int;reward:int
@dataclass(frozen=True,slots=True)
class PairedSearchReport:task_id:str;candidates_evaluated:int;selected:PairedCandidate;candidates:tuple[PairedCandidate,...]
@dataclass(frozen=True,slots=True)
class PairedWeightedSemantic:
    semantic_id:str;opcode:int;program:PairedProgram;dependency_semantic_ids:tuple[str,...];source_task_ids:tuple[str,...];invented_dependency_signature:str
    def to_dict(self)->dict[str,Any]:return {"semantic_id":self.semantic_id,"opcode":self.opcode,"program":self.program.to_dict(),"dependency_semantic_ids":list(self.dependency_semantic_ids),"source_task_ids":list(self.source_task_ids),"invented_dependency_signature":self.invented_dependency_signature}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"PairedWeightedSemantic":return cls(str(v["semantic_id"]),int(v["opcode"]),PairedProgram.from_dict(v["program"]),tuple(map(str,v["dependency_semantic_ids"])),tuple(map(str,v["source_task_ids"])),str(v["invented_dependency_signature"]))
class PairedExecutor:
    def execute(self,p:PairedProgram,records:Sequence[tuple[tuple[int,int],tuple[int,int],int]])->PairedExecution:
        if not records or any(w<=0 or x[1]<=0 or y[1]<=0 for x,y,w in records):return PairedExecution(False,(0,0),1)
        terms=[]
        for x,y,w in records:
            xf,yf=Fraction(*x),Fraction(*y);term={TERM_PRODUCT:xf*yf,TERM_LEFT:xf,TERM_RIGHT:yf,TERM_SUM:xf+yf}[p.term_mode];terms.append(term*w)
        den={DEN_WEIGHTS:sum(w for _,_,w in records),DEN_RECORDS:len(records),DEN_UNIT:1}[p.denominator_mode];value=sum(terms,Fraction(0))/den
        out=(value.numerator,value.denominator) if p.normalize else (sum(t.numerator for t in terms),den)
        tokens=5+sum(abs(t.numerator)+t.denominator for t in terms)+den
        return PairedExecution(True,out,tokens)
class PairedWeightedSearch:
    def search(self,task_id:str,examples:Sequence[PairedExample])->PairedSearchReport:
        cs=[]
        for tm,dm,norm in itertools.product(range(4),range(3),(False,True)):
            p=compile_paired_program(tm,dm,norm);passed=0;tokens=0
            for e in examples:r=PairedExecutor().execute(p,e.records);tokens+=r.primitive_execution_tokens;passed+=r.halted and r.output==e.expected
            exact=passed==len(examples);total,reward=FoundationRewardPolicy().score(exact=exact,passed_example_count=passed,execution_token_cost=tokens,program_token_cost=4);cs.append(PairedCandidate(p,exact,passed,len(examples),tokens,4,total,reward))
        exact=[x for x in cs if x.exact]
        if not exact:raise ValueError(f"no exact paired accumulator for {task_id}")
        exact.sort(key=lambda x:(-x.reward,x.program.program_id));return PairedSearchReport(task_id,len(cs),exact[0],tuple(cs))
class PairedWeightedInducer:
    def induce(self,r:PairedSearchReport,*,opcode:int,dependency_semantic_ids:Sequence[str],invented_dependency_signature:str)->PairedWeightedSemantic:
        payload={"opcode":opcode,"program_id":r.selected.program.program_id,"dependencies":list(dependency_semantic_ids),"source_tasks":[r.task_id],"invented_dependency_signature":invented_dependency_signature}
        return PairedWeightedSemantic("BSEM-"+_h(payload),opcode,r.selected.program,tuple(dependency_semantic_ids),(r.task_id,),invented_dependency_signature)
def compile_paired_program(tm:int,dm:int,norm:bool)->PairedProgram:
    p={"term_mode":tm,"denominator_mode":dm,"normalize":norm};return PairedProgram("BAP-"+_h(p),tm,dm,norm)
def paired_center(records:Sequence[tuple[tuple[int,int],tuple[int,int],int]])->tuple[int,int]:
    total=sum(w for _,_,w in records);v=sum((Fraction(*x)*Fraction(*y)*w for x,y,w in records),Fraction(0))/total;return v.numerator,v.denominator
def _h(p:Any)->str:return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:16]
