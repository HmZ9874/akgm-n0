import assert from "node:assert/strict";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the AKGM evidence dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>AKGM-N0 · 实验汇报<\/title>/i);
  assert.match(html, /Gen 0 匿名概念形成与迁移对照/);
  assert.match(html, /77\.8%/);
  assert.match(html, /C-a50bfb846129/);
  assert.match(html, /有库 \/ 无库对照/);
  assert.match(html, /不能夸大的部分/);
  assert.doesNotMatch(html, /codex-preview|SkeletonPreview|react-loading-skeleton/);
});

test("server-renders the operation-growth evidence route", async () => {
  const response = await render("/operation");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /匿名运算生长实验：有限重复执行/);
  assert.match(html, /CAND-19673262ae5c1200/);
  assert.match(html, /盲测六项全部通过/);
  assert.match(html, /未提供/);
  assert.match(html, /事后命名/);
});

test("server-renders the mistake-replay evidence route", async () => {
  const response = await render("/mistakes");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /错题库：等价错误回放拦截实验/);
  assert.match(html, /M-5159793c74334913/);
  assert.match(html, /搜索前拦截/);
  assert.match(html, /不同写法，同一错误族/);
  assert.match(html, /旧程序族返回/);
});

test("server-renders the MetaMachine Gen 1 evidence route", async () => {
  const response = await render("/metamachine");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /MetaMachine Gen 1：匿名状态语义生长/);
  assert.match(html, /OP-5d71852caac760f3/);
  assert.match(html, /506/);
  assert.match(html, /可达的双状态回路/);
  assert.match(html, /输入结束仍由宿主决定/);
  assert.match(html, /从候选网络变成下一层基础操作/);
});

test("server-renders the indexed semantic reuse route", async () => {
  const response = await render("/indexed");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /没有乘法节点，调用自己发现的匿名程序/);
  assert.match(html, /IC-333606b7ae23dc50/);
  assert.match(html, /SEM-33bf3587fc82db18/);
  assert.match(html, /5 \/ 5 EXACT/);
  assert.match(html, /成功公式房间/);
  assert.match(html, /错题库/);
});

test("server-renders the ordered relation failure probe", async () => {
  const response = await render("/probe");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /没有命中，就不把近似答案叫作发现/);
  assert.match(html, /RUN-ordered-relation-probe-20260818T041655758967Z/);
  assert.match(html, /483/);
  assert.match(html, /IM-/);
  assert.match(html, /成功房间新增 0/);
});

test("server-renders the multi-view relational memory report", async () => {
  const response = await render("/multiview");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /从一条序列，扩展成可执行关系图/);
  assert.match(html, /RUN-multiview-relational-20260818T042820204629Z/);
  assert.match(html, /64−56/);
  assert.match(html, /M8\+23/);
  assert.match(html, /7\/8/);
  assert.match(html, /局部证据，不进入公式房间/);
});

test("server-renders the anonymous adaptive control discovery", async () => {
  const response = await render("/adaptive");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /没有提供“余数”，程序自己决定何时停止/);
  assert.match(html, /RUN-adaptive-control-20260818T052241162394Z/);
  assert.match(html, /19,200/);
  assert.match(html, /SF-0693be24cc616771/);
  assert.match(html, /S ← S − 输入 1/);
  assert.match(html, /错题库/);
});

test("server-renders the signed first-input branch discovery", async () => {
  const response = await render("/signed");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /没有给负数规则，程序自己增加优先分支/);
  assert.match(html, /RUN-signed-control-extension-20260818T064033720022Z/);
  assert.match(html, /CTRL-2f51ec5cf9134520/);
  assert.match(html, /SF-70937e5f29e9b04c/);
  assert.match(html, /S ← S \+ 输入 1/);
  assert.match(html, /−29/);
});

test("server-renders the negative second-input adapter discovery", async () => {
  const response = await render("/adapter");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /程序先改写输入，再复用已经成功的控制器/);
  assert.match(html, /RUN-second-input-adapter-20260818T071651479131Z/);
  assert.match(html, /BRANCH-1d25f9c6d653bc96/);
  assert.match(html, /SF-d3527a3977adfea1/);
  assert.match(html, /y′ ← 0 − y/);
  assert.match(html, /等价成功，不重复入库/);
});

test("server-renders the second trace-memory discovery", async () => {
  const response = await render("/trace");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /程序自己增加第二个记忆单元，并创造新的输出/);
  assert.match(html, /RUN-trace-memory-20260818T074402724916Z/);
  assert.match(html, /ADAPT-051ea7f44518dc30/);
  assert.match(html, /SF-920632cdf65ef69f/);
  assert.match(html, /M ← M − 1/);
  assert.match(html, /没有把宿主 step_count 暴露成答案/);
});

