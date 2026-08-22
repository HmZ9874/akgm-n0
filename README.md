# AKGM-N0

[![Research prototype](https://img.shields.io/badge/status-research_prototype-orange)](https://github.com/HmZ9874/akgm-n0)
[![Help wanted](https://img.shields.io/badge/help-wanted-brightgreen)](https://github.com/HmZ9874/akgm-n0/issues)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)

> **Help wanted.** We are looking for independent reviewers and collaborators in program synthesis, formal verification, mathematical foundations, adversarial benchmarking, and reproducible physical experiments. If you find target leakage, a false universal claim, an invalid proof obligation, or a better experiment, please [open an issue](https://github.com/HmZ9874/akgm-n0/issues/new).

AKGM-N0 (Autonomous Knowledge Generation Model, N0) is an auditable research prototype for constructing executable numerical knowledge from anonymous observations and a small computational substrate. It searches for programs, compresses repeated computation into reusable semantics, seeks counterexamples, and restricts every claim to the domain actually supported by evidence.

It is **not a Transformer** and it is not a language model trained in the browser. Python processes perform program search and verification. The web dashboard displays programs, evidence, proof obligations, counterexamples, and claim boundaries.

## Research questions

AKGM-N0 investigates questions stricter than sequence completion:

1. Can a system construct executable relations without receiving their mathematical names or target formulas?
2. Can it compress repeated primitive instructions into a new, reusable runtime operation?
3. Can a discovered operation transfer to held-out scales, tasks, or physical trajectories?
4. When a counterexample appears, can the system reject or narrow a claim instead of preserving a false universal rule?
5. Can it identify a knowledge gap, choose the next experiment, and stop after semantic saturation?
6. Can anonymous physical observations induce a stateful computational mechanism?

## Claim boundary

The repository demonstrates program synthesis and verification inside explicit finite languages and protocols. It does **not** establish that the system:

- is artificial general intelligence;
- has mastered all mathematics or all mechanics;
- began without representational or computational priors;
- proved a universal law from finite samples alone;
- discovered a law previously unknown to humanity;
- performed a new live NASA battery experiment;
- invented recurrent state models for humanity.

In this repository, a “discovery” means that the learner was not given the target name or target formula, the candidate was produced by the declared search process, and it passed the stated verifier. Human-equivalent names are assigned post hoc. This is learner-relative novelty, not automatically historical novelty.

## Evidence labels used below

| Label | Meaning |
| --- | --- |
| **Proved** | The declared domain is covered by an algebraic identity, invariant, induction, or equivalent proof obligation. |
| **Verified** | All registered empirical, holdout, and OOD gates passed, without a universal mathematical claim beyond those gates. |
| **Bounded** | The program is useful on a restricted domain, awaits a broader proof, or failed a later generalization challenge. |
| **Post-hoc translation** | The learner saw opaque symbols; the familiar mathematical or physical interpretation was assigned after search. |

## Architecture

~~~mermaid
flowchart LR
    A[Anonymous observations or primitive workloads] --> B[Program and fragment enumeration]
    B --> C[Parameter fit and complexity score]
    C --> D[Independent verifier]
    D -->|all required gates pass| E[Admitted semantic library]
    D -->|optional challenge fails| F[Bounded knowledge]
    D -->|required gate fails| G[Counterexample and mistake store]
    E --> H[Reuse and composition]
    F --> H
    G --> I[Knowledge-gap analysis]
    H --> I
    I --> J[Next experiment or generated world]
    J --> A
    E --> K[Reports and evidence dashboard]
    F --> K
    G --> K
~~~

Repository boundaries:

- <code>src/akgm_n0/learner/</code>: public execution languages, search, semantic invention, and experiment planning.
- <code>src/akgm_n0/evaluator/</code>: independent verification, hidden cases, proof obligations, and claim control.
- <code>configs/</code>: learner-visible contracts and primitive manifests.
- <code>evaluator/</code>: sealed benchmark information that must not enter the learner process.
- <code>reports/data/</code>: compact experiment reports and audit evidence.
- <code>dashboard/</code>: local evidence dashboard.
- <code>tests/</code>: regression, mutation, counterexample, and claim-boundary tests.

## What is supplied at cold start?

The repository contains multiple protocols with different starting surfaces. Their claims must not be mixed.

### Gen 0 numerical-program protocol

Learner-visible information:

- anonymous numeric sequences;
- sequence order and boundaries;
- an explicit validity mask;
- bounds-checked relative reads;
- program composition;
- <code>p_read_offset</code>, <code>p_add</code>, <code>p_subtract</code>, <code>p_scalar_parameter</code>, and <code>p_compose</code>.

Hidden information:

- natural language and mathematical names;
- generator source code and parameters;
- train, validation, and blind split labels;
- pretrained models;
- network access;
- evaluator-side human interpretations.

Gen 0 supplies addition and subtraction, so it cannot prove that arithmetic emerged from an absolute zero-operation substrate. It establishes the information boundary, executable AST search, independent verification, and ledger pipeline.

### V16 strict semantic cold start

V16 loads no successful program, formula name, or dynamic operator. Its fixed VM substrate contains eight opcodes:

- data: <code>u_zero</code>, <code>u_unit</code>, <code>u_inc</code>, <code>u_dec</code>;
- control: <code>u_jz</code>, <code>u_jump</code>, <code>u_emit</code>, <code>u_halt</code>.

Semantic mining begins only from anonymous workloads over the four data opcodes. Registers, counters, an instruction pointer, and control flow are still supplied computational priors. The experiment studies abstraction above that substrate, not computation without any prior semantics.

## Core algorithms

### A. Gen 0 expression search

Candidates are executable ASTs, for example:

~~~json
{
  "op": "p_subtract",
  "args": [
    {"op": "p_read_offset", "offset": 0},
    {"op": "p_scalar_parameter", "parameter_slot": 0}
  ]
}
~~~

The search:

1. Enumerates expression trees in increasing odd node count.
2. Canonicalizes commutative addition arguments and deduplicates serialized ASTs.
3. Structurally prevents candidates from reading the target offset.
4. Splits valid examples in temporal order; the default validation fraction is 0.4.
5. Fits the single linear scalar slot by evaluating the program at θ=0 and θ=1. If pᵢ(θ)=bᵢ+cᵢθ, then:

   θ* = Σ cᵢ(yᵢ-bᵢ) / Σ cᵢ²

6. Ranks candidates by:

   J(P) = MSE_val(P) / max(Var(y), 10^-12) + λ · nodes(P)

   with default λ=10^-3, followed by raw validation MSE, node count, and stable candidate ID.
7. Rejects invalid indices, invalid masks, unknown operations, excessive depth or size, non-finite values, and excessive magnitude.

This is deterministic enumerative program synthesis, not neural-network training.

### B. Independent verification and counterexamples

Each verification case defines a scope, a parameter-refit prefix, an absolute tolerance, and whether it is required for validity. The verifier refits only on the allowed prefix, executes on the remaining positions, and records MSE, normalized MSE, maximum absolute error, and every counterexample.

| Result | Rule |
| --- | --- |
| <code>verified</code> | Every required and optional case passed. |
| <code>bounded</code> | Every required case passed, but at least one optional extension challenge failed. |
| <code>rejected</code> | At least one required case failed. |

Failures remain in the evidence record. They restrict the valid domain and feed the next knowledge-gap analysis.

### C. Runtime semantic invention

V16 creates new opcodes by cross-family minimum-description-length compression:

1. Mine instruction windows of length 2 through 4.
2. Normalize concrete register numbers into argument roles.
3. Require support in at least three workload families, with at least five occurrences in every counted family.
4. Let T_body be the encoded fragment cost, T_call=1+arity, and n the occurrence count:

   gain_per_use = T_body - T_call

   net_reward = n · gain_per_use - T_body

5. Reject candidates with non-positive gain, duplicate behavior, identity behavior, illegal execution, or unavailable dependencies.
6. Install a passing fragment as an opaque hash-bound opcode such as <code>nu_a1b2c3d4e5f6</code>.
7. Recompress the corpus and mine higher-generation combinations under acyclic dependency, arity, generation, and primitive-span limits.

“Created operation” therefore means a new executable and expandable runtime semantic that was absent from the registry and has cross-workload compression value. It does not imply that humanity lacks an equivalent operation.

### D. Correctness-first token reward

For foundation programs:

- exact completion reward: 1,000,000;
- non-exact reward: 1,000 per passed case;
- cost: expanded primitive execution tokens plus stored program tokens;
- final reward: correctness reward minus total token cost.

Macro calls cannot hide work: execution cost is charged after primitive expansion. These are program representation and execution tokens, not language-model context tokens.

### E. Autonomous experiment loop

V17:

1. Counts primitive transition pairs and operator arities in the current library.
2. Selects the least-evidenced transition and the least-evidenced arity among 1 and 2.
3. Commits the gap, round, and random seed to a deterministic hash.
4. Generates four anonymous families, 48 workloads per family, and 36 instructions per workload.
5. Extends V16 semantics and records rejected equivalents or zero-gain fragments.
6. Stops after four consecutive sterile rounds by default, or at the 32-round hard limit.

The generated worlds are still synthetic counter-machine worlds. Open-ended modeling of unknown real apparatus remains future work.

## Internal formula notation

The following opaque forms recur across reports:

| Internal symbol | Executable meaning | Human interpretation assigned afterward |
| --- | --- | --- |
| <code>MERGE&lt;x,y,...&gt;</code> | combine directed counter values | addition or accumulation |
| <code>TURN&lt;x&gt;</code> | swap positive and negative directed channels | additive inverse / negation |
| <code>SEM&lt;x,y&gt;</code> | proved repeated accumulation semantic | multiplication on the declared domain |
| <code>KEEP&lt;x&gt;</code> | route a source unchanged | identity route |
| <code>DOUBLE&lt;x&gt;</code> | combine a source with itself | 2x |
| <code>STATE_FOLD</code> | recurrently update stored state | a state-space recurrence |
| hashed IDs | bind a program or semantic to its exact structure | stable name, not a human formula name |

## Formula catalog

This catalog lists canonical, non-duplicate semantics with explicit evidence. Generated libraries containing hundreds or thousands of variants are not treated as hundreds or thousands of distinct mathematical laws.

### 1. Proved foundational semantics

| Internal representation | Human-equivalent formula or concept | Status and domain |
| --- | --- | --- |
| <code>STRICT-FSEM-82df58ba4ce6f41c</code> | x·y for x,y∈N | **Proved** by counter-loop invariant and termination. |
| <code>STRICT-FSEM-008b1597aed53d52</code> | n=dq+r, 0≤r&lt;d; q=⌊n/d⌋ | **Proved** for n∈N, d∈N+. |
| Pair equivalence <code>(a,b)~(c,d) iff ad=bc</code> | nonnegative rational equivalence classes | **Proved** on N×N+. |
| <code>V20-PROOF-PAIR-2f49d4c7971361a0</code> | a/b+c/d=(ad+bc)/(bd) | **Proved** well-defined on positive-denominator classes. |
| <code>V20-PROOF-PAIR-6088f4bcd017e9cc</code> | (a/b)(c/d)=ac/bd | **Proved** well-defined on positive-denominator classes. |
| Directed triple <code>(p,n,d)</code> with <code>MERGE</code>, <code>TURN</code>, and <code>SEM</code> | (p-n)/d; signed rational addition, negation, and multiplication | **Proved** commutative-ring presentation; multiplicative inverses are not yet claimed. |
| V21 translation solver | x+b=c ⇒ x=c-b | **Proved** for directed rational equivalence classes. |
| <code>XSEM-e27ac00be31ef317</code> | P(b,n)=∏ᵢ₌₀ⁿ⁻¹(b-i), with 0 when n&gt;b | **Proved** by exclusion invariant and structural induction. |
| <code>CSEM-b9aacd5426b56d40</code> | C(b,n)=b!/[n!(b-n)!] | **Proved** through unique increasing representatives and Pascal partition. |
| <code>MSEM-3e8b2a2c8bfae1e3</code> | μ(E)=|E|/|Ω|; fair binary P(K=k)=C(n,k)/2ⁿ | **Proved** only for finite uniform nonempty sample spaces. |
| <code>RSEM-a80a8102b32768d6</code> | exact √(p/q)=a/b when a²=p and b²=q; otherwise reject | **Proved** for nonnegative rational perfect squares. |
| <code>ISEM-0ca406080fcca1af</code> | Lₙ²≤x≤Uₙ² and Uₙ-Lₙ=max(1,x)/2ⁿ | **Proved** finite rational enclosure for nonnegative square roots; not a completed irrational real number. |

Source reports: [V20 program construction](reports/data/proof_driven_program_construction_v20_latest.json), [V21 directed rationals](reports/data/directed_rational_construction_v21_latest.json), [finite combinatorics](reports/data/autonomous_canonicalization_latest.json), [finite probability](reports/data/autonomous_finite_mass_latest.json), and [root boundaries](reports/data/autonomous_interval_memory_latest.json).

### 2. High-school core programs

The internal high-school programs are selected opaque modes. Their mathematical names and statements were evaluator-side only during search.

| Internal program | Post-hoc human equivalent | Proved statement / scope |
| --- | --- | --- |
| <code>HSP-beb378056706d8f0</code> | normalized rational quotient | (a/b)/(c/d)=ad/(bc), followed by unique gcd normalization. |
| <code>HSP-c137d9c3c048fa13</code> | one-variable linear equation | ax+b=c ⇒ x=(c-b)/a for a≠0. |
| <code>HSP-4064b48f6ff6b32d</code> | nonsingular 2×2 linear system | Cramer identities give the unique solution when ad-bc≠0. |
| <code>HSP-2ba2192d55090953</code> | exact quadratic roots | x=(-b±√(b²-4ac))/(2a) when the supported exact root exists. |
| <code>HSP-18086b42a455a053</code> | discriminant classification | sign(b²-4ac) classifies two, repeated, or no real roots. |
| <code>HSP-03adf64be2057b6e</code> | arithmetic sequence term | aₙ=a₁+(n-1)d. |
| <code>HSP-2094637a04498313</code> | arithmetic sequence sum | Sₙ=n[2a₁+(n-1)d]/2. |
| <code>HSP-30932f3ff4758be4</code> | geometric sequence term | aₙ=a₁qⁿ⁻¹. |
| <code>HSP-de21960f97154923</code> | finite geometric sum | Sₙ=a₁(qⁿ-1)/(q-1), with the q=1 case handled separately. |
| <code>HSP-5428450d08bce4a4</code> | cubic polynomial evaluation | Horner form equals ax³+bx²+cx+d. |
| <code>HSP-71f42915d934e214</code> | formal cubic derivative | d/dx(ax³+bx²+cx+d)=3ax²+2bx+c. |
| <code>HSP-e448f4c6d41a259a</code> | affine composition | f(g(x))=a(cx+d)+b. |
| <code>HSP-89f3b267c5a31daa</code> | exact integer logarithm | returns the unique n satisfying baseⁿ=value on exact powers. |
| <code>HSP-0e01deef1af154f9</code> | coordinate midpoint | ((x₁+x₂)/2,(y₁+y₂)/2). |
| <code>HSP-2bf32de987fe97ca</code> | nonvertical slope | m=(y₂-y₁)/(x₂-x₁). |
| <code>HSP-e0056da36499a642</code> | squared Euclidean distance | d²=(x₂-x₁)²+(y₂-y₁)². |
| <code>HSP-668c37cddbe7e714</code> | right-triangle ratios | sin=opposite/hypotenuse, cos=adjacent/hypotenuse, sin²+cos²=1 on positive Pythagorean triples. |
| <code>HSP-e2e26b7e739b76b0</code> | symmetric binomial probability | P(K=k)=C(n,k)/2ⁿ. |
| <code>HSP-90022000791738ec</code> | closed interval intersection | [max(l₁,l₂), min(u₁,u₂)] when nonempty. |
| <code>HSP-ca88f3a71f79efbe</code> | signed rational normalization | gcd reduction gives a unique positive-denominator normal form. |

Full evidence: [high_school_core_v6_latest.json](reports/data/high_school_core_v6_latest.json).

### 3. Bounded parametric program families

These programs passed their recorded examples and hidden cases, but their report explicitly says they await universal proof. They must not be presented as proved laws.

| Internal candidate | Human-equivalent family | Status |
| --- | --- | --- |
| <code>AP-6a9752a5f642937d</code> | A(a,d,n)=a+nd | **Bounded** |
| <code>AP-f0e8770fc5237676</code> | S(a,d,n)=Σᵢ₌₀ⁿ⁻¹(a+id) | **Bounded** |
| <code>AP-fd8c5ceab884e740</code> | rising factorial ∏ᵢ₌₀ᵏ⁻¹(a+i) | **Bounded** |
| <code>AP-83cc12a184cf61e5</code> | F₀=a, F₁=b, Fₜ₊₂=Fₜ+Fₜ₊₁ | **Bounded** |
| <code>AP-b6911239fc02f362</code> | digit length of x in base b | **Bounded** |
| <code>AP-0d42e85ae733addd</code> | ⌊log_b(x)⌋ | **Bounded** |
| <code>AP-ff387ecac036bc61</code> | lcm(a,b) | **Bounded** |
| <code>AP-550e86b4684e754b</code> | aⁿ mod m | **Bounded** |
| <code>AP-37582cd3f9a3706a</code> | Σᵢ₌₀ⁿaⁱ | **Bounded** |
| <code>AP-18f958c4b7fca578</code> | a+nd+C(n,2)e | **Bounded** |

Full machine words, counterexamples, and status records: [advanced_parametric_ten_latest.json](reports/data/advanced_parametric_ten_latest.json).

### 4. Synthetic mechanics: internal programs and known physical counterparts

These rows reconstruct familiar mechanics inside exact synthetic worlds. Human quantity names and formulas were hidden from the learner, but the hidden world generators still encode structured experiment families. They are not independent discoveries of new natural laws.

| Stage and internal program | Post-hoc physical counterpart | Evidence boundary |
| --- | --- | --- |
| V22 <code>MERGE&lt;SEM&lt;q3,q1&gt;,q0&gt;</code> | x′=x+Δt·v | **Proved** discrete rational transition. |
| V22 <code>MERGE&lt;SEM&lt;q3,q2&gt;,q1&gt;</code> | v′=v+Δt·a | **Proved** discrete rational transition. |
| V22 exchange <code>(q0⊕j)⊕(q1⊕TURN(j))</code> | additive closed-system conservation | **Proved** internally; momentum-like post-hoc interpretation. |
| V24 <code>RESP&lt;KEEP,DEN:SEM&lt;D,P&gt;&gt;</code> | a=F/m, equivalently F=ma | **Proved** in exact one-dimensional synthetic rational experiments. |
| V24 <code>MERGE&lt;SEM&lt;q0,q1&gt;,SEM&lt;q2,q3&gt;&gt;</code> | m₁v₁+m₂v₂ | **Proved** weighted conservation. |
| V25 <code>COL&lt;...;DEN:MERGE&lt;Q0,Q2&gt;&gt;</code> | exact 1-D elastic collision update | **Proved** for two instantaneous perfectly elastic entities. |
| V25 linear invariant | m₁v₁+m₂v₂ | **Proved** in the collision domain. |
| V25 <code>MERGE&lt;SEM&lt;q0,SEM&lt;q1,q1&gt;&gt;,SEM&lt;q2,SEM&lt;q3,q3&gt;&gt;&gt;</code> | m₁v₁²+m₂v₂², twice conventional kinetic energy | **Proved**; factor 1/2 is not identifiable from conservation alone. |
| V26 <code>ORB&lt;ZERO,KEEP,TURN,ZERO&gt;</code> | x v_y-y v_x | **Proved** planar oriented bilinear scalar. |
| V26 <code>ROT&lt;Q0,ORB&lt;...&gt;&gt;</code> | L=m(xv_y-yv_x) | **Proved** planar angular-momentum form. |
| V26 balance | ΔL=r×J | **Proved** angular-impulse relation for the synthetic domain. |
| V27 <code>AGG&lt;Q0,MERGE&lt;SEM&lt;Q1,Q1&gt;,SEM&lt;Q2,Q2&gt;&gt;&gt;</code> | I=Σᵢmᵢrᵢ² | **Proved** fixed-axis point-mass inertia. |
| V27 response | Δω=angular impulse/I | **Proved** synthetic fixed-axis response. |
| V27 angular quantity | L=Iω | **Proved** in the declared domain. |
| V27 quadratic quantity | Iω², twice rotational kinetic energy | **Proved** in the declared domain. |
| V27 parallel-axis relation | I_O=I_CM+Md² | **Proved** for the represented point sets. |
| V28 <code>STENCIL&lt;TURN,ZERO,KEEP;H^1;S2&gt;</code> | dx/dt≈[x(t+h)-x(t-h)]/(2h) | **Proved** exact on quadratics; second-order certificate on the stated polynomial family. |
| V28 <code>STENCIL&lt;KEEP,TURN_DOUBLE,KEEP;H^2;S1&gt;</code> | d²x/dt²≈[x(t-h)-2x(t)+x(t+h)]/h² | Same restricted refinement proof. |
| V29 <code>MET&lt;KEEP,ZERO,ZERO,KEEP&gt;</code> | dot product | **Proved** in the planar rational representation. |
| V29 <code>TANGENT&lt;TURN&lt;q1&gt;,KEEP&lt;q0&gt;&gt;</code> | tangent (-y,x) to x²+y²=R² | **Proved** for one circle constraint. |
| V29 <code>PROJECT&lt;TURN;DEN:MET&lt;R,R&gt;&gt;</code> | u-r(r·u)/(r·r) | **Proved** planar tangent projection. |
| V30 <code>RESTORE&lt;TURN;NUM:SEM&lt;K,X&gt;;DEN:M&gt;</code> | a=-(k/m)x | **Proved** linear one-mode oscillator. |
| V30 phase invariant | mv²+kx² | **Proved** for the modeled oscillator. |
| V30 recurrence | xₙ₊₁=2xₙ-xₙ₋₁-(k/m)h²xₙ | **Proved** in the declared discrete scheme. |
| V31 <code>FIELD&lt;TURN;SEM&lt;Q0,R&gt;;Q3^3&gt;</code> | a=-μr/r³; magnitude μ/r² | **Proved** for a 2-D point-particle central field. |
| V31 angular invariant | r×v | **Proved** in that field. |
| V31 <code>ENERGY&lt;MET&lt;V,V&gt;,TURN_DOUBLE&lt;Q0/Q3^1&gt;&gt;</code> | v²-2μ/r | **Proved** orbital classification invariant: negative bound, zero critical, positive escape. |
| V32 <code>ACTION&lt;KW:M;PW:K;P:TURN;H^2&gt;</code> | Σ[m(Δx/h)²-kx²]; stationarity gives mx″+kx=0 | **Proved** for one-coordinate quadratic actions; overall scale is unidentifiable. |
| V33 <code>MOMENTUM&lt;M,V&gt;</code> | p=mv | **Proved** one-degree-of-freedom canonical momentum. |
| V33 <code>FLOW&lt;KEEP;ONE*P/M&gt;</code> | q̇=p/m | **Proved** quadratic canonical flow. |
| V33 <code>FLOW&lt;TURN;K*Q/ONE&gt;</code> | ṗ=-kq | **Proved** quadratic canonical flow. |
| V33 <code>HAMILTON&lt;P2/M,KEEP&lt;K*Q2&gt;&gt;</code> | H₂=p²/m+kq², twice conventional H | **Proved** for the quadratic model. |
| V34 <code>SEM&lt;RHO,U&gt;</code> | mass flux ρu | **Proved** 1-D inviscid finite-volume model. |
| V34 <code>MERGE&lt;SEM&lt;RHO,U,U&gt;,P&gt;</code> | momentum flux ρu²+p | **Proved** in the same model. |
| V34 <code>BALANCE&lt;L:KEEP;R:TURN;DT^1;DX:DIV&gt;</code> | q_t+(flux)_x=0 | **Proved** finite-volume balance and global conservation in the declared grid model. |
| V35 <code>FRAME&lt;MERGE&lt;Q1,Q2&gt;;DEN:MERGE&lt;ONE,SEM&lt;Q1,Q2&gt;/SEM&lt;Q0,Q0&gt;&gt;&gt;</code> | (u+v)/(1+uv/c²) | **Proved/verified** for 1-D rational velocities and a supplied anonymous finite speed bound. |

Detailed reports are in <code>reports/data/*_latest.json</code> for V22 through V35.

### 5. Empirical, apparatus, and real-archive formulas

| Internal program | Post-hoc real-world interpretation | Status |
| --- | --- | --- |
| V36 <code>SCI-9d226ebd0e1c9402: MERGE&lt;DOUBLE&lt;ONE&gt;,Q0,TURN&lt;Q1&gt;,SEM&lt;Q0,Q1&gt;&gt;</code> | 2+x-y+xy on a blind synthetic oracle | **Verified workflow only**; local learner novelty, not a human-unknown law. |
| V37 <code>EMP-ded6dd18830aa0cc: POWER&lt;SCALE&lt;367.01582&gt;;Q0^3/2;Q1^-1/2&gt;</code> | P_days≈367.016·a_AU^(3/2)·M_solar^(-1/2) | **Verified known-law rediscovery** on a real archive; not a new law. |
| V38 <code>CAU-759e07bc9a29b606</code> | load-cell deflection ≈0.0005549+2.19637Q0-0.0287121Q0² | **Verified historical controlled calibration**, but temporal drift prevents a clean unrestricted causal claim. |
| V39 <code>LIVE-36da1f0fe8d71daf: LIVE_POWER&lt;SCALE&lt;51.4051&gt;;Q0^2&gt;</code> | elapsed runtime scales approximately with nested-loop side length squared | **Verified live computational apparatus**, not natural science. |
| V40 <code>PHYS-SEM-97df0a28f607243e: LOCAL_MEMORY&lt;...&gt;::NEAREST_DELTA_BLEND</code> | local interpolation from scanner brightness control to normalized image luminance | **Verified live external device calibration** on one HP scanner; no universal optical law claimed. |
| V41 <code>DYN-bb87df43ec46ed50: STATE_FOLD</code> | recurrent battery terminal-voltage trajectory model using current, temperature, and elapsed time | **Bounded**: verified on the registered RW3/RW4 protocol, generalized to RW5/RW6 early and middle life, failed late-life extrapolation. |
| V42 <code>XFER-a7588b2a1ab1b64d: INTERACTION_FOLD</code> | recurrent terminal-voltage program with initial-trajectory context and anonymous pairwise interaction features | **Verified on a reused archive with a programmatic seal**: selected on anonymous object A, frozen before object B was revealed to the learner, and remained below RMSE 0.10 in all three object-B stages. Developers had prior archive access, so this is not a fresh human-blind result or a universal battery law. |
| V43 <code>AUTOSEM-ca24f07411b0f22d: AUTONOMOUS_UPDATE</code> | second-order recurrent update with two anonymously selected exogenous inputs | **Verified bounded research-language growth on the reused archive**: the learner started with one visible input and zero state slots, autonomously grew another input and two state slots, froze the resulting program, and beat V42 transfer RMSE. This is not a fresh external replication or a fully autonomous scientist. |
| V44 <code>AUTOSEM-24d817b8706b9172: AUTONOMOUS_UPDATE</code> | guarded second-order recurrent update over one autonomously retained anonymous observation channel | **Verified bounded official-world selection**: the system ranked three anonymous NASA/NOAA/USGS worlds, committed before transfer and domain reveal, and passed two unseen source groups at normalized RMSE 0.2530. The first blind choice failed and is retained in the mandatory mistake replay room. This is observational archive research, not causal or fully autonomous science. |

The frozen V41 recurrence is:

s_t = -0.0207367186 + 0.9990723901 s_(t-1) - 0.00283072368 Q0_t + 0.000833014422 Q2_t + 0.000265220314 ΔQ3_t + 0.00000780798945 Q3_t

Post-hoc channel mapping:

- Q0: absolute measured current;
- Q1 and state s: terminal voltage;
- Q2: battery temperature;
- Q3: elapsed pulse time.

The RW5/RW6 late-life RMSE was 0.1757585774, above the 0.10 gate. The stored action is to restrict STATE_FOLD to early and middle life until an explicit aging state is created. Its final status is <code>bounded</code>, and the all-life universal formula was removed.

### V42 counterexample-guided transfer

V42 consumes the stored V41 late-life counterexample and searches three domain-blind recurrent program families on anonymous object A: `STATE_FOLD`, `CONTEXT_FOLD`, and `INTERACTION_FOLD`. The selection score is validation RMSE plus `10^-5` per program node. Object identity, life stage, and human channel meanings are absent from learner inputs.

The selected internal recurrence is:

```text
s_t =
  W0
  + W1 s_(t-1)
  + W2 Q0_t
  + W3 Q2_t
  + W4 ΔQ3_t
  + W5 Q3_t
  + W6 Q1_0
  + W7 Q0_0
  + W8 Q2_0
  + W9 (Q0_t Q3_t)
  + W10 Q0_t²
  + W11 (Q2_t Q3_t)
  + W12 (s_(t-1) Q0_t)
  + W13 (s_(t-1) Q2_t)
```

Frozen coefficients:

```text
W0=0.208500205696       W1=0.946309297718
W2=0.963260862397       W3=-0.00660226307528
W4=0.000361421879496    W5=0.00024258452456
W6=-0.000147882028285   W7=-0.93476875709
W8=0.00269371444817     W9=0.0000688909745147
W10=0.00195916688848    W11=-0.0000116416189427
W12=-0.014602537751     W13=0.0011750697087
```

Post-hoc real-world interpretation: the program predicts the next terminal voltage from previous voltage, anonymous current and temperature observations, elapsed pulse time, initial trajectory context, and automatically composed interaction features. The learner received none of those physical names.

| Audit | RMSE |
| --- | ---: |
| Object-A validation | 0.0837894949 |
| Frozen object-B transfer, overall | 0.0831146940 |
| Object-B early stage | 0.0910280532 |
| Object-B middle stage | 0.0796053564 |
| Object-B late stage | 0.0781091406 |

The V41 frozen program's late-stage RMSE was 0.1757585774. V42 passes the reused-archive threshold, but the earlier universal claim remains revoked. Developers had prior access to RW6 while building the software, so the repository permits only the claim **programmatically sealed reused-archive transfer**. Fresh data from another campaign or laboratory is still required.

### V43 autonomous research-language growth

V43 removes the V42 menu of named candidate families. The learner receives a minimal structural genome with one visible anonymous input and no recurrent state. It can mutate generic resources only:

- expose one additional anonymous input channel;
- add a recurrent state slot, up to the current two-slot safety ceiling;
- add initial-context reads;
- add delta features;
- add pairwise interaction features;
- add one guarded path.

Each mutation compiles to an executable feature program. Coefficients are fitted on the development partition, and mutations are ranked by validation RMSE plus `10^-5` per executable node. A mutation is admitted only when information gain exceeds `10^-5`. Search stops after three consecutive sterile rounds.

The autonomous mutation path was:

```text
minimal genome
→ grow_state_slot
→ grow_input_channel
→ grow_state_slot
→ three sterile rounds
→ semantic_saturation
```

The selected internal program contains only:

```text
[ONE, X0, X1, LAG1, LAG2]
```

Its frozen recurrence is:

```text
s_t =
  0.160896295734
  - 0.00809372713701 X0_t
  - 0.000576917593253 X1_t
  + 1.23312212809 s_(t-1)
  - 0.270134119977 s_(t-2)
```

Post-hoc human translation: this is a second-order autoregressive model with anonymous exogenous inputs. After discovery, `X0` maps to absolute current, `X1` maps to temperature, and state `s` maps to terminal voltage. None of these names or this formula were learner-visible.

| Audit | RMSE |
| --- | ---: |
| Frozen transfer, overall | 0.0760343257 |
| Early stage | 0.0705449960 |
| Middle stage | 0.0795722680 |
| Late stage | 0.0776872819 |
| V42 overall reference | 0.0831146940 |

The program is shorter and more accurate on this reused transfer object than the V42 selected program. The independent replay verifier reconstructs the program, recomputes its hash commitment and transfer metric, and rejects coefficient tampering.

This result establishes **bounded autonomous research-language growth**, not a fully autonomous scientist. Floating-point arithmetic, linear least-squares fitting, structural mutation types, a two-state ceiling, data access, and the independent verifier remain supplied. Developers had prior access to RW6, so a genuinely fresh external world remains mandatory.

### V44 autonomous official-world selection

V44 supplies a finite, provenance-checked registry built from three official APIs: [NASA POWER Daily](https://power.larc.nasa.gov/docs/services/api/temporal/daily/), [NOAA CO-OPS](https://api.tidesandcurrents.noaa.gov/api/prod/), and the [USGS Earthquake Catalog](https://earthquake.usgs.gov/fdsnws/event/1/). The learner sees only anonymous world identifiers, numeric development traces, channel counts, and source-group boundaries. Institution names, physical variable names, transfer outputs, and human task descriptions remain sealed.

For every anonymous world, the system starts a V43 language-growth search, then computes:

```text
evidence_value = 0.45 information_gain
               + 0.30 predictability
               + 0.15 structural_novelty
               + 0.10 verification_readiness
               - 0.002 executable_nodes

research_priority = evidence_value / (1 + worst_development_group_error)
```

The first blind run selected `WORLD-692abdb0cf477f47` because it had the largest within-development information gain. It then failed sealed cross-source transfer at normalized RMSE `2.2891651360`. That negative result is stored as `V44-BLIND-FAILURE-0001`; no transfer measurement was used to refit the program. The repair added a development-only anonymous source-group stability term to the selection rule.

The next preregistered run ranked the worlds without domain labels:

| Rank | Anonymous world | Research priority | Cross-group stability | Development information gain |
| --- | --- | ---: | ---: | ---: |
| 1 | `WORLD-90f60bd59102a427` | 0.450002 | 0.813815 | 0.152649 |
| 2 | `WORLD-692abdb0cf477f47` | 0.197495 | 0.257174 | 1.299454 |
| 3 | `WORLD-a83610976b378d8f` | 0.091907 | 0.250000 | 0.000421 |

After the world and program commitments were recorded, transfer measurements from two disjoint source groups were revealed. The frozen program achieved normalized transfer RMSE `0.2530277052`. Only after that audit did the evaluator reveal that the selected world was NASA POWER meteorology and surface solar energy data.

The internal executable formula is:

```text
s_t = -0.488947789848
    + 0.108142225947 X0_t
    + 1.10085525762 s_(t-1)
    - 0.288777988538 s_(t-2)
    + 0.141280713917 s_0
    - 0.0329576695536 X0_0
    - 0.0159327637227 I[X0_t >= X0_0] s_(t-1)
```

Post-hoc human mapping: `X0` is all-sky surface shortwave irradiance, `s` is temperature at two metres, `s_0` and `X0_0` are trace-initial context, and `I[...]` is the autonomously selected guarded path. This is a compact multivariate/autoregressive weather-response program, not a universal meteorological law.

V44 implements anonymous multi-world ranking, knowledge-gap selection, preregistration, disjoint-source transfer, a persistent failure room, and an autonomous next-world queue. It does **not** implement unrestricted language invention, causal intervention, live apparatus control, literature-level novelty adjudication, or independent-laboratory replication. A fully autonomous scientist is therefore still not claimed.
Reports: [V37](reports/data/empirical_science_v37_latest.json), [V38](reports/data/interventional_science_v38_latest.json), [V39](reports/data/live_randomized_science_v39_latest.json), [V40](reports/data/external_physical_science_v40_latest.json), [V41 registered experiment](reports/data/official_dynamic_science_v41_latest.json), [V41 blind challenge](reports/data/nasa_v41_blind_challenge_latest.json), [V42 counterexample transfer](reports/data/counterexample_transfer_v42_latest.json), and [V43 autonomous scientist kernel](reports/data/autonomous_scientist_v43_latest.json), and [V44 autonomous official-world research](reports/data/autonomous_world_research_v44_latest.json).

## Why generated formula counts are not discovery counts

The repository contains large generated catalogs, including hundreds of operators and one thousand parameterized entries. Many are:

- syntactic variants;
- compositions of already known semantics;
- fixed-constant special cases of a parameterized family;
- empirically fitted but not universally proved;
- behaviorally equivalent on the tested domain.

They remain useful search artifacts, but the canonical tables above intentionally collapse duplicates and fixed constants into their general families. A new human-level mathematical discovery would require stronger novelty checks against existing literature, independent formal review, and evidence beyond the current system.

## Current capability map

| Stage | Implemented capability | Explicit boundary |
| --- | --- | --- |
| Gen 0 | auditable AST search, verifier, and knowledge ledger | addition and subtraction are supplied |
| V8-V14 | counter, sign, partition, fold, and algebraic-closure experiments | mostly restricted tasks and specialized verifiers |
| V15-V17 | self-extending VM, strict semantic cold start, autonomous experiment loop | worlds remain finite counter-machine worlds |
| V18-V21 | goal-driven planning, proof-carrying program construction, directed rationals | not a general symbolic mathematics planner |
| V22-V35 | anonymous mechanics reconstruction | mostly exact synthetic worlds, not independent natural-law discovery |
| V36-V40 | scientific workflow, intervention, live apparatus interfaces | limited apparatus and known or engineered phenomena |
| V41 | anonymous dynamic-state discovery on NASA battery trajectories | late-life extrapolation failed and the claim is bounded |
| V42 | counterexample-guided semantic competition and frozen cross-object transfer | reused archive; not a fresh human-blind or independent-laboratory replication |
| V43 | autonomous generic research-language mutation and saturation-controlled search | bounded genome, supplied regression substrate, reused archive, and no fresh external world |
| V44 | autonomous anonymous-world ranking, cross-source risk selection, preregistration, official archive transfer, and mandatory failure replay | finite host-curated registry; observational data only; no causal apparatus, unrestricted language, independent lab, or literature novelty verdict |

Dashboard labels such as “high school,” “mechanics,” or “science” denote experiment suites, not full human-equivalent mastery of those subjects.

## Quick start

Requirements:

- Python 3.11 or newer;
- Node.js 22.13 or newer for the dashboard;
- Python dependencies declared in <code>pyproject.toml</code>.

~~~powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
~~~

Run core audits and experiments:

~~~powershell
.\.venv\Scripts\python.exe scripts/audit_contracts.py
.\.venv\Scripts\python.exe scripts/run_search_smoke.py
.\.venv\Scripts\python.exe scripts/run_verification_smoke.py
.\.venv\Scripts\python.exe scripts/run_cold_start_semantics_v16.py
.\.venv\Scripts\python.exe scripts/run_autonomous_research_loop_v17.py
~~~

Run the evidence dashboard:

~~~powershell
cd dashboard
npm install
npm run dev
~~~

Open <http://localhost:5173/>. The dashboard reports evidence; it is not the training location. The V42 report is available at <http://localhost:5173/science-v42>. The V43 report is available at <http://localhost:5173/science-v43>. The V44 autonomous-world report is available at <http://localhost:5173/science-v44>.

## NASA V41 reproduction

The GitHub repository excludes the 120 MB official archive and extracted MATLAB files. It retains compact snapshots, provenance, SHA-256 digests, and reports.

Official resource:

<https://data.nasa.gov/docs/legacy/ames/2.Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post.zip>

Expected archive SHA-256:

<code>18bf47337577e07872919327a6ee994adc59e33fd2901d69c5911c26102837b8</code>

From the repository root:

~~~powershell
$archive = "data\nasa_v41\Battery_Random_Walk_Room_Temp_2Post.zip"
Invoke-WebRequest -Uri "https://data.nasa.gov/docs/legacy/ames/2.Battery_Uniform_Distribution_Discharge_Room_Temp_DataSet_2Post.zip" -OutFile $archive
Get-FileHash $archive -Algorithm SHA256
Expand-Archive -Path $archive -DestinationPath "data\nasa_v41\official"
.\.venv\Scripts\python.exe scripts/build_nasa_battery_v41_snapshot.py
.\.venv\Scripts\python.exe scripts/run_official_dynamic_science_v41.py
.\.venv\Scripts\python.exe scripts/build_nasa_battery_v41_challenge.py
.\.venv\Scripts\python.exe scripts/run_nasa_blind_challenge_v41.py
.\.venv\Scripts\python.exe scripts/run_counterexample_transfer_v42.py
.\.venv\Scripts\python.exe scripts/run_autonomous_scientist_v43.py
.\.venv\Scripts\python.exe scripts/build_official_worlds_v44.py
.\.venv\Scripts\python.exe scripts/run_autonomous_world_research_v44.py
~~~

Manually confirm that the archive hash matches before running the builders. Do not commit the raw archive or extracted source files.

## Help wanted

Priority collaboration areas:

1. Audit learner/evaluator separation and detect target leakage.
2. Move specialized Python proof obligations into machine-checkable formal systems.
3. Improve behavioral equivalence and nontriviality checks for generated operators.
4. Scale synthesis with e-graphs, constraint solving, inductive synthesis, or stronger MDL methods.
5. Design low-cost blinded apparatus and cross-laboratory replication protocols.
6. Independently replicate V44 in a laboratory, add blinded intervention-capable worlds, and extend the bounded genome beyond two state slots and fixed least-squares fitting.
7. Add adversarial worlds, negative results, and benchmarks that defeat current candidates.
8. Improve dashboard review of ASTs, proof obligations, and failure boundaries.
9. Audit halting, memory, numeric range, and sandbox limits for generated programs.
10. Independently review the formula catalog and identify incorrect or overstated human translations.

Contribution requirements:

- open an [issue](https://github.com/HmZ9874/akgm-n0/issues/new) describing the knowledge gap and verification method;
- include tests, reproduction commands, and an explicit claim boundary in pull requests;
- provide an executable definition, valid domain, independent verification, and counterexample search for every proposed formula or operator;
- preserve failed experiments and negative evidence;
- do not label a relation universal based only on a few examples.

## Reproducibility checklist

An admissible result should record:

- input snapshot and provenance digest;
- learner-visible fields;
- evaluator-only fields;
- candidate AST or opcode definition;
- parameter-fit scope;
- program commitment;
- holdout, OOD, and adversarial cases;
- complexity or token cost;
- counterexamples;
- <code>verified</code>, <code>bounded</code>, or <code>rejected</code> state;
- an explicit list of what was not proved.

## License status

This repository is public for review and collaboration, but it does not yet include an open-source license. Redistribution and modification rights have therefore not been granted. Please discuss substantial reuse with the repository owner, and open an issue if you would like to recommend an appropriate license for the code, scientific reports, and third-party data boundaries.

## Discussion

- Questions, counterexamples, and collaboration: [GitHub Issues](https://github.com/HmZ9874/akgm-n0/issues)
- Code contributions: [Pull Requests](https://github.com/HmZ9874/akgm-n0/pulls)

The project needs stricter blind tests, stronger proofs, better failure records, and independent external experiments more than it needs a larger raw formula count.
