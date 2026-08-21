import reportData from "../../data/zero_arithmetic_foundation_latest.json";
import probeData from "../../data/foundation_capability_probe_latest.json";
import rewardData from "../../data/foundation_efficiency_reward_latest.json";
import cancellationData from "../../data/reversible_cancellation_latest.json";
import directionalData from "../../data/directional_difference_latest.json";
import nestedArithmeticData from "../../data/nested_arithmetic_latest.json";
import selfDirectedData from "../../data/self_directed_frontier_latest.json";
import gapResolutionData from "../../data/autonomous_gap_resolution_latest.json";
import canonicalData from "../../data/autonomous_canonicalization_latest.json";
import ratioData from "../../data/autonomous_ratio_latest.json";
import finiteMassData from "../../data/autonomous_finite_mass_latest.json";
import jointData from "../../data/autonomous_joint_latest.json";
import weightedData from "../../data/autonomous_weighted_latest.json";
import rationalData from "../../data/autonomous_rational_latest.json";
import pairedData from "../../data/autonomous_paired_latest.json";
import exactRootData from "../../data/autonomous_exact_root_latest.json";
import intervalMemoryData from "../../data/autonomous_interval_memory_latest.json";
import deepAuditData from "../../data/deep_frontier_adversarial_audit_latest.json";
import completionProbeData from "../../data/completion_boundary_probe_latest.json";
import researchSummaryData from "../../data/deep_research_hour_summary_latest.json";

type Discovery = {
  foundation_level: number;
  semantic: {
    semantic_id: string;
    opcode: number;
    source_slots: number[];
    dependency_semantic_ids: string[];
    program: { program_id: string; instructions: Array<{ opcode: number }> };
  };
  posthoc_name: string;
  posthoc_formula: string;
  search: {
    task_id: string;
    candidates_evaluated: number;
    selected_source_plan: number[];
    selected_instruction_count: number;
    passed_examples: number;
    example_count: number;
    formula_or_math_name_visible_to_search: boolean;
  };
  verification: { universal_statement: string; proof_method: string; obligations: Array<{ passed: boolean }>; case_results: Array<{ passed: boolean }> };
};

type Report = {
  run_id: string;
  architecture: {
    learner_visible_representation: string;
    learner_visible_opcodes: number[];
    learner_visible_opcode_names: boolean;
    arithmetic_values_visible: boolean;
    addition_subtraction_multiplication_division_visible: boolean;
    search_grammar: string;
  };
  discoveries: Discovery[];
  capability_graph: {
    verified_foundation_count: number;
    verified_path: Array<{ node: string; human_label_added_after_proof: string }>;
    next_frontier: { learner_label: null; evaluator_only_interpretation: string; status: string };
    composite_formula_library: { record_count: number; classification: string; counts_as_foundational_discovery: boolean };
  };
  proof_summary: { obligations_passed: number; obligations_total: number; hidden_cases_passed: number; hidden_cases_total: number };
  rooms: { success: string; mistakes: string; success_count: number; mistake_count: number; hash_chained: boolean; success_proof_replayed_on_load: boolean };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; required: unknown }>;
  limitations: string[];
};