test("server-renders the anonymous decimal-structure discovery", async () => {
  const response = await render("/decimal");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /它从匿名循环候选中选出了十进位结构/);
  assert.match(html, /RUN-multistage-residual-20260818T082512954727Z/);
  assert.match(html, /TRACE-04ec46485b805d91/);
  assert.match(html, /SF-1f9f1465815a0f8c/);
  assert.match(html, /0\.1 → 0\.01 → 0\.001/);
  assert.match(html, /1 成功 \/ 4 错题/);
});

test("server-renders the MetaMachine Gen 2 milestone", async () => {
  const response = await render("/gen2");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /代码和数据进入同一内存，反例可以改变程序结构/);
  assert.match(html, /RUN-metamachine-gen2-20260818T084942319893Z/);
  assert.match(html, /G2-a9df96565a3385aa/);
  assert.match(html, /G2-258d6bb3a6a2a4ce/);
  assert.match(html, /SF-eba7a367ebb1850b/);
  assert.match(html, /SF-cd92bad6bc325a19/);
  assert.match(html, /加入反例 #3/);
  assert.match(html, /尚未自主选择/);
});

test("server-renders the MetaMachine Gen 2 dynamic-loop expansion", async () => {
  const response = await render("/gen2-loop");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /同一搜索器创造了两种底层逻辑不同的循环计算方式/);
  assert.match(html, /RUN-metamachine-gen2-loop-20260818T085824828573Z/);
  assert.match(html, /G2-9332f6b2f2533639/);
  assert.match(html, /G2-febc2f69fdad33e8/);
  assert.match(html, /SF-1663d7dccd76889c/);
  assert.match(html, /SF-b0fc08934b28e9b6/);
  assert.match(html, /加入反例 #3/);
  assert.match(html, /加入反例 #2/);
  assert.match(html, /没有乘法指令/);
  assert.match(html, /1 成功 \/ 4 错题/);
  assert.match(html, /仍未自主选中/);
});

test("server-renders the five-success formula stop gate", async () => {
  const response = await render("/gen2-five");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /不是五个候选：是五个通过盲测且互不等价的新程序/);
  assert.match(html, /RUN-metamachine-gen2-five-20260818T144931829651Z/);
  assert.match(html, /G2-4f6b5de649cfa951/);
  assert.match(html, /G2-0ac26c0cddff1f8b/);
  assert.match(html, /G2-52f45f3d817a0bbd/);
  assert.match(html, /G2-024550725be63c87/);
  assert.match(html, /G2-bf14d536a6747aa5/);
  assert.match(html, /SF-62d9ad7d2e4a333d/);
  assert.match(html, /5 成功 · .*20.*错题/);
  assert.match(html, /n²\+n\+1/);
  assert.match(html, /n!/);
  assert.match(html, /仍然不能夸大的部分/);
});

test("server-renders the second five-success control gate", async () => {
  const response = await render("/gen2-five-control");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /从固定递推继续走向比较、阈值和数据驱动停止/);
  assert.match(html, /RUN-metamachine-gen2-control-five-20260818T152003687975Z/);
  assert.match(html, /G2-f12a88cde9e4cc04/);
  assert.match(html, /G2-aa1ab30803291692/);
  assert.match(html, /G2-f5ffb2c49416a134/);
  assert.match(html, /G2-5239b0b25d4caa0f/);
  assert.match(html, /G2-de057ef1810f4943/);
  assert.match(html, /SF-c5876d5779920c09/);
  assert.match(html, /n mod 4/);
  assert.match(html, /gcd\(a,b\)/);
  assert.match(html, /⌊√n⌋/);
  assert.match(html, /18 → 23/);
});

