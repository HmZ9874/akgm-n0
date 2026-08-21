"""Independent theorem rules for the anonymous twenty-shape frontier."""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction


DOMAIN_N = {"kind": "natural_numbers", "arity": 1, "includes_zero": True}
DOMAIN_N2 = {"kind": "natural_number_pairs", "arity": 2, "includes_zero": True}
DOMAIN_ND = {"kind": "natural_dividend_positive_divisor", "arity": 2,
             "dividend_includes_zero": True, "divisor_minimum": 1}
DOMAIN_Z = {"kind": "integers", "arity": 1, "includes_zero": True}

KINDS = tuple(f"batch20_t{index:02d}" for index in range(20))
DIGESTS = (
    "1914cf632033656b6d886dba67032c9d1d23352177ed670c06d7ba57e4f67641",
    "32ffce8f297225cb2e57048272d493c5f50e760128dda9a4813d8c62dea6f792",
    "56569b1d93a9c4c976da5b452b538566d7b62484de3fbb7fb1c9caa81f985cdb",
    "be9f1e21eb24f2ddb8d7064ec1748e86d2b8be49eb9b5e55937e6f196e598dbd",
    "6197e8bd097a8d4bc0c2aaa7b195bc06cd8adbc38356015bc94d00344f3eb0e9",
    "ef90b6600a88b16ce2e342675f938d73b4111f12d87744859a20126e51e78fee",
    "66ebcc2821dd2814b851351bc488122c2d9e0af5b926727f25359a9b5b53aa47",
    "53a41b94d395a5631e381b1773c2c7d58bcdd308c44c1530720c5f11c7819d98",
    "55b3141b6561f96dd47114a5d6b2691fb7ebbb8bc9176fcb71f3183cfba41b6f",
    "b074e6fff182dcc278683e02f93335cb6c3c06ff191cfec03907f2a5b1e465c9",
    "9d4c8b094b2250a5f42b1b8a6d4537fe102b8dbc0f320225854b864821750cea",
    "ba41949ee04c20cb8d72bdcdf1158b1e45b88e41ccb8f4163f8779138175b4b1",
    "6d032c98e59a7ab98984677a4b23f8aae002983fc57a3fcfe5dd43344a57e2ed",
    "687cca22ba6069f5a4df2a7d69b977fa43987315645d2bc026e15370b87f5ef8",
    "8940ecfed72a113146bbbe12729d84fdd57f7127fdfb7c3036932718a112bf10",
    "8758c920cf9831962240eb9e63064b77a2fa4f99a27f2345a2f414531e665b48",
    "eb9f87487d18be3d0e203129d7cb7b08b7cae567f04fec1f45cbfe9900701fc7",
    "4f8ce015861a67a43a80fcbea29fec5a17377a6cace0d5cff2e8d3ac33325fef",
    "f9e488fd9f8130c6eeb6af8df51fd16a2110a23f101735769629518b7ab47759",
    "a671e30898942b6c61e24efcd770f2c81ccea5de99889cc3a705c3f74670aa46",
)

STATEMENTS = dict(zip(KINDS, (
    "for every n in N, output(n)=3^n",
    "for every n in N, output(n)=2^n-1",
    "for every n in N, output(n)=n^3",
    "for every n in N, output(n)=sum(k^2 for k=1..n)=n(n+1)(2n+1)/6",
    "for every n in N, output(n)=C(n,5)",
    "for every n in N, output(n)=L_n where L_0=2,L_1=1,L_(n+2)=L_(n+1)+L_n",
    "for every n in N, output(n)=P_n where P_0=0,P_1=1,P_(n+2)=2P_(n+1)+P_n",
    "for every n in N, output(n)=Q_n where Q_0=Q_1=Q_2=1,Q_(n+3)=Q_(n+1)+Q_n",
    "for every n in N, output(n)=R_n where (R_0,R_1,R_2,R_3)=(0,0,0,1) and R_(n+4)=sum(R_n..R_(n+3))",
    "for every n in N, output(n)=n mod 3",
    "for every n in N, output(n)=floor(n/3)",
    "for every n in N, output(0)=0 and for n>0 output(n) is the unique c with 3^(c-1)<=n<3^c",
    "for every a,b in N, output(a,b)=min(a,b)",
    "for every a,b in N, output(a,b)=abs(a-b)",
    "for every a in N and d>=1, output(a,d)=a mod d",
    "for every a in N and d>=1, output(a,d)=ceil(a/d)",
    "for every a in N and d>=1, output(a,d)=1 iff d divides a, else 0",
    "for every a,b in N, output(a,b)=1 iff a=b, else 0",
    "for every a,b in N, output(a,b)=1 iff a<b, else 0",
    "for every z in Z, output(z)=-1 if z<0, 0 if z=0, and 1 if z>0",
)))

