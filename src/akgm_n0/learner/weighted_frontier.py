"""Anonymous weighted-accumulation search over finite outcome records."""
from __future__ import annotations
import hashlib,itertools,json,math
from dataclasses import dataclass
from typing import Any,Mapping,Sequence
from .foundation_kernel import FoundationRewardPolicy

TERM_VALUES=0;TERM_WEIGHTS=1;TERM_VALUE_WEIGHT=2;TERM_LAST_VALUE=3
DEN_UNIT=0;DEN_RECORDS=1;DEN_WEIGHTS=2;DEN_VALUES=3

@dataclass(frozen=True,slots=True)
class WeightedProgram:
    program_id:str;term_mode:int;denominator_mode:int;normalize:bool
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"term_mode":self.term_mode,"denominator_mode":self.denominator_mode,"normalize":self.normalize}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"WeightedProgram":return cls(str(v["program_id"]),int(v["term_mode"]),int(v["denominator_mode"]),bool(v["normalize"]))
@dataclass(frozen=True,slots=True)
class WeightedExample: records:tuple[tuple[int,int],...];expected_pair:tuple[int,int]
@dataclass(frozen=True,slots=True)
class WeightedExecution: halted:bool;output_pair:tuple[int,int];primitive_execution_tokens:int;accumulation_tokens:int
@dataclass(frozen=True,slots=True)
class WeightedCandidate:
    program:WeightedProgram;exact:bool;passed_example_count:int;example_count:int;execution_token_cost:int;program_token_cost:int;total_token_cost:int;reward:int
@dataclass(frozen=True,slots=True)
class WeightedSearchReport: task_id:str;candidates_evaluated:int;selected:WeightedCandidate;candidates:tuple[WeightedCandidate,...]
@dataclass(frozen=True,slots=True)
class WeightedFoundationSemantic:
    semantic_id:str;opcode:int;program:WeightedProgram;dependency_semantic_ids:tuple[str,...];source_task_ids:tuple[str,...];invented_dependency_signature:str
    def to_dict(self)->dict[str,Any]:return {"semantic_id":self.semantic_id,"opcode":self.opcode,"program":self.program.to_dict(),"dependency_semantic_ids":list(self.dependency_semantic_ids),"source_task_ids":list(self.source_task_ids),"invented_dependency_signature":self.invented_dependency_signature}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"WeightedFoundationSemantic":return cls(str(v["semantic_id"]),int(v["opcode"]),WeightedProgram.from_dict(v["program"]),tuple(map(str,v["dependency_semantic_ids"])),tuple(map(str,v["source_task_ids"])),str(v["invented_dependency_signature"]))

class WeightedExecutor:
    def execute(self,p:WeightedProgram,records:Sequence[tuple[int,int]])->WeightedExecution:
        if not records or any(value<0 or weight<=0 for value,weight in records):return WeightedExecution(False,(0,0),1,0)
        values=[x for x,_ in records];weights=[w for _,w in records]
        numerator={TERM_VALUES:sum(values),TERM_WEIGHTS:sum(weights),TERM_VALUE_WEIGHT:sum(x*w for x,w in records),TERM_LAST_VALUE:values[-1]}[p.term_mode]
        denominator={DEN_UNIT:1,DEN_RECORDS:len(records),DEN_WEIGHTS:sum(weights),DEN_VALUES:sum(values)}[p.denominator_mode]
        if denominator<=0:return WeightedExecution(False,(0,0),2,0)
        accumulation=sum((x*w if p.term_mode==TERM_VALUE_WEIGHT else x) for x,w in records)
        tokens=3+len(records)+accumulation+denominator
        if p.normalize:
            g=math.gcd(numerator,denominator);pair=(0,1) if numerator==0 else (numerator//g,denominator//g);tokens+=g+2
        else:pair=(numerator,denominator)
        return WeightedExecution(True,pair,tokens,accumulation)

class WeightedAccumulatorSearch:
    def search(self,task_id:str,examples:Sequence[WeightedExample])->WeightedSearchReport:
        candidates=[]
        for tm,dm,norm in itertools.product(range(4),range(4),(False,True)):
            p=compile_weighted_program(tm,dm,norm);passed=0;tokens=0
            for e in examples:
                r=WeightedExecutor().execute(p,e.records);tokens+=r.primitive_execution_tokens;passed+=r.halted and r.output_pair==e.expected_pair
            exact=passed==len(examples);total,reward=FoundationRewardPolicy().score(exact=exact,passed_example_count=passed,execution_token_cost=tokens,program_token_cost=4)
            candidates.append(WeightedCandidate(p,exact,passed,len(examples),tokens,4,total,reward))
        exact=[x for x in candidates if x.exact]
        if not exact:raise ValueError(f"no exact weighted accumulator for {task_id}")
        exact.sort(key=lambda x:(-x.reward,x.program.program_id));return WeightedSearchReport(task_id,len(candidates),exact[0],tuple(candidates))

class WeightedSemanticInducer:
    def induce(self,report:WeightedSearchReport,*,opcode:int,dependency_semantic_ids:Sequence[str],invented_dependency_signature:str)->WeightedFoundationSemantic:
        payload={"opcode":opcode,"program_id":report.selected.program.program_id,"dependencies":list(dependency_semantic_ids),"source_tasks":[report.task_id],"invented_dependency_signature":invented_dependency_signature}
        return WeightedFoundationSemantic("WSEM-"+_d(payload),opcode,report.selected.program,tuple(dependency_semantic_ids),(report.task_id,),invented_dependency_signature)

def compile_weighted_program(tm:int,dm:int,norm:bool)->WeightedProgram:
    payload={"term_mode":tm,"denominator_mode":dm,"normalize":norm};return WeightedProgram("WAP-"+_d(payload),tm,dm,norm)
def weighted_center(records:Sequence[tuple[int,int]])->tuple[int,int]:
    num=sum(x*w for x,w in records);den=sum(w for _,w in records)
    if den<=0:raise ValueError("positive total weight required")
    if num==0:return (0,1)
    g=math.gcd(num,den);return num//g,den//g
def _d(p:Any)->str:return hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:16]
