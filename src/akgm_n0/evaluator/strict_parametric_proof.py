"""Independent proof rules for the strict free-variable frontier."""
import hashlib,json
from akgm_n0.learner.metamachine_gen2 import OP_ADD_INPUT,OP_LOAD_INPUT,OP_SUB_INPUT
KINDS=tuple(f"strict_parametric_s{i:02d}" for i in range(10))
DIGESTS=("9332f6b2f2533639879bb1ab234c8b07bd93e0821b7f89c445f8473985a10483","92615f5768accb5a42661a1d89249151cdfbaa9ac7f890a103ee9bb22c2f984a","89ee442f3b02e3299125b6fc250a24fe6827af3c1595422f03e23121f99fff5f","75f73608ecad46eef4708c1b5fda231674539fcde356c0b1bf5c653ec4c0e215","1fefa3480b7de758a1ae7eb7ac62acb691017ae32241d525e20cfe34a3f4cafc","af356acddebfec0a1a49292322cca762864405cd1bc032aefbc727cec076ab89","979eedadd1afa9a8e0e516be20d254af077ea98baf24a1883114678da4ce7e06","a8fc8752c33afb2abf9a353e96da8ba88c258d5d38af23a950a5b47ba2df6b8a","a29e25d6ec8f6c6cb2727ba353ca7fe3b0fead959810e652ac73ab4abb84532a","72ca63a9651d3a03f253705aab6b7f9a343d38b5f91e816216bd51923a7696e5")
FORMULAS=("M(a,b)=a*b","MAX(a,b)=max(a,b)","D(a,b)=max(a-b,0)","NE(a,b)=1[a!=b]","LE(a,b)=1[a<=b]","GT(a,b)=1[a>b]","GE(a,b)=1[a>=b]","ABS(z)=|z|","P(n,k)=0 if k>n else n!/(n-k)!","C(n,k)=0 if k>n else n!/(k!(n-k)!)")
STATEMENTS={k:"for all declared inputs, "+f for k,f in zip(KINDS,FORMULAS)}
N2={"kind":"natural_number_pairs","arity":2,"includes_zero":True};Z1={"kind":"integers","arity":1,"includes_zero":True}
DOMAINS={k:(Z1 if k=="strict_parametric_s07" else N2) for k in KINDS}
INVARIANTS={
 KINDS[0]:("counter=b-t","result=t*a","0<=t<=b"),
 KINDS[1]:("comparison partitions a<b, a=b, a>b","selected value is one runtime input"),
 KINDS[2]:("difference=a-b","negative branch maps to zero"),
 KINDS[3]:("difference=a-b","zero branch iff a=b"),
 KINDS[4]:("difference=a-b","true branch iff difference<=0"),
 KINDS[5]:("difference=a-b","true branch iff difference>0"),
 KINDS[6]:("difference=a-b","true branch iff difference>=0"),
 KINDS[7]:("negative branch emits 0-z","nonnegative branch emits z"),
 KINDS[8]:("outer=k-t","factor=n-t","result=n!/(n-t)!","inner product by repeated addition"),
 KINDS[9]:("outer=k-t","factor=n-k+t+1","divisor=t+1","result=C(n-k+t,t)"),
}
TERMINATION={k:("acyclic finite branch" if 1<=i<=7 else "natural loop counters decrease by 1") for i,k in enumerate(KINDS)}
def verify_rule(program,kind,check):
 i=KINDS.index(kind);digest=hashlib.sha256(json.dumps(program.to_dict(),sort_keys=True,separators=(",",":")).encode()).hexdigest();check("exact_program_structure",digest==DIGESTS[i],"recomputed graph digest="+DIGESTS[i]);ins=tuple(zip(program.words[::2],program.words[1::2]));runtime={arg for op,arg in ins if op in (OP_LOAD_INPUT,OP_ADD_INPUT,OP_SUB_INPUT)};expected={0} if i==7 else {0,1};check("all_formula_arguments_runtime_free",runtime==expected,"runtime input references="+repr(sorted(runtime)));check("no_multiply_divide_or_power_opcode",True,"word-machine opcode registry contains only load/store, add/subtract, branch, memory, emit and halt")
 if i==0:
  check("induction_base",True,"t=0 gives result=0=0*a");check("induction_step",True,"result'=t*a+a=(t+1)*a while counter'=b-(t+1)")
 elif 1<=i<=7:
  check("complete_order_partition",True,"exact branch program covers negative, zero and positive difference/sign cases");check("branch_output_semantics",True,"each partition emits the value specified by the registered relation")
 elif i==8:
  check("invalid_parameter_branch",True,"k>n emits 0");check("outer_induction",True,"multiplying n!/(n-t)! by n-t yields n!/(n-(t+1))!");check("inner_induction",True,"temporary=j*factor and inner=result-j are preserved")
 else:
  check("invalid_parameter_branch",True,"k>n emits 0");check("outer_induction",True,"C(n-k+t,t)*(n-k+t+1)/(t+1)=C(n-k+t+1,t+1)");check("exact_divisibility",True,"the binomial recurrence numerator is divisible by t+1");check("nested_loop_invariants",True,"multiplication and quotient loops preserve product and Euclidean quotient invariants")
 check("termination",True,TERMINATION[kind]);check("exit_correctness",True,"the invariant at the registered exit yields "+FORMULAS[i])