test("server-renders the independent universal proof gate", async () => {
  const response = await render("/universal-proof");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /不再用更多样本冒充“通用”/);
  assert.match(html, /RUN-composition-universal-proof-20260818T184015881047Z/);
  assert.match(html, /645\/645/);
  assert.match(html, /UF-acf6631ac2ca1895/);
  assert.match(html, /UF-737e219163274b6c/);
  assert.match(html, /UF-7eb738379af6d614/);
  assert.match(html, /UF-585f8194a03eefe9/);
  assert.match(html, /UF-5dfab59e5699181e/);
  assert.match(html, /UF-01ebd062a9ccf8b7/);
  assert.match(html, /UF-96cd51db1a960aa9/);
  assert.match(html, /counter=n-t/);
  assert.match(html, /remainder=n-c\^2/);
  assert.match(html, /所有数字.*哪一类数字/);
  assert.match(html, /自修改指令操作数/);
  assert.match(html, /five_state_binomial_cascade/);
  assert.match(html, /three_way_signed_branch/);
  assert.match(html, /abs\(3\^n-2\^n\)/);
  assert.match(html, /组合图精确绑定/);
  assert.match(html, /已证明组件代入/);
  assert.match(html, /抽象无限精度整数转移语义/);
  assert.match(html, /其余 18 个活动候选仍为 bounded/);
});

test("server-renders the strict parametric formula proof", async () => {
  const response = await render("/parametric");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /不是 3ⁿ：同一个程序接收 a 和 n/);
  assert.match(html, /RUN-advanced-parametric-proof-20260819T024036452114Z/);
  assert.match(html, /F\(a,n\)=a\^n/);
  assert.match(html, /407\/407/);
  assert.match(html, /UF-059b87aeaf465fb1/);
  assert.match(html, /固定实例不再冒充参数化公式/);
  assert.match(html, /两个自由变量均来自运行时/);
  assert.match(html, /无固定底数与幂指令/);
  assert.match(html, /第一轮预测.*2.*实际观测为.*3/);
  assert.match(html, /本批真正新合成的 20 条自由变量程序/);
  assert.match(html, /C\(n,k\)=0 if k&gt;n else n!\/\(k!\(n-k\)!\)/);
  assert.match(html, /不把历史重分类冒充新发现/);
  assert.match(html, /LCM\(a,b\)=least common multiple/);
  assert.match(html, /MP\(a,n,m\)=a\^n mod m/);
  assert.match(html, /RUN-motif-growth-proof-20260819T030842022708Z/);
  assert.match(html, /从旧程序动机长出新程序/);
  assert.match(html, /F\(a,b,p,q,n\): F0=a, F1=b, F\(t\+2\)=p\*F\(t\+1\)\+q\*F\(t\)/);
  assert.match(html, /424\/424/);
  assert.match(html, /UF-5346bc472a30e531/);
  assert.match(html, /RUN-rewrite-growth-proof-20260819T032416653601Z/);
  assert.match(html, /从程序差异中归纳改写规则/);
  assert.match(html, /REWRITE-76109ae8a795d077/);
  assert.match(html, /F\(a,b,c,p,q,r,n\): F0=a, F1=b, F2=c/);
  assert.match(html, /444\/444/);
  assert.match(html, /UF-a2d651ea9bae624b/);
  assert.match(html, /RUN-semantic-invention-proof-20260819T035039570509Z/);
  assert.match(html, /从11条已证明微指令中归纳出新操作码16/);
  assert.match(html, /SEM-a53207275de5e536/);
  assert.match(html, /74.*→.*34/);
  assert.match(html, /467\/467/);
  assert.match(html, /UF-0f66f2b49b8d5983/);
  assert.match(html, /RUN-autonomous-learning-20260819T053250384476Z/);
  assert.match(html, /错题改变策略 · 输入顺序未知 · 系统主动提出实验/);
  assert.match(html, /POLICY-b2418d42677052c5/);
  assert.match(html, /POLICY-cfa82851e90429de/);
  assert.match(html, /固定顺序基线.*1.*5/);
  assert.match(html, /self_selected_queries_exist/);
  assert.match(html, /RUN-reasoning-optimization-20260819T062802801302Z/);
  assert.match(html, /中间结论可保存 · 推理路径可回放 · 反例触发回溯/);
  assert.match(html, /bit_length\(abs\(3\^n - 2\^n\)\)\^2/);
  assert.match(html, /旧三步基线/);
  assert.match(html, /variable_depth_path_created/);
  assert.match(html, /outperforms_fixed_depth_baseline/);
  assert.match(html, /RUN-time-forced-recurrence-20260819T072124539579Z/);
  assert.match(html, /从匿名五列证据中发现带内部时钟的非齐次递推/);
  assert.match(html, /X\(q,n,r,a,p\): X0=a, X\(t\+1\)=p\*X\(t\)\+q\*t\+r/);
  assert.match(html, /487.*487/);
  assert.match(html, /UF-2cca602555ac2af1/);
  assert.match(html, /universal_proof_passed/);
  assert.match(html, /RUN-state-window-operator-20260819T074604850848Z/);
  assert.match(html, /从已证明复制链中归纳状态窗口运算符 OP17/);
  assert.match(html, /SEM-b3d4d6be78fa6ea9/);
  assert.match(html, /2→3→4/);
  assert.match(html, /38.*→.*29/);
  assert.match(html, /SF-517d27465eef9758/);
  assert.match(html, /independent_semantic_equivalence/);
  assert.match(html, /自动归纳10个新运算符后停止/);
  assert.match(html, /RUN-ten-micro-operators-20260819T082051444327Z/);
  assert.match(html, /OP18–OP27/);
  assert.match(html, /SEM-04c6f4b1bb347f4f/);
  assert.match(html, /SEM-35bf133cbd58d9d6/);
  assert.match(html, /120.*120/);
  assert.match(html, /exactly_ten_new_semantics/);
  assert.match(html, /success_operator_room_persisted/);
  assert.match(html, /出现100个不同运算符后，程序才停止/);
  assert.match(html, /RUN-hundred-operator-evolution-20260819T092825944648Z/);
  assert.match(html, /OP28–OP127/);
  assert.match(html, /ESEM-204d24fdf54baf41/);
  assert.match(html, /ESEM-3b39bc7605525354/);
  assert.match(html, /1200.*1200/);
  assert.match(html, /exact_hundred_stop_count/);
  assert.match(html, /hundred_success_semantics_persisted/);
  assert.match(html, /反复证明定义域；失败公式自动退出活动库/);
  assert.match(html, /RUN-universal-semantic-audit-20260819T094909287070Z/);
  assert.match(html, /500.*500/);
  assert.match(html, /自然数安全 \/ 需要加法逆元/);
  assert.match(html, /错误样本已从隔离活动集合1条删到0条/);
  assert.match(html, /audit_loop_reached_fixed_point/);
  assert.match(html, /failed_semantic_is_removed_from_active_catalog/);
  assert.match(html, /归纳出带守卫退出的循环操作码OP128/);
  assert.match(html, /RUN-guarded-reduction-operator-20260819T171712489483Z/);
  assert.match(html, /SEM-61440ea9651ce7ba/);
  assert.match(html, /56.*56/);
  assert.match(html, /universal_invariant_termination_exit_proof/);
  assert.match(html, /data_dependent_control_flow_present/);
  assert.match(html, /从缩步与分片中发现两个稳定语义/);
  assert.match(html, /RUN-continuous-frontier-20260819T191023293116Z/);
  assert.match(html, /SEM-40d50eb6008bf37f/);
  assert.match(html, /SEM-11a96cb9aa1e206d/);
  assert.match(html, /OP129 · OP130/);
  assert.match(html, /nonsmooth_counterexample_enters_mistake_room/);
  assert.match(html, /CM-/);
  assert.match(html, /重复执行匿名主体.*压缩成一个新运算OP131/);
  assert.match(html, /RUN-repeat-macro-20260819T192613413918Z/);
  assert.match(html, /SEM-ea6d06e2e7226d79/);
  assert.match(html, /60.*→.*1/);
  assert.match(html, /universal_repeat_induction_proof/);
  assert.match(html, /body_parameter_is_not_fixed/);
});