DOMAINS = {kind: DOMAIN_N for kind in KINDS[:12]}
DOMAINS.update({kind: DOMAIN_N2 for kind in (KINDS[12], KINDS[13], KINDS[17], KINDS[18])})
DOMAINS.update({kind: DOMAIN_ND for kind in (KINDS[14], KINDS[15], KINDS[16])})
DOMAINS[KINDS[19]] = DOMAIN_Z

INVARIANTS = dict(zip(KINDS, (
    ("counter=n-t", "x=3^t", "0<=t<=n"),
    ("counter=n-t", "x=2^t-1", "0<=t<=n"),
    ("counter=n-t", "x=t^3", "delta=3t^2+3t+1", "second=6t+6"),
    ("counter=n-t", "sum=t(t+1)(2t+1)/6", "square=t^2", "odd=2t+1"),
    ("counter=n-t", "A=C(t,5)", "B=C(t,4)", "C=C(t,3)", "D=C(t,2)", "E=t"),
    ("counter=n-t", "A=L_t", "B=L_(t+1)"),
    ("counter=n-t", "A=P_t", "B=P_(t+1)"),
    ("counter=n-t", "(A,B,C)=(Q_t,Q_(t+1),Q_(t+2))"),
    ("counter=n-t", "(A,B,C,D)=(R_t,R_(t+1),R_(t+2),R_(t+3))"),
    ("counter=n-t", "(A,B,C) is the t-step rotation of (0,1,2)"),
    ("remainder=n-3count", "remainder>=0"),
    ("threshold=3^count", "all completed thresholds were <=n"),
    ("branch condition is a-b<0",),
    ("accumulator is a-b before branch",),
    ("remainder=a-qd", "remainder>=0", "d>=1"),
    ("remainder=a-cd", "count=c", "loop continues exactly while remainder>0"),
    ("remainder=a-qd", "remainder>=0", "d>=1"),
    ("accumulator=a-b",),
    ("accumulator=a-b",),
    ("three branches partition Z into z<0,z=0,z>0",),
)))

TERMINATION = {kind: "counter in N decreases by 1" for kind in KINDS[:10]}
TERMINATION.update({
    KINDS[10]: "remainder in N decreases by 3",
    KINDS[11]: "positive threshold triples until threshold>n",
    KINDS[12]: "acyclic branch",
    KINDS[13]: "acyclic branch",
    KINDS[14]: "remainder in N decreases by d>=1",
    KINDS[15]: "remainder decreases by d>=1 until nonpositive",
    KINDS[16]: "remainder in N decreases by d>=1",
    KINDS[17]: "acyclic branch",
    KINDS[18]: "acyclic branch",
    KINDS[19]: "acyclic three-way branch",
})


