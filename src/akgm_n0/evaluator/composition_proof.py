"""Compositional total-correctness rules over previously proven operations."""
import hashlib,json
KINDS=tuple(f"composition20_c{i:02d}" for i in range(20))
DIGESTS=("63a3c7a592321402bed14497c0c00685c989d5640e2a87f1d4d589b9c9d3eb7f","ab1941e8c5f4e746513206a9ae2ce027dab35152a610f8aeb3a517094c7ebce5","740448f0bdf6f08be14122a84b1b62390e160a2879430d305c0fb7c79a4e8860","d71fd2cd55f653dd65e25df22d63d38ef95d9e033dcb2c4ebda332a5110e0b45","5ae2212fb006b803c72ae67677b7a1b1858560884732ef587f8d4ddcf1dcb6c7","1a19c3bdee337e03f541f005a6897892a4901d18aa501ba48b807b4b004e04c4","1ca92b0baabe0b55a8be644c6b728680d7a44e3dcc9fc94f9cb42fd1545633db","c3512dd01363349e5e77eea6e3bf898c084201e5a2b783fa78fb23d19dbef60d","e243f65d84f6db1dc998ae68848e0c9e4f9c8f8e1d2f04ef1001e660cf11a7b5","ca17e1ccfe534736a8539d2ffb4352176df11b0b00fe23d98ebcd7bc27be3f3e","63437f7bcb3e0738fb3152ca31e5b4266e1f1134211ad06eda0f831ebd4105a6","d2d6dae50a8a2702aebb3af7e2dff5bed4f90deeed4d1a5383425c120fa71dce","e600e470260f546bec8cf6b9305fef399fd428e0fa734ebdd714afeeed7191a0","0ce304a70ceb3732fa652200a1a816db6f605acb81d929f06b50fdbba31a9781","95bacec65fd495fec688129b7739e53fe852fc28312313234362813f85018690","a75a68b6b1adaa4307875bd533ed44c87ec5054be28de0046e5e568a5d7bec40","6576eebf679d0b931856328e9eff0faac6d1d192e7ff7360e7d4e8d3415651ab","11f5abd396436aaa504ee7023dd1f0281021786a22869e865fd3c8451ac7c909","a8fb1cc3e53aed5fe3c050eb5b3310b2cc03dc10cb3c42bbd6238d1b61fa9f00","82d127038bfcec8be59a0366f09ec692cc1a278217bafad1719358207237e126")
FORMULAS=("(3^n)^2","(2^n)^3","bit_length(n^3)","bit_length(n)^2","floor(sqrt(n^3))","floor(sqrt(n))^3","C(n^2,3)","C(n,3)^2","C(bit_length(n),4)","n^3 mod 4","C(n,4) mod 3","floor(n^2/3)","ternary_length(n^2)","2^(n mod 3)","3^(n mod 4)","abs(3^n-2^n)","1[n mod 3 = n mod 4]","1[n mod 4 < n mod 3]","abs(C(n,5)-C(n,4))","min(C(n,3),C(n,4))")
STATEMENTS={k:f"for every n in N, output(n)={f}" for k,f in zip(KINDS,FORMULAS)}
DOMAIN={"kind":"natural_numbers","arity":1,"includes_zero":True}
DOMAINS={k:DOMAIN for k in KINDS}
INVARIANTS={k:("every node equals its previously proven component applied to its declared arguments","node references form a forward acyclic graph") for k in KINDS}
TERMINATION={k:"finite acyclic composition of total previously proven operations" for k in KINDS}

COMPONENTS={
 "G2NEW-4f6b5de649cfa951":(1,"pow2"),"G4NEW-1914cf632033656b":(1,"pow3"),
 "G4NEW-56569b1d93a9c4c9":(1,"cube"),"G3NEW-2d402424e2bb97f1":(1,"square"),
 "G3NEW-5682429236b9b26a":(1,"bit_length"),"G2CTRL-de057ef1810f4943":(1,"floor_sqrt"),
 "G2CTRL-aa1ab30803291692":(1,"choose3"),"G3NEW-98a7cc88ec88ae78":(1,"choose4"),
 "G4NEW-6197e8bd097a8d4b":(1,"choose5"),"G4NEW-b074e6fff182dcc2":(1,"mod3"),
 "G2CTRL-f5ffb2c49416a134":(1,"mod4"),"G4NEW-9d4c8b094b2250a5":(1,"floor3"),
 "G4NEW-ba41949ee04c20cb":(1,"ternary_length"),"G4NEW-6d032c98e59a7ab9":(2,"minimum"),
 "G4NEW-687cca22ba6069f5":(2,"absolute_difference"),"G4NEW-4f8ce015861a67a4":(2,"equal"),
 "G4NEW-f9e488fd9f8130c6":(2,"less_than"),
}

N=("input",0)
def _node(operator,*arguments):
 if operator in {"minimum","absolute_difference","equal"}:
  arguments=tuple(sorted(arguments,key=repr))
 return (operator,)+tuple(arguments)

EXPECTED=(
 _node("square",_node("pow3",N)),_node("cube",_node("pow2",N)),
 _node("bit_length",_node("cube",N)),_node("square",_node("bit_length",N)),
 _node("floor_sqrt",_node("cube",N)),_node("cube",_node("floor_sqrt",N)),
 _node("choose3",_node("square",N)),_node("square",_node("choose3",N)),
 _node("choose4",_node("bit_length",N)),_node("mod4",_node("cube",N)),
 _node("mod3",_node("choose4",N)),_node("floor3",_node("square",N)),
 _node("ternary_length",_node("square",N)),_node("pow2",_node("mod3",N)),
 _node("pow3",_node("mod4",N)),_node("absolute_difference",_node("pow3",N),_node("pow2",N)),
 _node("equal",_node("mod3",N),_node("mod4",N)),_node("less_than",_node("mod4",N),_node("mod3",N)),
 _node("absolute_difference",_node("choose5",N),_node("choose4",N)),
 _node("minimum",_node("choose3",N),_node("choose4",N)),
)

def _decode(program):
 expressions=[]
 for index,node in enumerate(program.nodes):
  component=COMPONENTS.get(node.operation_id)
  if component is None or component[0] != len(node.arguments): return None
  arguments=[]
  for reference in node.arguments:
   try: kind,raw=reference.split(":",1); position=int(raw)
   except (ValueError,AttributeError): return None
   if kind=="input" and position==0: arguments.append(N)
   elif kind=="node" and 0<=position<index: arguments.append(expressions[position])
   else: return None
  expressions.append(_node(component[1],*arguments))
 return expressions[-1] if expressions else None

def verify_rule(program,kind,check):
 idx=KINDS.index(kind);encoded=json.dumps(program.to_dict(),sort_keys=True,separators=(",",":")).encode()
 check("exact_composition_graph",hashlib.sha256(encoded).hexdigest()==DIGESTS[idx],f"graph sha256={DIGESTS[idx]}")
 nodes=getattr(program,"nodes",())
 expression=_decode(program) if nodes else None
 valid=expression is not None
 check("acyclic_reference_check",valid,"every node reference points to an earlier node")
 check("proven_component_substitution",valid,"substitute each component's prior universal theorem into the graph")
 check("domain_closure",valid,"each intermediate value remains in the declared natural-number component domain")
 check("termination",valid,"a finite DAG of total component calls is total")
 check("exit_correctness",expression==EXPECTED[idx],f"symbolic substitution yields {FORMULAS[idx]}")