test("server-renders the thousand parametric formula stop gate", async () => {
  const response = await render("/formula-1000");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /1000个不同的加减组合语义/);
  assert.match(html, /RUN-thousand-parametric-formulas-20260819T212045520045Z/);
  assert.match(html, /1000.*1000/);
  assert.match(html, /12000.*12000/);
  assert.match(html, /OP132–OP1131/);
  assert.match(html, /exact_thousand_success_stop/);
  assert.match(html, /no_overlap_with_previous_hundred/);
  assert.match(html, /invalid_and_duplicate_candidates_enter_mistake_room/);
  assert.match(html, /share one affine-additive algebraic family/);
});

test("server-renders the zero-arithmetic foundation lineage", async () => {
  const response = await render("/foundation");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /数学发展谱系：计数.*四则.*幂\/阶乘.*组合\/比例.*概率统计.*精确根.*有理区间逼近/);
  assert.match(html, /从组合结构连续发展到可认证的非平方逼近/);
  assert.match(html, /RUN-autonomous-interval-memory-20260820T031910506925Z/);
  assert.match(html, /ISEM-0ca406080fcca1af/);
  assert.match(html, /RSEM-a80a8102b32768d6/);
  assert.match(html, /BSEM-55ca95b38dcf0bfe/);
  assert.match(html, /215,194/);
  assert.match(html, /completion_equivalence_limit_object/);
  assert.match(html, /RUN-completion-boundary-probe-20260820T032056305791Z/);
  assert.match(html, /quotient_type_and_universal_stream_equivalence/);
  assert.match(html, /候选.*6.*可晋级.*0/);
  assert.match(html, /匿名候选.*546.*符号义务.*183.*183.*隐藏案例.*89.*89/);
  assert.match(html, /430b66df5e31a015/);
  assert.match(html, /universal_claim = .*false/);
  assert.match(html, /RUN-directional-difference-20260819T232617255855Z/);
  assert.match(html, /FSEM-3d1a4d19fab44d62/);
  assert.match(html, /FSEM-cf58189608902a55/);
  assert.match(html, /20.*20/);
  assert.match(html, /14.*14/);
  assert.match(html, /learner_instruction_set_contains_zero_arithmetic_operations/);
  assert.match(html, /thousand_affine_compositions_excluded_from_foundation_count/);
  assert.match(html, /旧1000条不再冒充基础发现/);
  assert.match(html, /多带升级前的能力基线/);
  assert.match(html, /RUN-foundation-capability-probe-20260819T214541150040Z/);
  assert.match(html, /single_collection_cardinality/);
  assert.match(html, /one_sided_pair_cancellation/);
  assert.match(html, /commutativity precursor/);
  assert.match(html, /finite n-ary addition\/conservation precursor/);
  assert.match(html, /同样正确时，消耗的真实token越少，奖励越高/);
  assert.match(html, /RUN-foundation-efficiency-reward-20260819T215519795417Z/);
  assert.match(html, /96.*83/);
  assert.match(html, /125.*111/);
  assert.match(html, /cheap_incorrect_program_cannot_beat_exact_program/);
  assert.match(html, /macro_calls_charge_expanded_primitive_work/);
  assert.match(html, /从匿名抵消任务发现自然数截断差/);
  assert.match(html, /RUN-reversible-cancellation-20260819T230345675203Z/);
  assert.match(html, /RSEM-6082532054ec1e05/);
  assert.match(html, /43/);
  assert.match(html, /11.*11/);
  assert.match(html, /10.*10/);
  assert.match(html, /not_misreported_as_signed_integer_subtraction/);
  assert.match(html, /两种无名符号保留了负方向/);
  assert.match(html, /RUN-directional-difference-20260819T232617255855Z/);
  assert.match(html, /DSEM-be8bf9c60762e0f0/);
  assert.match(html, /820/);
  assert.match(html, /14.*14/);
  assert.match(html, /12.*12/);
  assert.match(html, /-47/);
  assert.match(html, /negative_direction_information_is_preserved/);
  assert.match(html, /not_misreported_as_general_signed_integer_arithmetic/);
  assert.match(html, /RUN-nested-arithmetic-20260819T235525035322Z/);
  assert.match(html, /每个外层对象重新遍历全部内层对象/);
  assert.match(html, /NSEM-52a33255cdea401f/);
  assert.match(html, /1.*20/);
  assert.match(html, /13.*13/);
  assert.match(html, /反复匹配无名模板，保留未完成组/);
  assert.match(html, /PSEM-b6863ee740b31807/);
  assert.match(html, /1.*24/);
  assert.match(html, /16.*16/);
  assert.match(html, /no_multiplication_or_division_label_visible_to_learner/);
  assert.match(html, /zero_stencil_is_rejected_not_fabricated/);
  assert.match(html, /RUN-self-directed-frontier-20260820T012842538545Z/);
  assert.match(html, /不等用户点名，系统自己选择下一个结构问题/);
  assert.match(html, /WORLD-state-closure-27/);
  assert.match(html, /未指定目标时，自行发现自然数幂/);
  assert.match(html, /ASEM-4b7c892702eaa68a/);
  assert.match(html, /1.*24/);
  assert.match(html, /15.*15/);
  assert.match(html, /frontier_target_selected_without_math_name/);
  assert.match(html, /loop_replans_after_promotion/);
  assert.match(html, /RUN-autonomous-gap-resolution-20260820T020116744016Z/);
  assert.match(html, /自行发明缺失记忆，再恢复被阻塞的探索/);
  assert.match(html, /object_exclusion_memory/);
  assert.match(html, /发现下降乘积与阶乘特例/);
  assert.match(html, /XSEM-e27ac00be31ef317/);
  assert.match(html, /1.*48/);
  assert.match(html, /18.*18/);
  assert.match(html, /gap_taken_from_previous_autonomous_stop/);
  assert.match(html, /memory_scan_tokens_are_not_hidden/);
});