const report = reportData as Report;
const probe = probeData as {
  run_id: string;
  results: Array<{
    task_id: string;
    posthoc_evaluator_label: string;
    status: string;
    candidates_evaluated: number;
    development: { passed: number; total: number; minimum_exact_program_count: number };
    hidden: { passed: number; total: number };
  }>;
  summary: { transferred_task_count: number; failed_task_count: number; new_foundation_count: number };
  discovered_properties: Array<{ property_id: string; posthoc_interpretation: string; new_foundation: boolean }>;
  expressive_boundary_proof: { statement: string; consequence: string; finite_sampling_used_as_proof: boolean };
  gates: Array<{ gate_id: string; passed: boolean }>;
};
const reward = rewardData as {
  run_id: string;
  policy: {
    execution_token_definition: string;
    program_token_definition: string;
    exact_candidate_reward: string;
    promotion_rule: string;
    macro_accounting: string;
  };
  comparisons: Array<{
    comparison_id: string;
    selected_total_tokens: number;
    redundant_total_tokens: number;
    token_reduction: number;
    selected_reward: number;
    redundant_reward: number;
    reward_gain: number;
  }>;
  cheap_incorrect_control: { exact: boolean; total_token_cost: number; reward: number };
  gates: Array<{ gate_id: string; passed: boolean }>;
  limitations: string[];
};
const cancellation = cancellationData as {
  run_id: string;
  learner_received: { math_name: boolean; subtraction_symbol: boolean; target_formula: boolean; negative_number_representation: boolean; generic_multi_tape_opcodes: number[]; token_efficiency_reward: boolean };
  search: { candidate_count: number; exact_candidate_count: number; selected_token_cost: number; selected_reward: number; selected_program: { program_id: string; phases: Array<{ source_tapes: number[]; emit_mark: boolean }> } };
  discovery: { semantic: { semantic_id: string; opcode: number; dependency_semantic_ids: string[] }; posthoc_name: string; posthoc_formula: string; novelty_reason: string; counts_as_new_foundation: boolean };
  verification: { universal_statement: string; declared_domain: string; not_claimed: string; obligations: Array<{ passed: boolean }>; case_results: Array<{ passed: boolean }> };
  capability_graph: { verified_foundation_count: number; verified_path: string[]; next_frontier: { evaluator_only_interpretation: string; status: string } };
  rooms: { success: string; mistakes: string; success_count: number; mistake_count: number };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; required: unknown }>;
  limitations: string[];
};
const directional = directionalData as {
  run_id: string;
  learner_received: { negative_name: boolean; positive_name: boolean; subtraction_symbol: boolean; target_formula: boolean; two_anonymous_output_glyphs: string[]; generic_multi_tape_opcodes: number[] };
  search: { candidate_count: number; exact_candidate_count: number; selected_token_cost: number; selected_reward: number; selected_program: { program_id: string; phases: Array<{ source_tapes: number[]; emit_slot: number }> }; all_exact_rewards: number[] };
  discovery: { semantic: { semantic_id: string; opcode: number; dependency_semantic_ids: string[] }; posthoc_name: string; posthoc_decoding: string; posthoc_formula: string; novelty_reason: string };
  verification: { decoded_statement: string; declared_domain: string; not_claimed: string; obligations: Array<{ passed: boolean }>; case_results: Array<{ passed: boolean; decoded_value: number }> };
  capability_graph: { verified_foundation_count: number; verified_path: string[]; next_frontier: { evaluator_only_interpretation: string; status: string } };
  rooms: { success: string; mistakes: string; success_count: number; mistake_count: number };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown }>;
  limitations: string[];
};
type CycleProof = {
  posthoc_mathematical_name: string;
  posthoc_cardinality_statement: string;
  structural_statement: string;
  declared_domain: string;
  not_claimed: string;
  undefined_boundary?: string;
  obligations: Array<{ passed: boolean }>;
  case_results: Array<{ passed: boolean }>;
};
const nestedArithmetic = nestedArithmeticData as {
  run_id: string;
  learner_received: {
    multiplication_name_or_symbol: boolean;
    division_name_or_symbol: boolean;
    target_formula: boolean;
    numeric_constants: boolean;
    arithmetic_opcodes: number[];
    anonymous_capabilities: string[];
    observations: string[];
  };
  searches: {
    nested: { candidate_count: number; exact_candidate_count: number; selected_token_cost: number; selected_reward: number; selected_program: { program_id: string } };
    partition: { candidate_count: number; exact_candidate_count: number; selected_token_cost: number; selected_reward: number; selected_program: { program_id: string } };
  };
  discoveries: Array<{
    foundation_level: number;
    semantic: { semantic_id: string; opcode: number; dependency_semantic_ids: string[] };
    posthoc_name: string;
    posthoc_formula: string;
    structural_origin: string;
    proof: CycleProof;
  }>;
  capability_graph: { verified_foundation_count: number; verified_path: string[]; next_frontier: { evaluator_only_interpretation: string; status: string } };
  rooms: { nested_success: string; partition_success: string; nested_mistakes: string; partition_mistakes: string; nested_success_count: number; partition_success_count: number; nested_mistake_count: number; partition_mistake_count: number };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; required: unknown }>;
  limitations: string[];
};
const selfDirected = selfDirectedData as {
  run_id: string;
  control_logic: { selection_inputs: string[]; selection_formula: string; math_names_visible_to_controller: boolean; automatic_cycle: string[]; stop_condition: string };
  frontier_before: Array<{ world: { world_id: string; structural_signature: string; dependency_signatures: string[] }; status: string; score: number | null; reasons: string[] }>;
  selected_world: { world: { world_id: string; structural_signature: string }; status: string; score: number; reasons: string[] };
  search: { candidate_count: number; exact_candidate_count: number; selected_token_cost: number; selected_reward: number; selected_program: { program_id: string } };
  discovery: { foundation_level: number; semantic: { semantic_id: string; opcode: number; structural_signature: string }; structural_origin: string; posthoc_name: string; posthoc_formula: string; name_given_to_controller_or_search: boolean };
  verification: { declared_domain: string; not_claimed: string; obligations: Array<{ passed: boolean }>; case_results: Array<{ passed: boolean }> };
  capability_graph: { verified_foundation_count: number; verified_path: string[] };
  stop_reason: string;
  rooms: { success: string; mistakes: string; success_count: number; mistake_count: number };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; required: unknown }>;
  limitations: string[];
};
const gapResolution = gapResolutionData as {
  run_id: string;
  resumed_from: { run_id: string; blocked_world: { world: { world_id: string; structural_signature: string } }; missing_dependency: string; user_supplied_math_target: boolean };
  capability_invention: { candidate_memory_modes: number[]; mode_names_visible_to_search: boolean; selected_mode: number; proof_interpretation: string; new_dependency_signature: string; honest_comparison_token_accounting: boolean };
  search: { candidate_count: number; exact_candidate_count: number; selected_token_cost: number; selected_reward: number; selected_program: { program_id: string; filter_mode: number } };
  discovery: { foundation_level: number; semantic: { semantic_id: string; opcode: number }; structural_origin: string; posthoc_name: string; posthoc_formula: string; name_given_to_search: boolean };
  verification: { declared_domain: string; not_claimed: string; obligations: Array<{ passed: boolean }>; case_results: Array<{ passed: boolean; equality_comparison_tokens: number; primitive_execution_tokens: number }> };
  capability_graph: { verified_foundation_count: number; verified_path: string[] };
  next_frontier: { world_id: string; structural_signature: string; status: string; missing_dependency: string; posthoc_math_name: null };
  rooms: { success: string; mistakes: string; success_count: number; mistake_count: number };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; required: unknown }>;
  limitations: string[];
};