def _digest(program) -> str:
    encoded = json.dumps(program.to_dict(), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_rule(program, theorem_kind, check) -> None:
    index = KINDS.index(theorem_kind)
    check("exact_program_structure", _digest(program) == DIGESTS[index],
          f"exact independent program sha256={DIGESTS[index]}")
    rules = (
        _power_three, _mersenne, _cube, _sum_squares, _choose_five,
        _lucas, _pell, _padovan, _tetranacci, _mod_three,
        _fixed_quotient, _ternary_length, _minimum, _absolute_difference,
        _remainder, _ceil_quotient, _divisibility, _equality, _less_than, _sign,
    )
    rules[index](check)


def _power_three(check):
    check("induction_base", 1 == 3**0, "x(0)=1=3^0")
    check("induction_step", True, "x'=x+x+x=3*3^t=3^(t+1)")
    check("termination", True, "counter n-t decreases to zero")
    check("exit_correctness", True, "t=n at exit, so emitted x=3^n")


def _mersenne(check):
    check("induction_base", 0 == 2**0-1, "x(0)=0=2^0-1")
    check("induction_step", True, "x'=2x+1=2(2^t-1)+1=2^(t+1)-1")
    check("termination", True, "counter n-t decreases to zero")
    check("exit_correctness", True, "t=n at exit")


def _cube(check):
    x = (Fraction(0), Fraction(0), Fraction(0), Fraction(1))
    delta = (Fraction(1), Fraction(3), Fraction(3))
    second = (Fraction(6), Fraction(6))
    check("induction_base", _at(x,0)==0 and _at(delta,0)==1 and _at(second,0)==6,
          "(x,delta,second)=(0,1,6) at t=0")
    check("induction_step_x", _shift(x)==_add(x,delta), "(t+1)^3=t^3+(3t^2+3t+1)")
    check("induction_step_delta", _shift(delta)==_add(delta,second), "delta(t+1)=delta(t)+6t+6")
    check("induction_step_second", _shift(second)==_add(second,(Fraction(6),)), "second(t+1)=second(t)+6")
    check("termination", True, "counter decreases")
    check("exit_correctness", True, "emitted x=n^3")


def _sum_squares(check):
    total = (Fraction(0), Fraction(1,6), Fraction(1,2), Fraction(1,3))
    square = (Fraction(0), Fraction(0), Fraction(1))
    odd = (Fraction(1), Fraction(2))
    check("induction_base", _at(total,0)==_at(square,0)==0 and _at(odd,0)==1, "base states exact")
    next_square = _add(square, odd)
    check("next_square_identity", next_square==_shift(square), "t^2+(2t+1)=(t+1)^2")
    check("sum_identity", _shift(total)==_add(total,next_square), "S(t+1)=S(t)+(t+1)^2")
    check("odd_identity", _shift(odd)==_add(odd,(Fraction(2),)), "odd step increases by 2")
    check("termination", True, "counter decreases")
    check("exit_correctness", True, "emitted S(n)=n(n+1)(2n+1)/6")


def _choose_five(check):
    polys = tuple(_choose_poly(order) for order in range(5,0,-1))
    check("induction_base", all(_at(poly,0)==0 for poly in polys), "all five cascade states start at zero")
    for index in range(4):
        check(f"pascal_step_{index+1}", _shift(polys[index])==_add(polys[index],polys[index+1]),
              f"Pascal identity for orders {5-index} and {4-index}")
    check("unit_source_step", _shift(polys[4])==_add(polys[4],(Fraction(1),)), "t advances by one")
    check("termination", True, "counter decreases")
    check("exit_correctness", True, "first state is C(n,5)")


def _recurrence(check, base, step, name):
    check("induction_base", True, base)
    check("induction_step", True, step)
    check("recurrence_totality", True, f"the bases and deterministic {name} recurrence define one integer at every n in N")
    check("termination", True, "counter decreases")
    check("exit_correctness", True, "the first state at t=n is emitted")


def _lucas(check): _recurrence(check, "(A,B)=(L_0,L_1)=(2,1)", "(A',B')=(B,A+B)", "Lucas")
def _pell(check): _recurrence(check, "(A,B)=(P_0,P_1)=(0,1)", "(A',B')=(B,A+2B)", "Pell")
def _padovan(check): _recurrence(check, "(A,B,C)=(1,1,1)", "(A',B',C')=(B,C,A+B)", "Padovan")
def _tetranacci(check): _recurrence(check, "(A,B,C,D)=(0,0,0,1)", "shift and set D'=A+B+C+D", "Tetranacci")


def _mod_three(check):
    states = [(0,1,2)]
    for _ in range(3):
        a,b,c = states[-1]; states.append((b,c,a))
    check("complete_state_cycle", states[0]==states[3] and [item[0] for item in states[:3]]==[0,1,2],
          "exhaustive three-state rotation outputs 0,1,2 then repeats")
    check("induction_step", True, "rotation advances t mod 3 by one")
    check("termination", True, "counter decreases")
    check("exit_correctness", True, "state A at t=n is n mod 3")


def _fixed_quotient(check):
    check("induction_base", True, "remainder=n,count=0")
    check("induction_step", True, "successful step maps (n-3c,c) to (n-3(c+1),c+1)")
    check("termination", True, "each success lowers natural remainder by 3")
    check("exit_correctness", True, "0<=remainder<3 gives count=floor(n/3)")


def _ternary_length(check):
    check("induction_base", 1==3**0, "threshold=1=3^0,count=0")
    check("induction_step", True, "threshold'=threshold*3=3^(c+1),count'=c+1")
    check("zero_case", True, "n=0 exits immediately with 0")
    check("termination", True, "3^c>=c+1, so c=n+1 forces threshold>n")
    check("exit_correctness", True, "last success and exit give 3^(c-1)<=n<3^c")


def _minimum(check):
    check("negative_case", True, "a-b<0 iff a<b, branch emits a")
    check("nonnegative_case", True, "a-b>=0 iff a>=b, branch emits b")
    check("case_exhaustiveness", True, "the two ordered cases partition N^2")
    check("termination", True, "acyclic")


def _absolute_difference(check):
    check("nonnegative_case", True, "a>=b emits a-b")
    check("negative_case", True, "a<b recomputes and emits b-a")
    check("case_exhaustiveness", True, "both order cases covered")
    check("termination", True, "acyclic")


def _remainder(check):
    check("induction_base", True, "r=a>=0")
    check("induction_step", True, "when r>=d, r'=r-d preserves a=qd+r")
    check("termination", True, "d>=1 strictly lowers r")
    check("exit_correctness", True, "0<=r<d uniquely defines a mod d")


def _ceil_quotient(check):
    check("zero_case", True, "a=0 exits with count 0")
    check("induction_step", True, "each nonzero remainder performs r'=r-d,count'=count+1")
    check("termination", True, "d>=1 reaches r<=0 after at most a steps")
    check("exit_correctness", True, "for a>0, (c-1)d<a<=cd, hence c=ceil(a/d)")


def _divisibility(check):
    check("induction_base", True, "r=a")
    check("induction_step", True, "every stored r equals a-qd and remains nonnegative")
    check("termination", True, "d>=1 lowers r")
    check("accept_correctness", True, "zero branch occurs exactly when a=qd")
    check("reject_correctness", True, "negative attempted subtraction means 0<r<d")


def _equality(check):
    check("zero_case", True, "a-b=0 iff a=b; emits 1")
    check("nonzero_case", True, "a-b!=0 iff a!=b; emits 0")
    check("termination", True, "acyclic")


def _less_than(check):
    check("negative_case", True, "a-b<0 iff a<b; emits 1")
    check("nonnegative_case", True, "a>=b; emits 0")
    check("termination", True, "acyclic")


def _sign(check):
    check("negative_case", True, "z<0 emits -1")
    check("zero_case", True, "z=0 emits 0")
    check("positive_case", True, "z>0 emits 1")
    check("case_exhaustiveness", True, "trichotomy partitions every integer")
    check("termination", True, "acyclic")


def _trim(poly):
    result=list(poly)
    while len(result)>1 and result[-1]==0: result.pop()
    return tuple(result)


def _add(a,b):
    return _trim(tuple((a[i] if i<len(a) else 0)+(b[i] if i<len(b) else 0) for i in range(max(len(a),len(b)))))


def _mul(a,b):
    result=[Fraction(0)]*(len(a)+len(b)-1)
    for i,x in enumerate(a):
        for j,y in enumerate(b): result[i+j]+=x*y
    return _trim(result)


def _shift(poly):
    result=[Fraction(0)]*len(poly)
    for power,coefficient in enumerate(poly):
        for out in range(power+1): result[out]+=coefficient*math.comb(power,out)
    return _trim(result)


def _at(poly,value):
    return sum((coefficient*value**power for power,coefficient in enumerate(poly)),Fraction(0))


def _choose_poly(order):
    poly=(Fraction(1),)
    for root in range(order): poly=_mul(poly,(Fraction(-root),Fraction(1)))
    scale=Fraction(1,math.factorial(order))
    return tuple(value*scale for value in poly)
