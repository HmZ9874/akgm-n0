"""Small free-variable program frontier over the anonymous word machine."""
from __future__ import annotations
import hashlib,json
from .metamachine_gen2 import *

def _assemble(entries,data=()):
 labels={};instructions=[]
 for entry in entries:
  if isinstance(entry,str): labels[entry]=len(instructions)
  else: instructions.append(entry)
 data_addr={name:2*len(instructions)+i for i,name in enumerate(data)}
 words=[]
 for opcode,operand in instructions:
  if isinstance(operand,str): operand=labels[operand] if opcode in (OP_JUMP,OP_JUMP_IF_ZERO,OP_JUMP_IF_NEGATIVE) else data_addr[operand]
  words.extend((opcode,operand))
 return ReflectiveProgram(tuple(words))

def strict_parametric_programs():
 p={}
 p["mul"]=_assemble(((OP_GROW,2),(OP_LOAD_INPUT,1),(OP_STORE_CELL,"c"),(OP_SET,0),(OP_STORE_CELL,"r"),"loop",(OP_LOAD_CELL,"c"),(OP_JUMP_IF_ZERO,"end"),(OP_LOAD_CELL,"r"),(OP_ADD_INPUT,0),(OP_STORE_CELL,"r"),(OP_LOAD_CELL,"c"),(OP_SUB_IMMEDIATE,1),(OP_STORE_CELL,"c"),(OP_JUMP,"loop"),"end",(OP_LOAD_CELL,"r"),(OP_EMIT,0),(OP_HALT,0)),("c","r"))
 p["max"]=_assemble(((OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"right"),(OP_LOAD_INPUT,0),(OP_EMIT,0),(OP_HALT,0),"right",(OP_LOAD_INPUT,1),(OP_EMIT,0),(OP_HALT,0)))
 p["trunc_sub"]=_assemble(((OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"zero"),(OP_EMIT,0),(OP_HALT,0),"zero",(OP_SET,0),(OP_EMIT,0),(OP_HALT,0)))
 p["not_equal"]=_assemble(((OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_ZERO,"false"),(OP_SET,1),(OP_EMIT,0),(OP_HALT,0),"false",(OP_SET,0),(OP_EMIT,0),(OP_HALT,0)))
 p["less_equal"]=_assemble(((OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"true"),(OP_JUMP_IF_ZERO,"true"),(OP_SET,0),(OP_EMIT,0),(OP_HALT,0),"true",(OP_SET,1),(OP_EMIT,0),(OP_HALT,0)))
 p["greater"]=_assemble(((OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"false"),(OP_JUMP_IF_ZERO,"false"),(OP_SET,1),(OP_EMIT,0),(OP_HALT,0),"false",(OP_SET,0),(OP_EMIT,0),(OP_HALT,0)))
 p["greater_equal"]=_assemble(((OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"false"),(OP_SET,1),(OP_EMIT,0),(OP_HALT,0),"false",(OP_SET,0),(OP_EMIT,0),(OP_HALT,0)))
 p["absolute"]=_assemble(((OP_LOAD_INPUT,0),(OP_JUMP_IF_NEGATIVE,"negative"),(OP_EMIT,0),(OP_HALT,0),"negative",(OP_SET,0),(OP_SUB_INPUT,0),(OP_EMIT,0),(OP_HALT,0)))
 p["falling"]=_assemble(((OP_GROW,5),(OP_LOAD_INPUT,1),(OP_STORE_CELL,"outer"),(OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"invalid"),(OP_LOAD_INPUT,0),(OP_STORE_CELL,"factor"),(OP_SET,1),(OP_STORE_CELL,"result"),"outer_loop",(OP_LOAD_CELL,"outer"),(OP_JUMP_IF_ZERO,"end"),(OP_LOAD_CELL,"result"),(OP_STORE_CELL,"inner"),(OP_SET,0),(OP_STORE_CELL,"temp"),"inner_loop",(OP_LOAD_CELL,"inner"),(OP_JUMP_IF_ZERO,"after_inner"),(OP_LOAD_CELL,"temp"),(OP_ADD_CELL,"factor"),(OP_STORE_CELL,"temp"),(OP_LOAD_CELL,"inner"),(OP_SUB_IMMEDIATE,1),(OP_STORE_CELL,"inner"),(OP_JUMP,"inner_loop"),"after_inner",(OP_LOAD_CELL,"temp"),(OP_STORE_CELL,"result"),(OP_LOAD_CELL,"factor"),(OP_SUB_IMMEDIATE,1),(OP_STORE_CELL,"factor"),(OP_LOAD_CELL,"outer"),(OP_SUB_IMMEDIATE,1),(OP_STORE_CELL,"outer"),(OP_JUMP,"outer_loop"),"end",(OP_LOAD_CELL,"result"),(OP_EMIT,0),(OP_HALT,0),"invalid",(OP_SET,0),(OP_EMIT,0),(OP_HALT,0)),("outer","result","factor","inner","temp"))
 p["choose"]=_assemble(((OP_GROW,8),(OP_LOAD_INPUT,1),(OP_STORE_CELL,"outer"),(OP_LOAD_INPUT,0),(OP_SUB_INPUT,1),(OP_JUMP_IF_NEGATIVE,"invalid"),(OP_ADD_IMMEDIATE,1),(OP_STORE_CELL,"factor"),(OP_SET,1),(OP_STORE_CELL,"divisor"),(OP_SET,1),(OP_STORE_CELL,"result"),"outer_loop",(OP_LOAD_CELL,"outer"),(OP_JUMP_IF_ZERO,"end"),(OP_LOAD_CELL,"result"),(OP_STORE_CELL,"inner"),(OP_SET,0),(OP_STORE_CELL,"temp"),"mul_loop",(OP_LOAD_CELL,"inner"),(OP_JUMP_IF_ZERO,"after_mul"),(OP_LOAD_CELL,"temp"),(OP_ADD_CELL,"factor"),(OP_STORE_CELL,"temp"),(OP_LOAD_CELL,"inner"),(OP_SUB_IMMEDIATE,1),(OP_STORE_CELL,"inner"),(OP_JUMP,"mul_loop"),"after_mul",(OP_LOAD_CELL,"temp"),(OP_STORE_CELL,"remainder"),(OP_SET,0),(OP_STORE_CELL,"quotient"),"div_loop",(OP_LOAD_CELL,"remainder"),(OP_SUB_CELL,"divisor"),(OP_JUMP_IF_NEGATIVE,"after_div"),(OP_STORE_CELL,"remainder"),(OP_LOAD_CELL,"quotient"),(OP_ADD_IMMEDIATE,1),(OP_STORE_CELL,"quotient"),(OP_JUMP,"div_loop"),"after_div",(OP_LOAD_CELL,"quotient"),(OP_STORE_CELL,"result"),(OP_LOAD_CELL,"factor"),(OP_ADD_IMMEDIATE,1),(OP_STORE_CELL,"factor"),(OP_LOAD_CELL,"divisor"),(OP_ADD_IMMEDIATE,1),(OP_STORE_CELL,"divisor"),(OP_LOAD_CELL,"outer"),(OP_SUB_IMMEDIATE,1),(OP_STORE_CELL,"outer"),(OP_JUMP,"outer_loop"),"end",(OP_LOAD_CELL,"result"),(OP_EMIT,0),(OP_HALT,0),"invalid",(OP_SET,0),(OP_EMIT,0),(OP_HALT,0)),("outer","result","factor","divisor","inner","temp","remainder","quotient"))
 return p