const deepStages = [
  { level: canonicalData.discovery.foundation_level, run: canonicalData.run_id, semantic: canonicalData.discovery.semantic.semantic_id, name: canonicalData.discovery.posthoc_name, formula: canonicalData.discovery.posthoc_formula, candidates: canonicalData.search.candidate_count, exact: canonicalData.search.exact_candidate_count, proof: canonicalData.verification.obligations, hidden: canonicalData.verification.case_results, mistakes: canonicalData.rooms.mistake_count },
  { level: ratioData.discovery.foundation_level, run: ratioData.run_id, semantic: ratioData.discovery.semantic.semantic_id, name: ratioData.discovery.posthoc_name, formula: ratioData.discovery.posthoc_formula, candidates: ratioData.search.candidate_count, exact: ratioData.search.exact_candidate_count, proof: ratioData.verification.obligations, hidden: ratioData.verification.case_results, mistakes: ratioData.rooms.mistake_count },
  { level: jointData.discovery.foundation_level, run: jointData.run_id, semantic: jointData.discovery.semantic.semantic_id, name: jointData.discovery.posthoc_name, formula: jointData.discovery.posthoc_formula, candidates: jointData.search.candidate_count, exact: jointData.search.exact_candidate_count, proof: jointData.verification.obligations, hidden: jointData.verification.case_results, mistakes: jointData.rooms.mistake_count },
  { level: weightedData.discovery.foundation_level, run: weightedData.run_id, semantic: weightedData.discovery.semantic.semantic_id, name: weightedData.discovery.posthoc_name, formula: weightedData.discovery.posthoc_formula, candidates: weightedData.search.candidate_count, exact: weightedData.search.exact_candidate_count, proof: weightedData.verification.obligations, hidden: weightedData.verification.case_results, mistakes: weightedData.rooms.mistake_count },
  { level: rationalData.discovery.foundation_level, run: rationalData.run_id, semantic: rationalData.discovery.semantic.semantic_id, name: rationalData.discovery.posthoc_name, formula: rationalData.discovery.posthoc_formula, candidates: rationalData.searches.difference.candidate_count + rationalData.searches.square.candidate_count, exact: rationalData.searches.difference.exact_candidate_count + rationalData.searches.square.exact_candidate_count, proof: rationalData.verification.obligations, hidden: rationalData.verification.case_results, mistakes: rationalData.rooms.mistake_count },
  { level: pairedData.discovery.foundation_level, run: pairedData.run_id, semantic: pairedData.discovery.semantic.semantic_id, name: pairedData.discovery.posthoc_name, formula: pairedData.discovery.posthoc_formula, candidates: pairedData.search.candidate_count, exact: pairedData.search.exact_candidate_count, proof: pairedData.verification.obligations, hidden: pairedData.verification.case_results, mistakes: pairedData.rooms.mistake_count },
  { level: exactRootData.discovery.foundation_level, run: exactRootData.run_id, semantic: exactRootData.discovery.semantic.semantic_id, name: exactRootData.discovery.posthoc_name, formula: exactRootData.discovery.posthoc_formula, candidates: exactRootData.search.candidate_count, exact: exactRootData.search.exact_candidate_count, proof: exactRootData.verification.obligations, hidden: exactRootData.verification.case_results, mistakes: exactRootData.rooms.mistake_count },
  { level: intervalMemoryData.discovery.foundation_level, run: intervalMemoryData.run_id, semantic: intervalMemoryData.discovery.semantic.semantic_id, name: intervalMemoryData.discovery.posthoc_name, formula: intervalMemoryData.discovery.posthoc_formula, candidates: intervalMemoryData.search.candidate_count, exact: intervalMemoryData.search.exact_candidate_count, proof: intervalMemoryData.verification.obligations, hidden: intervalMemoryData.verification.case_results, mistakes: intervalMemoryData.rooms.mistake_count },
];
const deepMistakes = deepStages.reduce((total, stage) => total + stage.mistakes, 0) + finiteMassData.rooms.mistake_count;

