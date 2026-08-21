"""Anonymous searches for a two-dimensional linear-transformation substrate."""
from __future__ import annotations
import hashlib,itertools,json
from dataclasses import dataclass
from fractions import Fraction
from typing import Any,Mapping,Sequence

Matrix=tuple[Fraction,Fraction,Fraction,Fraction]
def _matrix(values:Sequence[int|Fraction])->Matrix:return tuple(map(Fraction,values))  # type: ignore[return-value]
def _transpose(m:Matrix)->Matrix:return m[0],m[2],m[1],m[3]
def _id(prefix:str,payload:Any)->str:return prefix+hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()[:16]

@dataclass(frozen=True,slots=True)
class ContractionProgram:
    program_id:str;swap_operands:bool;transpose_left:bool;transpose_right:bool;transpose_output:bool;second_term_sign:int
    def execute(self,left:Matrix,right:Matrix)->Matrix:
        a,b=(_matrix(right),_matrix(left)) if self.swap_operands else (_matrix(left),_matrix(right))
        if self.transpose_left:a=_transpose(a)
        if self.transpose_right:b=_transpose(b)
        out=[]
        for row in range(2):
            for column in range(2):out.append(a[row*2]*b[column]+self.second_term_sign*a[row*2+1]*b[2+column])
        result=_matrix(out);return _transpose(result) if self.transpose_output else result
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"swap_operands":self.swap_operands,"transpose_left":self.transpose_left,"transpose_right":self.transpose_right,"transpose_output":self.transpose_output,"second_term_sign":self.second_term_sign}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"ContractionProgram":
        p=compile_contraction(bool(v["swap_operands"]),bool(v["transpose_left"]),bool(v["transpose_right"]),bool(v["transpose_output"]),int(v["second_term_sign"]));
        if v.get("program_id")!=p.program_id:raise ValueError("contraction digest mismatch")
        return p
def compile_contraction(swap:bool,tl:bool,tr:bool,to:bool,sign:int)->ContractionProgram:
    if sign not in (-1,1):raise ValueError("invalid contraction sign")
    p={"s":swap,"tl":tl,"tr":tr,"to":to,"s2":sign};return ContractionProgram(_id("LA21-",p),swap,tl,tr,to,sign)

@dataclass(frozen=True,slots=True)
class DeterminantProgram:
    program_id:str;left_term:tuple[int,int];right_term:tuple[int,int];right_sign:int
    def execute(self,matrix:Matrix)->Fraction:
        m=_matrix(matrix);return m[self.left_term[0]]*m[self.left_term[1]]+self.right_sign*m[self.right_term[0]]*m[self.right_term[1]]
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"left_term":list(self.left_term),"right_term":list(self.right_term),"right_sign":self.right_sign}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"DeterminantProgram":
        p=compile_determinant(v["left_term"],v["right_term"],int(v["right_sign"]));
        if v.get("program_id")!=p.program_id:raise ValueError("determinant digest mismatch")
        return p
def compile_determinant(left:Sequence[int],right:Sequence[int],sign:int)->DeterminantProgram:
    l=tuple(map(int,left));r=tuple(map(int,right));p={"l":l,"r":r,"s":sign};return DeterminantProgram(_id("LA22-",p),l,r,sign)  # type: ignore[arg-type]

@dataclass(frozen=True,slots=True)
class InverseProgram:
    program_id:str;permutation:tuple[int,int,int,int];signs:tuple[int,int,int,int]
    def execute(self,matrix:Matrix,determinant:DeterminantProgram)->Matrix:
        m=_matrix(matrix);det=determinant.execute(m)
        if det==0:raise ValueError("singular transformation")
        return _matrix(tuple(self.signs[i]*m[self.permutation[i]]/det for i in range(4)))
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"permutation":list(self.permutation),"signs":list(self.signs)}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"InverseProgram":
        p=compile_inverse(v["permutation"],v["signs"])
        if v.get("program_id")!=p.program_id:raise ValueError("inverse digest mismatch")
        return p
def compile_inverse(permutation:Sequence[int],signs:Sequence[int])->InverseProgram:
    p=tuple(map(int,permutation));s=tuple(map(int,signs));payload={"p":p,"s":s};return InverseProgram(_id("LA23-",payload),p,s)  # type: ignore[arg-type]