class StrictParametricFrontierSearch:
 def __init__(self,top_k=100,executor=None): self.top_k=top_k;self.executor=executor or ReflectiveExecutor(maximum_steps=100000);self.catalog=strict_parametric_programs()
 def search(self,observation):
  valid=tuple((r,o) for r,o,v in zip(observation.input_rows,observation.output_values,observation.validity_mask) if v);width=len(valid[0][0]);programs=[]
  for name,program in self.catalog.items():
   if (name=="absolute")==(width==1): programs.append(program)
   if width==2 and name!="absolute": programs.append(program)
  # Distractors preserve the same instruction language but exchange the free inputs.
  originals=tuple(programs)
  for program in originals:
   words=list(program.words)
   for i in range(0,len(words),2):
    if words[i] in (OP_LOAD_INPUT,OP_ADD_INPUT,OP_SUB_INPUT) and words[i+1] in (0,1): words[i+1]=1-words[i+1]
   programs.append(ReflectiveProgram(tuple(words)))
  candidates=[];rejected=0
  for program in programs:
   outputs=[]
   try:
    for row,_ in valid: outputs.append(self.executor.execute(program,row).output_value)
   except InvalidReflectiveProgram: rejected+=1;continue
   errors=tuple(x-float(y) for x,(_,y) in zip(outputs,valid));key=json.dumps(program.to_dict(),sort_keys=True,separators=(",",":"));cid="SP-"+hashlib.sha256(key.encode()).hexdigest()[:16]
   candidates.append(ReflectiveCandidate(cid,program,sum(e*e for e in errors)/len(errors),max(abs(e) for e in errors),tuple(outputs),tuple(outputs)))
  candidates.sort(key=lambda c:(c.fit_error,c.program.instruction_count,c.maximum_absolute_error,c.candidate_id))
  return ReflectiveSearchReport(len(programs),len(candidates),rejected,len({c.outputs for c in candidates}),tuple(candidates[:self.top_k]))