export default function FoundationPage() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">ZERO-ARITHMETIC FOUNDATION</p><p className="brand-name">AKGM-N0 / 数学自发展谱系</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/meta-autonomy">能力升级</a><a className="nav-link" href="/formula-1000">组合程序库</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">基础能力 {intervalMemoryData.capability_graph.verified_foundation_count}</span><span className="scope-label">DEEP AUTONOMOUS FRONTIER</span></div><h1>数学发展谱系：计数 → 四则 → 幂/阶乘 → 组合/比例 → 概率统计 → 精确根 → 有理区间逼近</h1><p className="lede">系统从上次的顺序缺口连续发展八层匿名机制；数学名称与公式只在独立证明通过后添加，失败与冗余候选进入错题库。</p><div className="run-id"><span>LATEST</span><code>{intervalMemoryData.run_id}</code><code>{deepAuditData.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{intervalMemoryData.verification.obligations.filter(x => x.passed).length}/{intervalMemoryData.verification.obligations.length}</strong><span>最新晋级证明义务</span></div><p>{completionProbeData.next_frontier.world_id}</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>学习器可见算术原语</p><strong>0</strong><span>没有加减乘除与数值常量</span></article>
      <article className="metric-card accent-violet"><p>已验证基础语义</p><strong>{intervalMemoryData.capability_graph.verified_foundation_count}</strong><span>不是把组合公式数量冒充基础能力</span></article>
      <article className="metric-card accent-amber"><p>跨层对抗执行</p><strong>{deepAuditData.passed_case_count}/{deepAuditData.case_count}</strong><span>有界穷举，明确不冒充全称证明</span></article>
      <article className="metric-card accent-slate"><p>本轮新增错题记录</p><strong>{deepMistakes}</strong><span>失败和等价冗余程序不晋级</span></article>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">ONE-HOUR DEEP RESEARCH</p><h2>从组合结构连续发展到可认证的非平方逼近</h2></div><span className="evidence-chip">LEVEL 9–16</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新增基础层</p><strong>8</strong><span>组合、比例、交集、加权、有理偏差、配对累积、精确根、区间记忆</span></article><article className="metric-card accent-violet"><p>派生但不重复计级</p><strong>{finiteMassData.derived_discovery.derived_results.length + jointData.derived_results.length + weightedData.derived_results.length + rationalData.derived_results.length + pairedData.derived_results.length}</strong><span>概率、条件概率、期望、方差、协方差等</span></article><article className="metric-card accent-amber"><p>对抗审计</p><strong>{deepAuditData.failed_case_count}</strong><span>在 {deepAuditData.case_count.toLocaleString()} 个直接执行案例中发现的反例</span></article><article className="metric-card accent-slate"><p>当前真实边界</p><strong>BLOCKED</strong><span>{completionProbeData.next_frontier.missing_dependency}</span></article></div>
      <div className="promotion-lanes">
        {deepStages.map(stage => <div className="promotion-lane" key={stage.semantic}><span>LEVEL {stage.level} · 证明后命名</span><p><strong>{stage.name}</strong></p><p>{stage.formula}</p><p>{stage.semantic} · 候选 {stage.exact}/{stage.candidates}</p><p>证明 {stage.proof.filter(item => item.passed).length}/{stage.proof.length} · 隐藏 {stage.hidden.filter(item => item.passed).length}/{stage.hidden.length}</p><p>{stage.run}</p></div>)}
      </div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>派生结果，不增加基础计数</span><p><strong>{finiteMassData.derived_discovery.posthoc_name}</strong></p><p>{finiteMassData.derived_discovery.derived_results.join(" · ")}</p><p>{jointData.derived_results.join(" · ")}</p><p>{weightedData.derived_results.join(" · ")}</p><p>{rationalData.derived_results.join(" · ")}</p><p>{pairedData.derived_results.join(" · ")}</p></div><div className="promotion-lane blocked-lane"><span>完备化边界探针 · 不晋级</span><p>{completionProbeData.finding}</p><p>候选 {completionProbeData.candidate_count} · 可晋级 {completionProbeData.promotable_candidate_count} · 基础计数 {completionProbeData.foundation_count_before} → {completionProbeData.foundation_count_after}</p><p>先前宽泛缺口：{intervalMemoryData.next_frontier.missing_dependency}</p><p>细化后缺口：{completionProbeData.next_frontier.missing_dependency}</p><p>{completionProbeData.run_id}</p></div></div>
      <div className="finding-strip"><span className="note-icon">✓</span><p><strong>审计结论：</strong>{deepAuditData.verdict}，{deepAuditData.passed_case_count}/{deepAuditData.case_count}；该审计仅补充符号证明，`universal_claim = {String(deepAuditData.universal_claim)}`。</p></div>
      <div className="finding-strip"><span className="note-icon">∑</span><p><strong>本轮总证据：</strong>匿名候选 {researchSummaryData.aggregate.anonymous_candidates_evaluated} · 符号义务 {researchSummaryData.aggregate.symbolic_obligations_passed}/{researchSummaryData.aggregate.symbolic_obligations_total} · 隐藏案例 {researchSummaryData.aggregate.hidden_cases_passed}/{researchSummaryData.aggregate.hidden_cases_total} · 总结哈希 {researchSummaryData.summary_hash.slice(0, 16)}…</p></div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">VERIFIED DEVELOPMENT PATH</p><h2>这是依赖链，不是预置公式表</h2></div><span className="evidence-chip">下一级尚未发现</span></div>
      <div className="promotion-lanes">
        {report.discoveries.map((item, index) => <div className="promotion-lane" key={item.semantic.semantic_id}><span>LEVEL {item.foundation_level} · 证明后命名</span><p><strong>{item.posthoc_name}</strong></p><p>{item.posthoc_formula}</p><p>{item.semantic.semantic_id} · 程序 {item.semantic.program.program_id}</p><p>匿名候选 {item.search.candidates_evaluated} · 选中槽 [{item.search.selected_source_plan.join(", ")}] · 依赖 {index === 0 ? "无" : item.semantic.dependency_semantic_ids.join(", ")}</p></div>)}
      </div>
      <div className="finding-strip"><span className="note-icon">→</span><p><strong>当前下一缺口：</strong>{completionProbeData.next_frontier.world_id} 需要 {completionProbeData.next_frontier.missing_dependency}，尚未晋级。</p></div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">AUTONOMOUS GAP RESOLUTION</p><h2>自行发明缺失记忆，再恢复被阻塞的探索</h2></div><span className="evidence-chip">{gapResolution.run_id}</span></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>从上次停止点恢复</span><p>{gapResolution.resumed_from.blocked_world.world.world_id}</p><p>缺失依赖：{gapResolution.resumed_from.missing_dependency}</p><p>用户提供数学目标：{String(gapResolution.resumed_from.user_supplied_math_target)}</p></div><div className="promotion-lane"><span>能力发明竞争</span><p>无名记忆模式：[{gapResolution.capability_invention.candidate_memory_modes.join(", ")}]</p><p>选中模式：{gapResolution.capability_invention.selected_mode}</p><p>{gapResolution.capability_invention.proof_interpretation}</p></div></div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FOUNDATION LEVEL 8 · AUTONOMOUS</p><h2>发现下降乘积与阶乘特例</h2></div><span className="evidence-chip">{gapResolution.resumed_from.blocked_world.world.world_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新基础语义</p><strong>{gapResolution.discovery.semantic.semantic_id}</strong><span>FOP{gapResolution.discovery.semantic.opcode} · 证明后命名</span></article><article className="metric-card accent-violet"><p>匿名候选</p><strong>{gapResolution.search.exact_candidate_count}/{gapResolution.search.candidate_count}</strong><span>只有1个记忆程序完全正确</span></article><article className="metric-card accent-amber"><p>全称证明</p><strong>{gapResolution.verification.obligations.filter(item => item.passed).length}/{gapResolution.verification.obligations.length}</strong><span>{gapResolution.verification.declared_domain}</span></article><article className="metric-card accent-slate"><p>隐藏结构测试</p><strong>{gapResolution.verification.case_results.filter(item => item.passed).length}/{gapResolution.verification.case_results.length}</strong><span>相等比较全部计token</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>自主形成的底层机制</span><p><strong>{gapResolution.capability_invention.new_dependency_signature}</strong></p><p>{gapResolution.capability_invention.proof_interpretation}</p><p>程序 {gapResolution.search.selected_program.program_id} · token {gapResolution.search.selected_token_cost}</p></div><div className="promotion-lane"><span>证明后解释</span><p><strong>{gapResolution.discovery.posthoc_name}</strong></p><p>{gapResolution.discovery.structural_origin}</p><p>{gapResolution.discovery.posthoc_formula}</p></div></div>
      <div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>当时不允许夸大</span><p>{gapResolution.verification.not_claimed}</p><p>在该历史运行时，组合数与概率尚未发现；本轮后续运行已补上对应证据。</p></div><div className="promotion-lane blocked-lane"><span>成功与错题房间</span><p>{gapResolution.rooms.success}</p><p>{gapResolution.rooms.mistakes} · {gapResolution.rooms.mistake_count}条</p></div></div>
      <div className="gate-grid">{gapResolution.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">SELF-DIRECTED FRONTIER LOOP</p><h2>不等用户点名，系统自己选择下一个结构问题</h2></div><span className="evidence-chip">{selfDirected.run_id}</span></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>自动闭环</span>{selfDirected.control_logic.automatic_cycle.map((item, index) => <p key={item}>{index + 1}. {item}</p>)}</div><div className="promotion-lane"><span>选题评分</span><p>{selfDirected.control_logic.selection_inputs.join(" · ")}</p><p><strong>{selfDirected.control_logic.selection_formula}</strong></p><p>数学名称对控制器可见：{String(selfDirected.control_logic.math_names_visible_to_controller)}</p></div></div>
      <div className="gate-grid">{selfDirected.frontier_before.map(item => <div className="gate-item" key={item.world.world_id}><span className={`gate-light ${item.status === "ready" ? "passed" : item.status === "dependency_blocked" ? "failed" : "passed"}`}/><div><strong>{item.world.world_id} · {item.status}</strong><span>{item.world.structural_signature} · score {String(item.score)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FOUNDATION LEVEL 7 · AUTONOMOUS</p><h2>未指定目标时，自行发现自然数幂</h2></div><span className="evidence-chip">{selfDirected.selected_world.world.world_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新基础语义</p><strong>{selfDirected.discovery.semantic.semantic_id}</strong><span>FOP{selfDirected.discovery.semantic.opcode} · 证明后命名</span></article><article className="metric-card accent-violet"><p>匿名候选</p><strong>{selfDirected.search.exact_candidate_count}/{selfDirected.search.candidate_count}</strong><span>只有1个递归程序完全正确</span></article><article className="metric-card accent-amber"><p>全称证明</p><strong>{selfDirected.verification.obligations.filter(item => item.passed).length}/{selfDirected.verification.obligations.length}</strong><span>{selfDirected.verification.declared_domain}</span></article><article className="metric-card accent-slate"><p>隐藏递归测试</p><strong>{selfDirected.verification.case_results.filter(item => item.passed).length}/{selfDirected.verification.case_results.length}</strong><span>包含空控制集合单位情形</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>控制器选择的匿名结构</span><p>{selfDirected.selected_world.world.structural_signature}</p><p>{selfDirected.discovery.structural_origin}</p><p>程序 {selfDirected.search.selected_program.program_id} · token {selfDirected.search.selected_token_cost}</p></div><div className="promotion-lane"><span>证明后解释</span><p><strong>{selfDirected.discovery.posthoc_name}</strong></p><p>{selfDirected.discovery.posthoc_formula}</p><p>名称预先可见：{String(selfDirected.discovery.name_given_to_controller_or_search)}</p></div></div>
      <div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>不允许夸大</span><p>{selfDirected.verification.not_claimed}</p><p>系统仍依赖已注册的匿名世界生成器，尚不能凭空发明任意传感器。</p></div><div className="promotion-lane blocked-lane"><span>成功与错题房间</span><p>{selfDirected.rooms.success}</p><p>{selfDirected.rooms.mistakes} · {selfDirected.rooms.mistake_count}条</p></div></div>
      <div className="gate-grid">{selfDirected.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FOUNDATION LEVEL 6</p><h2>反复匹配无名模板，保留未完成组</h2></div><span className="evidence-chip">{nestedArithmetic.run_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新基础语义</p><strong>{nestedArithmetic.discoveries[1].semantic.semantic_id}</strong><span>FOP{nestedArithmetic.discoveries[1].semantic.opcode} · 证明后命名</span></article><article className="metric-card accent-violet"><p>匿名候选</p><strong>{nestedArithmetic.searches.partition.exact_candidate_count}/{nestedArithmetic.searches.partition.candidate_count}</strong><span>只有1个结构程序完全正确</span></article><article className="metric-card accent-amber"><p>全称证明</p><strong>{nestedArithmetic.discoveries[1].proof.obligations.filter(item => item.passed).length}/{nestedArithmetic.discoveries[1].proof.obligations.length}</strong><span>{nestedArithmetic.discoveries[1].proof.declared_domain}</span></article><article className="metric-card accent-slate"><p>隐藏分组测试</p><strong>{nestedArithmetic.discoveries[1].proof.case_results.filter(item => item.passed).length}/{nestedArithmetic.discoveries[1].proof.case_results.length}</strong><span>零模板明确拒绝</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>结构任务</span><p>{nestedArithmetic.discoveries[1].structural_origin}</p><p>程序 {nestedArithmetic.searches.partition.selected_program.program_id} · token {nestedArithmetic.searches.partition.selected_token_cost}</p></div><div className="promotion-lane"><span>证明后解释</span><p><strong>{nestedArithmetic.discoveries[1].posthoc_name}</strong></p><p>{nestedArithmetic.discoveries[1].posthoc_formula}</p><p>边界：{nestedArithmetic.discoveries[1].proof.undefined_boundary}</p></div></div>
      <div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>不允许夸大</span><p>{nestedArithmetic.discoveries[1].proof.not_claimed}</p><p>当前输出商标记与余数对象，不产生分数或小数。</p></div><div className="promotion-lane blocked-lane"><span>成功与错题房间</span><p>{nestedArithmetic.rooms.partition_success}</p><p>{nestedArithmetic.rooms.partition_mistakes} · {nestedArithmetic.rooms.partition_mistake_count}条</p></div></div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FOUNDATION LEVEL 5</p><h2>每个外层对象重新遍历全部内层对象</h2></div><span className="evidence-chip">{nestedArithmetic.run_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新基础语义</p><strong>{nestedArithmetic.discoveries[0].semantic.semantic_id}</strong><span>FOP{nestedArithmetic.discoveries[0].semantic.opcode} · 证明后命名</span></article><article className="metric-card accent-violet"><p>匿名候选</p><strong>{nestedArithmetic.searches.nested.exact_candidate_count}/{nestedArithmetic.searches.nested.candidate_count}</strong><span>只有1个结构程序完全正确</span></article><article className="metric-card accent-amber"><p>全称证明</p><strong>{nestedArithmetic.discoveries[0].proof.obligations.filter(item => item.passed).length}/{nestedArithmetic.discoveries[0].proof.obligations.length}</strong><span>{nestedArithmetic.discoveries[0].proof.declared_domain}</span></article><article className="metric-card accent-slate"><p>隐藏配对测试</p><strong>{nestedArithmetic.discoveries[0].proof.case_results.filter(item => item.passed).length}/{nestedArithmetic.discoveries[0].proof.case_results.length}</strong><span>每个有序对象对恰好一次</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>学习器真正看到的东西</span><p>{nestedArithmetic.learner_received.anonymous_capabilities.join(" · ")}</p><p>未看到乘号、乘法名称、数值常量或目标公式。</p><p>程序 {nestedArithmetic.searches.nested.selected_program.program_id} · token {nestedArithmetic.searches.nested.selected_token_cost}</p></div><div className="promotion-lane"><span>证明后解释</span><p><strong>{nestedArithmetic.discoveries[0].posthoc_name}</strong></p><p>{nestedArithmetic.discoveries[0].structural_origin}</p><p>{nestedArithmetic.discoveries[0].posthoc_formula}</p></div></div>
      <div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>不允许夸大</span><p>{nestedArithmetic.discoveries[0].proof.not_claimed}</p><p>当前只证明有限集合基数上的自然数语义。</p></div><div className="promotion-lane blocked-lane"><span>成功与错题房间</span><p>{nestedArithmetic.rooms.nested_success}</p><p>{nestedArithmetic.rooms.nested_mistakes} · {nestedArithmetic.rooms.nested_mistake_count}条</p></div></div>
      <div className="gate-grid">{nestedArithmetic.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FOUNDATION LEVEL 4</p><h2>两种无名符号保留了负方向</h2></div><span className="evidence-chip">{directional.run_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新基础语义</p><strong>{directional.discovery.semantic.semantic_id}</strong><span>FOP{directional.discovery.semantic.opcode} · 已证明后命名</span></article><article className="metric-card accent-violet"><p>匿名候选</p><strong>{directional.search.exact_candidate_count}/{directional.search.candidate_count}</strong><span>两个等价程序只差剩余阶段顺序</span></article><article className="metric-card accent-amber"><p>全称证明</p><strong>{directional.verification.obligations.filter(item => item.passed).length}/{directional.verification.obligations.length}</strong><span>{directional.verification.declared_domain}</span></article><article className="metric-card accent-slate"><p>隐藏方向测试</p><strong>{directional.verification.case_results.filter(item => item.passed).length}/{directional.verification.case_results.length}</strong><span>最小解码值 {Math.min(...directional.verification.case_results.map(item => item.decoded_value))}</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>学习器真正看到的东西</span><p>两个无名输出符号：[{directional.learner_received.two_anonymous_output_glyphs.join(", ")}]</p><p>操作码：[{directional.learner_received.generic_multi_tape_opcodes.join(", ")}]</p><p>未看到负数名称、减号或目标公式。</p></div><div className="promotion-lane"><span>证明后解释</span><p><strong>{directional.discovery.posthoc_name}</strong></p><p>{directional.discovery.posthoc_decoding}</p><p>{directional.verification.decoded_statement}</p></div></div>
      <div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>不允许夸大</span><p>{directional.verification.not_claimed}</p><p>它能对两个自然数输入保留负结果，但还不能直接处理两个已带符号的输入。</p></div><div className="promotion-lane blocked-lane"><span>程序与房间</span><p>{directional.search.selected_program.program_id} · token {directional.search.selected_token_cost}</p><p>成功：{directional.rooms.success}</p><p>错题：{directional.rooms.mistakes} · {directional.rooms.mistake_count}条</p></div></div>
      <div className="gate-grid">{directional.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FOUNDATION LEVEL 3</p><h2>从匿名抵消任务发现自然数截断差</h2></div><span className="evidence-chip">{cancellation.run_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>新基础语义</p><strong>{cancellation.discovery.semantic.semantic_id}</strong><span>FOP{cancellation.discovery.semantic.opcode} · 依赖计数与加法</span></article><article className="metric-card accent-violet"><p>匿名候选</p><strong>{cancellation.search.exact_candidate_count}/{cancellation.search.candidate_count}</strong><span>只有1个程序完全达成</span></article><article className="metric-card accent-amber"><p>全称证明</p><strong>{cancellation.verification.obligations.filter(item => item.passed).length}/{cancellation.verification.obligations.length}</strong><span>{cancellation.verification.declared_domain}</span></article><article className="metric-card accent-slate"><p>隐藏抵消</p><strong>{cancellation.verification.case_results.filter(item => item.passed).length}/{cancellation.verification.case_results.length}</strong><span>token成本 {cancellation.search.selected_token_cost}</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>模型选中的两阶段程序</span>{cancellation.search.selected_program.phases.map((phase, index) => <p key={index}>阶段 {index + 1}：同步访问带 [{phase.source_tapes.join(", ")}] · {phase.emit_mark ? "输出标记" : "不输出"}</p>)}<p>程序 {cancellation.search.selected_program.program_id}</p></div><div className="promotion-lane"><span>证明后才命名</span><p><strong>{cancellation.discovery.posthoc_name}</strong></p><p>{cancellation.discovery.posthoc_formula}</p><p>{cancellation.discovery.novelty_reason}</p></div></div>
      <div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>不允许夸大</span><p><strong>这还不是完整减法。</strong></p><p>{cancellation.verification.not_claimed}</p><p>当右侧较大时只输出0，尚不会保留负方向。</p></div><div className="promotion-lane blocked-lane"><span>基础房间</span><p>成功：{cancellation.rooms.success}</p><p>错题：{cancellation.rooms.mistakes} · {cancellation.rooms.mistake_count}条</p></div></div>
      <div className="gate-grid">{cancellation.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">PRE-UPGRADE BLIND PROBE</p><h2>多带升级前的能力基线</h2></div><span className="evidence-chip">{probe.run_id}</span></div>
      <div className="metric-grid"><article className="metric-card accent-cyan"><p>成功迁移</p><strong>{probe.summary.transferred_task_count}/6</strong><span>计数与集合合并族</span></article><article className="metric-card accent-violet"><p>新基础语义</p><strong>{probe.summary.new_foundation_count}</strong><span>已有能力泛化不重复计数</span></article><article className="metric-card accent-amber"><p>能力边界</p><strong>{probe.summary.failed_task_count}</strong><span>抵消 · 矩形重复 · 等组提取</span></article><article className="metric-card accent-slate"><p>新性质前兆</p><strong>{probe.discovered_properties.length}</strong><span>交换顺序不变 · 有限多元扩展</span></article></div>
      <div className="gate-grid">{probe.results.map(item => <div className="gate-item" key={item.task_id}><span className={`gate-light ${item.status === "transferred" ? "passed" : "failed"}`}/><div><strong>{item.posthoc_evaluator_label}</strong><span>开发 {item.development.passed}/{item.development.total} · 隐藏 {item.hidden.passed}/{item.hidden.total} · 候选 {item.candidates_evaluated}</span></div></div>)}</div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>它额外表现出的性质</span>{probe.discovered_properties.map(item => <p key={item.property_id}><strong>{item.posthoc_interpretation}</strong> · 不重复计为新基础</p>)}</div><div className="promotion-lane blocked-lane"><span>表达能力证明</span><p>{probe.expressive_boundary_proof.statement}</p><p>{probe.expressive_boundary_proof.consequence}</p></div></div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">TOKEN EFFICIENCY REWARD</p><h2>同样正确时，消耗的真实token越少，奖励越高</h2></div><span className="evidence-chip">{reward.run_id}</span></div>
      <div className="metric-grid">{reward.comparisons.map(item => <article className="metric-card accent-cyan" key={item.comparison_id}><p>{item.comparison_id}</p><strong>{item.redundant_total_tokens}→{item.selected_total_tokens}</strong><span>节省 {item.token_reduction} token · 奖励 +{item.reward_gain}</span></article>)}<article className="metric-card accent-amber"><p>便宜但错误</p><strong>{reward.cheap_incorrect_control.exact ? "误晋级" : "已拦截"}</strong><span>正确性是硬门，不能用低成本换通过</span></article><article className="metric-card accent-slate"><p>宏运算计费</p><strong>完整展开</strong><span>不允许一次宏调用隐藏底层工作</span></article></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>奖励公式</span><p><strong>{reward.policy.exact_candidate_reward}</strong></p><p>{reward.policy.execution_token_definition}</p><p>{reward.policy.program_token_definition}</p></div><div className="promotion-lane blocked-lane"><span>防止钻空子</span><p>{reward.policy.promotion_rule}</p><p>{reward.policy.macro_accounting}</p></div></div>
      <div className="gate-grid">{reward.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "失败"}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>基础语义晋级条件</h2></div><span className="evidence-chip">{report.rooms.success_count}/2 已持久化</span></div><div className="gate-grid">{report.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)} / {typeof gate.required === "object" ? JSON.stringify(gate.required) : String(gate.required)}</span></div></div>)}</div></section>

    <section className="content-grid lower-grid"><article className="surface"><div className="section-heading"><div><p className="eyebrow">RECLASSIFICATION</p><h2>旧1000条不再冒充基础发现</h2></div></div><p>{report.capability_graph.composite_formula_library.record_count} 条仍保留为可执行组合程序，但基础发现计数为 <strong>0</strong>。</p><p>当前新谱系只承认已证明的“计数 → 加法”两级。</p></article><article className="surface limitations-card"><div className="section-heading"><div><p className="eyebrow">BOUNDARIES</p><h2>还不能宣称的能力</h2></div></div><ol className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol></article></section>

    <footer><div><span className="footer-mark">AKGM-N0</span><span>零算术符号机 · 非 Transformer · 证明后命名</span></div><code>{report.rooms.success}</code></footer>
  </main>;
}