@dataclass(frozen=True,slots=True)
class CharacteristicReductionProgram:
    program_id:str;trace_coefficient:int;determinant_coefficient:int
    def execute(self,matrix:Matrix,composition:ContractionProgram,determinant:DeterminantProgram)->Matrix:
        m=_matrix(matrix);square=composition.execute(m,m);trace=m[0]+m[3];det=determinant.execute(m)
        return _matrix((square[0]+self.trace_coefficient*trace*m[0]+self.determinant_coefficient*det,square[1]+self.trace_coefficient*trace*m[1],square[2]+self.trace_coefficient*trace*m[2],square[3]+self.trace_coefficient*trace*m[3]+self.determinant_coefficient*det))
    def to_dict(self)->dict[str,Any]:return {"program_id":self.program_id,"trace_coefficient":self.trace_coefficient,"determinant_coefficient":self.determinant_coefficient}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"CharacteristicReductionProgram":
        p=compile_characteristic(int(v["trace_coefficient"]),int(v["determinant_coefficient"]));
        if v.get("program_id")!=p.program_id:raise ValueError("characteristic digest mismatch")
        return p
def compile_characteristic(trace_coefficient:int,determinant_coefficient:int)->CharacteristicReductionProgram:
    p={"t":trace_coefficient,"d":determinant_coefficient};return CharacteristicReductionProgram(_id("LA24-",p),trace_coefficient,determinant_coefficient)

@dataclass(frozen=True,slots=True)
class MatrixCompositionExample:left:Matrix;right:Matrix;expected:Matrix
@dataclass(frozen=True,slots=True)
class DeterminantExample:matrix:Matrix;expected:Fraction
@dataclass(frozen=True,slots=True)
class InverseExample:matrix:Matrix;expected:Matrix

class LinearAlgebraSearch:
    def discover(self,composition_examples:Sequence[MatrixCompositionExample],determinant_examples:Sequence[DeterminantExample],inverse_examples:Sequence[InverseExample],characteristic_examples:Sequence[Matrix])->"LinearAlgebraFoundationV9":
        contractions=[]
        for values in itertools.product((False,True),repeat=4):
            for sign in (-1,1):
                p=compile_contraction(*values,sign)
                if all(p.execute(e.left,e.right)==e.expected for e in composition_examples):contractions.append(p)
        if not contractions:raise ValueError("no exact contraction")
        contractions.sort(key=lambda p:p.program_id);composition=contractions[0]
        terms=tuple(itertools.combinations_with_replacement(range(4),2));determinants=[]
        for left,right,sign in itertools.product(terms,terms,(-1,1)):
            p=compile_determinant(left,right,sign)
            if all(p.execute(e.matrix)==e.expected for e in determinant_examples):determinants.append(p)
        if not determinants:raise ValueError("no exact invariant")
        determinants.sort(key=lambda p:p.program_id);determinant=determinants[0]
        inverses=[]
        for permutation in itertools.permutations(range(4)):
            for signs in itertools.product((-1,1),repeat=4):
                p=compile_inverse(permutation,signs)
                try:valid=all(p.execute(e.matrix,determinant)==e.expected for e in inverse_examples)
                except ValueError:valid=False
                if valid:inverses.append(p)
        if not inverses:raise ValueError("no exact inverse")
        inverses.sort(key=lambda p:p.program_id);inverse=inverses[0]
        reductions=[]
        for tc,dc in itertools.product(range(-2,3),repeat=2):
            p=compile_characteristic(tc,dc)
            if all(p.execute(m,composition,determinant)==_matrix((0,0,0,0)) for m in characteristic_examples):reductions.append(p)
        if not reductions:raise ValueError("no characteristic reduction")
        reductions.sort(key=lambda p:p.program_id);reduction=reductions[0]
        return LinearAlgebraFoundationV9(composition,determinant,inverse,reduction,(32,len(terms)**2*2,384,25),(len(contractions),len(determinants),len(inverses),len(reductions)))

@dataclass(frozen=True,slots=True)
class LinearAlgebraFoundationV9:
    composition:ContractionProgram;determinant:DeterminantProgram;inverse:InverseProgram;characteristic_reduction:CharacteristicReductionProgram;candidate_counts:tuple[int,int,int,int];exact_counts:tuple[int,int,int,int]
    def to_dict(self)->dict[str,Any]:return {"composition":self.composition.to_dict(),"determinant":self.determinant.to_dict(),"inverse":self.inverse.to_dict(),"characteristic_reduction":self.characteristic_reduction.to_dict(),"candidate_counts":list(self.candidate_counts),"exact_counts":list(self.exact_counts)}
    @classmethod
    def from_dict(cls,v:Mapping[str,Any])->"LinearAlgebraFoundationV9":return cls(ContractionProgram.from_dict(v["composition"]),DeterminantProgram.from_dict(v["determinant"]),InverseProgram.from_dict(v["inverse"]),CharacteristicReductionProgram.from_dict(v["characteristic_reduction"]),tuple(map(int,v["candidate_counts"])),tuple(map(int,v["exact_counts"])))
