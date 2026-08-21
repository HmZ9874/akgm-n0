import type { Metadata } from "next";
import reportData from "../../data/parametric_power_proof_latest.json";
import finalData from "../../data/advanced_parametric_proof_latest.json";
import motifData from "../../data/motif_growth_proof_latest.json";
import rewriteData from "../../data/rewrite_growth_proof_latest.json";
import semanticData from "../../data/semantic_invention_proof_latest.json";
import learningData from "../../data/autonomous_learning_optimization_latest.json";
import reasoningData from "../../data/reasoning_optimization_latest.json";
import timeForcedData from "../../data/time_forced_recurrence_latest.json";
import stateWindowData from "../../data/state_window_operator_latest.json";
import tenOperatorData from "../../data/ten_micro_operator_invention_latest.json";
import hundredOperatorData from "../../data/hundred_operator_evolution_latest.json";
import universalAuditData from "../../data/universal_semantic_audit_latest.json";
import guardedReductionData from "../../data/guarded_reduction_operator_latest.json";
import continuousFrontierData from "../../data/continuous_frontier_latest.json";
import repeatMacroData from "../../data/repeat_macro_latest.json";

export const metadata: Metadata = {
  title: "参数化公式 · AKGM-N0",
  description: "从固定底数实例跨越到二输入自由变量公式的发现与证明。",
};

type Obligation = { obligation_id: string; passed: boolean; evidence: string };
type Report = {
  run_id: string;
  source_discovery_run_id: string;
  formula: string;
  domain: string;
  candidate_id: string;
  parametric_room_record_id: string;
  strict_parametric_formula_count: number;
  proof_obligation_count: number;
  proof_obligation_passed_count: number;
  invariants: string[];
  termination_measure: string;
  discovery_trace: {
    cegis_round_count: number;
    first_round_was_fixed_base_instance: boolean;
    counterexample_that_forced_abstraction: { inputs: number[]; predicted: number; observed: number };
    unseen_bases: number[];
    unseen_cases_passed: number;
    unseen_case_count: number;
  };
  proof: { verifier_version: string; obligations: Obligation[] };
  autonomy_boundary: { learner_selected: string; host_supplied: string; posthoc_only: string };
  limitations: string[];
};

const report = reportData as Report;
const finalReport = finalData as {
  run_id: string;
  strict_formula_total: number;
  batch_newly_synthesized_count: number;
  historical_reclassified_count: number;
  proof_obligation_count: number;
  proof_obligation_passed_count: number;
  batch_new_formulas: Array<{ formula: string; mechanism: string; record_id: string }>;
};
const motifReport = motifData as {
  run_id: string;
  formula: string;
  strict_formula_total_after: number;
  room_proof_obligation_count: number;
  room_proof_obligation_passed_count: number;
  invariants: string[];
  termination_measure: string;
  strict_room_record: { room_record_id: string };
  discovery_summary: {
    learned_motif_count: number;
    cegis_round_count: number;
    sealed_passed: number;
    sealed_total: number;
    mistakes_recorded: number;
    first_counterexample: { inputs: number[]; predicted: number; observed: number };
  };
  autonomy_boundary: { learned: string; grown: string; host_supplied: string };
};
const rewriteReport = rewriteData as {
  run_id: string;
  formula: string;
  strict_formula_total_after: number;
  room_proof_obligation_count: number;
  room_proof_obligation_passed_count: number;
  termination_measure: string;
  strict_room_record: { room_record_id: string };
  discovery_summary: {
    rewrite_rule: { rule_id: string; observed_copy_chain_widths: number[]; edit_sequence: string[] };
    candidate_instruction_count: number;
    cegis_round_count: number;
    sealed_passed: number;
    sealed_total: number;
    mistakes_recorded: number;
    first_counterexample: { inputs: number[]; predicted: number; observed: number };
  };
  autonomy_boundary: { learned: string; applied: string; host_supplied: string };
};
const semanticReport = semanticData as {
  run_id: string;
  formula: string;
  strict_formula_total_after: number;
  room_proof_obligation_count: number;
  room_proof_obligation_passed_count: number;
  strict_room_record: { room_record_id: string };
  invented_semantic: {
    semantic_id: string;
    opcode: number;
    supporting_occurrence_count: number;
    compression_saving_per_use: number;
  };
  discovery_summary: {
    compressed_instruction_count: number;
    equivalent_expanded_instruction_count: number;
    crossed_old_instruction_limit: boolean;
    cegis_round_count: number;
    sealed_passed: number;
    sealed_total: number;
    mistakes_recorded: number;
    first_counterexample: { inputs: number[]; predicted: number; observed: number };
  };
  autonomy_boundary: { invented: string; verified: string; host_supplied: string };
};
const learningReport = learningData as {
  run_id: string;
  policy: {
    initial_policy_id: string;
    updated_policy_id: string;
    success_example_count: number;
    failure_example_count_after: number;
    feature_count: number;
    new_mistake_ids: string[];
  };
  blind_task: {
    input_permutations_searched: number;
    host_seed_observation_count: number;
    self_selected_experiment_count: number;
    total_observation_count: number;
    selected_rows: number[][];
  };
  sealed_results: Array<{ passed: boolean }>;
  baseline: { sealed_results: Array<{ passed: boolean }> };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string; threshold: number | string }>;
  limitations: string[];
};
const reasoningReport = reasoningData as {
  run_id: string;
  reasoner: {
    primitive_operation_count: number;
    maximum_depth: number;
    maximum_nodes: number;
    host_selected_episode_operation_pool: boolean;
  };
  experiment: {
    host_seed_count: number;
    self_selected_query_count: number;
    total_observation_count: number;
    self_selected_queries: Array<{ input_row: number[]; distinct_output_count: number; disagreeing_candidate_pairs: number }>;
  };
  result: {
    reasoning_depth: number;
    reasoning_step_count: number;
    posthoc_interpretation: string;
    component_proof_records: string[];
    layers: Array<{ depth: number; programs_generated: number; retained_states: number; exact_states: number }>;
  };
  sealed_transfer: { passed: number; total: number };
  fixed_depth_baseline: { sealed_passed: number; sealed_total: number; maximum_graph_nodes: number };
  mistake_feedback: { count: number };
  verification: { verifier_version: string; passed: boolean; obligations: Array<{ obligation_id: string; passed: boolean }> };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string; threshold: number | string }>;
  limitations: string[];
};
const timeForcedReport = timeForcedData as {
  run_id: string;
  formula: string;
  invented_semantic_id: string;
  experiment: {
    host_seed_count: number;
    self_selected_query_count: number;
    total_observation_count: number;
    self_selected_queries: Array<{ input_row: number[]; distinct_output_count: number; disagreeing_candidate_pairs: number }>;
  };
  sealed_results: Array<{ passed: boolean }>;
  mistake_ids: string[];
  strict_room_record: { room_record_id: string };
  strict_formula_total_before: number;
  strict_formula_total_after: number;
  proof: { obligations: Array<{ passed: boolean }> };
  room_proof_obligation_count: number;
  room_proof_obligation_passed_count: number;
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string; threshold: number | string }>;
  limitations: string[];
};
const stateWindowReport = stateWindowData as {
  run_id: string;
  posthoc_symbol: string;
  invented_operator: {
    semantic_id: string;
    opcode: number;
    source_record_ids: string[];
    observed_widths: number[];
    supporting_occurrence_count: number;
    effect_schema: string;
  };
  semantic_verification: { obligations: Array<{ passed: boolean }> };
  demonstration: {
    unseen_window_width: number;
    compressed_instruction_count: number;
    expanded_instruction_count: number;
    posthoc_formula: string;
    success_room_record: { room_record_id: string };
  };
  experiment: {
    self_selected_query_count: number;
    self_selected_queries: Array<{ input_row: number[]; distinct_output_count: number; disagreeing_candidate_pairs: number }>;
  };
  sealed_results: Array<{ passed: boolean }>;
  mistake_ids: string[];
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string | number[]; threshold: number | string | number[] }>;
  limitations: string[];
};
const tenOperatorReport = tenOperatorData as {
  run_id: string;
  stop_rule: { requested_new_operator_count: number; actual_new_operator_count: number; program_stopped: boolean };
  source_evidence: { independently_proven_word_program_count: number; formula_or_operator_names_given_to_miner: boolean };
  operators: Array<{
    operator_id: string;
    opcode: number;
    posthoc_effect: string;
    supporting_occurrence_count: number;
    source_program_count: number;
  }>;
  verification: { passed_probe_case_count: number; probe_case_count: number };
  semantic_room: { path: string; batch_record_count: number; hash_chained: boolean; proof_replayed_on_load: boolean };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string | number[]; required: number | string | number[] }>;
  limitations: string[];
};
const hundredOperatorReport = hundredOperatorData as {
  run_id: string;
  stop_rule: { requested_new_operator_count: number; actual_new_operator_count: number; program_stopped: boolean };
  evolution: {
    generation: number;
    seed_operator_count: number;
    formula_or_operator_names_given_to_search: boolean;
    selection_rule: string;
    operand_roles_discovered_from_seeds: string[];
    expanded_instruction_length_distribution: Record<string, number>;
  };
  operators: Array<{
    operator_id: string;
    opcode: number;
    posthoc_effect: string;
    coefficient_vector: number[];
    expanded_instruction_count: number;
  }>;
  verification: { passed_probe_case_count: number; probe_case_count: number; operator_results: Array<{ passed: boolean }> };
  semantic_room: { path: string; batch_record_count: number; hash_chained: boolean; proof_replayed_on_load: boolean };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string | number[]; required: number | string | number[] }>;
  limitations: string[];
};
const universalAuditReport = universalAuditData as {
  run_id: string;
  meaning_of_universal: { formal_domain: string; proof_rule: string; not_claimed: string };
  loop: {
    input_operator_count: number;
    active_operator_count: number;
    removed_operator_count: number;
    round_count: number;
    converged: boolean;
    rounds: Array<{ round: number; input_count: number; removed_count: number; survivor_count: number; stable_round_count: number }>;
  };
  proof_summary: {
    active_semantics_passed: number;
    active_semantics_total: number;
    obligations_passed: number;
    obligations_total: number;
    natural_number_safe_without_subtraction_count: number;
    requires_additive_inverse_count: number;
  };
  negative_control: { description: string; removed_from_active_catalog: boolean; isolated_loop_rounds: Array<{ round: number; input_count: number; removed_count: number; survivor_count: number }> };
  active_catalog: { path: string; count: number; contains_only_passed_audits: boolean };
  rejection_room: { path: string; new_actual_rejections: number; history_is_preserved: boolean };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string; required: number | string }>;
  limitations: string[];
};
const guardedReductionReport = guardedReductionData as {
  run_id: string;
  invented_operator: {
    semantic_id: string;
    opcode: number;
    source_record_ids: string[];
    supporting_occurrence_count: number;
    normalized_opcode_shape: number[];
  };
  posthoc_interpretation: { name: string; effect: string; provided_to_learner: boolean };
  discovery: { proven_word_programs_scanned: number; distinct_backward_loop_shapes: number; supporting_source_count: number };
  verification: { obligations: Array<{ obligation_id: string; passed: boolean }>; case_results: Array<{ passed: boolean }> };
  demonstration: { inputs: { remainder: number; count: number; divisor: number }; result: { final_remainder: number; final_count: number; iteration_count: number } };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string | number[]; required: number | string }>;
  control_semantic_room: { event_hash: string };
  limitations: string[];
};
const continuousFrontierReport = continuousFrontierData as {
  run_id: string;
  exploration_scale: {
    anonymous_world_count: number;
    local_observation_count: number;
    partition_observation_count: number;
    local_candidate_count: number;
    partition_candidate_count: number;
    total_candidate_count: number;
  };
  discovered_semantics: Array<{
    semantic: { semantic_id: string; opcode: number; forward_form?: string; backward_form?: string; denominator_power?: number; anchor?: string; aggregation?: string; width_power?: number };
    posthoc_name: string;
    name_given_to_learner: boolean;
  }>;
  verification: {
    formal_domain: string;
    obligations: Array<{ obligation_id: string; passed: boolean }>;
    local_cases: Array<{ passed: boolean }>;
    partition_cases: Array<{ passed: boolean }>;
    additivity_cases: Array<{ passed: boolean }>;
  };
  counterexample: { kind: string; forward_value: string; backward_value: string; rejected: boolean; mistake_record: { mistake_id: string } };
  demonstrations: {
    anonymous_local_world: Array<{ step: string; forward: string; backward: string }>;
    anonymous_partition_world: Array<{ partition_count: number; value: string }>;
  };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string | boolean | object; required: number | string | boolean }>;
  limitations: string[];
};
const repeatMacroReport = repeatMacroData as {
  run_id: string;
  invented_operator: {
    semantic_id: string;
    opcode: number;
    source_record_ids: string[];
    supporting_occurrence_count: number;
    observed_body_shapes: number[][];
  };
  posthoc_interpretation: { name: string; contract: string; provided_to_learner: boolean };
  compression: {
    macro_instruction_count: number;
    demonstration_body_instruction_count: number;
    demonstration_repeat_count: number;
    expanded_body_instruction_count: number;
    saved_body_dispatches: number;
    semantic_body_is_a_parameter: boolean;
  };
  demonstrations: {
    repeat_anonymous_increment: { final_state: number[]; iteration_count: number };
    repeat_anonymous_pair_transition: { final_state: number[]; iteration_count: number };
  };
  verification: { obligations: Array<{ passed: boolean }>; case_results: Array<{ passed: boolean }> };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | string; required: number | string }>;
  limitations: string[];
};

const labels: Record<string, string> = {
  exact_program_structure: "程序结构精确绑定",
  both_runtime_inputs_are_free: "两个自由变量均来自运行时",
  no_fixed_base_or_power_opcode: "无固定底数与幂指令",
  induction_base: "外层归纳起点",
  inner_induction_step: "内层累积不变量",
  inner_exit_correctness: "内层出口",
  outer_induction_step: "外层递推",
  zero_boundary_cases: "零边界",
  termination: "嵌套循环终止",
  exit_correctness: "最终出口",
};

export default function ParametricFormulaPage() {
  const score = `${semanticReport.room_proof_obligation_passed_count}/${semanticReport.room_proof_obligation_count}`;
  const latestScore = `${timeForcedReport.room_proof_obligation_passed_count}/${timeForcedReport.room_proof_obligation_count}`;
  const rewriteScore = `${rewriteReport.room_proof_obligation_passed_count}/${rewriteReport.room_proof_obligation_count}`;
  const motifScore = `${motifReport.room_proof_obligation_passed_count}/${motifReport.room_proof_obligation_count}`;
  const counterexample = report.discovery_trace.counterexample_that_forced_abstraction;
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">aⁿ</span><div><p className="eyebrow">STRICT PARAMETRIC FORMULA</p><p className="brand-name">AKGM-N0 / Free-variable discovery</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/formula-1000">1000公式</a><a className="nav-link" href="/universal-proof">历史程序证明</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">严格公式库 {timeForcedReport.strict_formula_total_after} 条</span><span className="scope-label">FREE RUNTIME VARIABLES</span></div><h1>不是 3ⁿ：同一个程序接收 a 和 n</h1><p className="lede">模型已从自由变量公式推进到循环动机、程序改写、底层语义发明与可回放的多步推理。最新发现又加入内部时钟，从匿名五列证据中形成新的非齐次递推公式。</p><div className="run-id"><span>RUN</span><code>{timeForcedReport.run_id}</code><code>{finalReport.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{latestScore}</strong><span>证明义务通过</span></div><p>{timeForcedReport.formula}</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>严格公式库</p><strong>{timeForcedReport.strict_formula_total_after}</strong><span>既有公式 · 生长 · 改写 · 语义发明 · 时钟递推</span></article>
      <article className="metric-card accent-violet"><p>本批真正新增</p><strong>{finalReport.batch_newly_synthesized_count}</strong><span>不把历史重分类冒充新发现</span></article>
      <article className="metric-card accent-amber"><p>aⁿ 未见底数</p><strong>{report.discovery_trace.unseen_cases_passed}/{report.discovery_trace.unseen_case_count}</strong><span>{report.discovery_trace.unseen_bases.join(" · ")}</span></article>
      <article className="metric-card accent-slate"><p>历史重分类</p><strong>{finalReport.historical_reclassified_count}</strong><span>重新证明，但不计本轮新发现</span></article>
    </section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">HIGHER-ORDER SEMANTIC COMPRESSION</p><h2>把“重复执行匿名主体”压缩成一个新运算OP131</h2></div><span className="evidence-chip">{repeatMacroReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>新高阶操作码</p><strong>OP{repeatMacroReport.invented_operator.opcode}</strong><span>{repeatMacroReport.invented_operator.semantic_id}</span></article><article className="metric-card accent-violet"><p>已证明来源</p><strong>{repeatMacroReport.invented_operator.source_record_ids.length}</strong><span>{repeatMacroReport.invented_operator.supporting_occurrence_count}个循环 · {repeatMacroReport.invented_operator.observed_body_shapes.length}种不同主体</span></article><article className="metric-card accent-amber"><p>展开等价</p><strong>{repeatMacroReport.verification.case_results.filter(item => item.passed).length}/{repeatMacroReport.verification.case_results.length}</strong><span>零次、一次与多次 · 四类状态转换</span></article><article className="metric-card accent-slate"><p>压缩演示</p><strong>{repeatMacroReport.compression.expanded_body_instruction_count}→{repeatMacroReport.compression.macro_instruction_count}</strong><span>一次宏调用，主体仍执行 {repeatMacroReport.compression.demonstration_repeat_count} 次</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>证明后命名</span><p><strong>{repeatMacroReport.posthoc_interpretation.name}</strong></p><p>{repeatMacroReport.posthoc_interpretation.contract}</p><p>主体操作是参数，不固定为加法或某个公式。</p></div><div className="promotion-lane blocked-lane"><span>两个匿名主体演示</span><p>单状态重复20次：最终状态 [{repeatMacroReport.demonstrations.repeat_anonymous_increment.final_state.join(", ")}]。</p><p>双状态重复10次：最终状态 [{repeatMacroReport.demonstrations.repeat_anonymous_pair_transition.final_state.join(", ")}]。</p><p>证明义务 {repeatMacroReport.verification.obligations.filter(item => item.passed).length}/{repeatMacroReport.verification.obligations.length}。</p></div></div><div className="gate-grid">{repeatMacroReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.required)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{repeatMacroReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">CONTINUOUS FRONTIER · FIRST CONTACT</p><h2>未提供微积分公式：从缩步与分片中发现两个稳定语义</h2></div><span className="evidence-chip">{continuousFrontierReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>匿名精确观测</p><strong>{continuousFrontierReport.exploration_scale.local_observation_count + continuousFrontierReport.exploration_scale.partition_observation_count}</strong><span>{continuousFrontierReport.exploration_scale.anonymous_world_count}个世界 · 有理数无舍入</span></article><article className="metric-card accent-violet"><p>枚举候选程序</p><strong>{continuousFrontierReport.exploration_scale.total_candidate_count}</strong><span>局部 {continuousFrontierReport.exploration_scale.local_candidate_count} · 分片 {continuousFrontierReport.exploration_scale.partition_candidate_count}</span></article><article className="metric-card accent-amber"><p>新语义</p><strong>OP129 · OP130</strong><span>{continuousFrontierReport.discovered_semantics.map(item => item.semantic.semantic_id).join(" · ")}</span></article><article className="metric-card accent-slate"><p>独立证明</p><strong>{continuousFrontierReport.verification.obligations.filter(item => item.passed).length}/{continuousFrontierReport.verification.obligations.length}</strong><span>{continuousFrontierReport.verification.formal_domain}</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>OP129 · 证明后命名</span><p><strong>{continuousFrontierReport.discovered_semantics[0].posthoc_name}</strong></p><p>搜索选择：右值−中心值、中心值−左值，并都按一步长度归一化；左右必须趋向同一稳定值。</p>{continuousFrontierReport.demonstrations.anonymous_local_world.map(item => <p key={item.step}>步长 {item.step}：右侧 {item.forward} · 左侧 {item.backward}</p>)}</div><div className="promotion-lane"><span>OP130 · 证明后命名</span><p><strong>{continuousFrontierReport.discovered_semantics[1].posthoc_name}</strong></p><p>搜索选择：中点采样求和，再乘每个分片宽度；细分后趋稳且区间可以拼接。</p>{continuousFrontierReport.demonstrations.anonymous_partition_world.map(item => <p key={item.partition_count}>分片 {item.partition_count}：{item.value}</p>)}</div></div><div className="promotion-lanes"><div className="promotion-lane blocked-lane"><span>反例没有被平均掉</span><p>{continuousFrontierReport.counterexample.kind}：右侧={continuousFrontierReport.counterexample.forward_value}，左侧={continuousFrontierReport.counterexample.backward_value}。</p><p>{continuousFrontierReport.counterexample.rejected ? "左右不一致，拒绝进入成功语义" : "错误：未拒绝"}；错题记录 {continuousFrontierReport.counterexample.mistake_record.mistake_id}。</p></div><div className="promotion-lane blocked-lane"><span>验证覆盖</span><p>局部收敛 {continuousFrontierReport.verification.local_cases.filter(item => item.passed).length}/{continuousFrontierReport.verification.local_cases.length}</p><p>分片收敛 {continuousFrontierReport.verification.partition_cases.filter(item => item.passed).length}/{continuousFrontierReport.verification.partition_cases.length}</p><p>区间拼接 {continuousFrontierReport.verification.additivity_cases.filter(item => item.passed).length}/{continuousFrontierReport.verification.additivity_cases.length}</p></div></div><div className="gate-grid">{continuousFrontierReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{typeof gate.actual === "object" ? JSON.stringify(gate.actual) : String(gate.actual)} / {String(gate.required)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{continuousFrontierReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">NEW DATA-DEPENDENT CONTROL SEMANTIC</p><h2>离开直线加减：归纳出带守卫退出的循环操作码OP128</h2></div><span className="evidence-chip">{guardedReductionReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>新控制操作码</p><strong>OP{guardedReductionReport.invented_operator.opcode}</strong><span>{guardedReductionReport.invented_operator.semantic_id}</span></article><article className="metric-card accent-violet"><p>多来源证据</p><strong>{guardedReductionReport.discovery.supporting_source_count}</strong><span>{guardedReductionReport.discovery.proven_word_programs_scanned}个证明程序 · {guardedReductionReport.discovery.distinct_backward_loop_shapes}种循环骨架</span></article><article className="metric-card accent-amber"><p>通用证明</p><strong>{guardedReductionReport.verification.obligations.filter(item => item.passed).length}/{guardedReductionReport.verification.obligations.length}</strong><span>循环不变量、终止性和出口唯一性</span></article><article className="metric-card accent-slate"><p>隐藏重放</p><strong>{guardedReductionReport.verification.case_results.filter(item => item.passed).length}/{guardedReductionReport.verification.case_results.length}</strong><span>非负初值与正步长</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>发现时只看到匿名结构</span><p>操作码骨架：[{guardedReductionReport.invented_operator.normalized_opcode_shape.join(", ")}]</p><p>同时包含“试减后检测负数”和“跳回循环起点”，循环次数由运行数据决定。</p><p>来源：{guardedReductionReport.invented_operator.source_record_ids.join(" · ")}</p></div><div className="promotion-lane blocked-lane"><span>证明后才附加的解释</span><p><strong>{guardedReductionReport.posthoc_interpretation.name}</strong></p><p>{guardedReductionReport.posthoc_interpretation.effect}</p><p>示例：17与5进入循环后，成功 {guardedReductionReport.demonstration.result.iteration_count} 次，计数={guardedReductionReport.demonstration.result.final_count}，剩余={guardedReductionReport.demonstration.result.final_remainder}。</p><p>成功房间哈希：{guardedReductionReport.control_semantic_room.event_hash}</p></div></div><div className="gate-grid">{guardedReductionReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.required)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{guardedReductionReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">UNIVERSAL VALIDITY AUDIT LOOP</p><h2>反复证明定义域；失败公式自动退出活动库</h2></div><span className="evidence-chip">{universalAuditReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>活动库</p><strong>{universalAuditReport.loop.active_operator_count}/{universalAuditReport.loop.input_operator_count}</strong><span>本轮实际撤销 {universalAuditReport.loop.removed_operator_count} 条</span></article><article className="metric-card accent-violet"><p>固定点循环</p><strong>{universalAuditReport.loop.round_count}</strong><span>{universalAuditReport.loop.converged ? "连续两轮活动集合不变，允许停止" : "尚未收敛"}</span></article><article className="metric-card accent-amber"><p>通用证明义务</p><strong>{universalAuditReport.proof_summary.obligations_passed}/{universalAuditReport.proof_summary.obligations_total}</strong><span>{universalAuditReport.proof_summary.active_semantics_passed}/{universalAuditReport.proof_summary.active_semantics_total} 个语义通过</span></article><article className="metric-card accent-slate"><p>定义域分层</p><strong>{universalAuditReport.proof_summary.natural_number_safe_without_subtraction_count}/{universalAuditReport.proof_summary.requires_additive_inverse_count}</strong><span>自然数安全 / 需要加法逆元</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>“所有数学”在程序中的精确定义</span><p><strong>{universalAuditReport.meaning_of_universal.formal_domain}</strong></p><p>证明规则：{universalAuditReport.meaning_of_universal.proof_rule}。</p><p>不声称：{universalAuditReport.meaning_of_universal.not_claimed}。</p><p>活动文件：{universalAuditReport.active_catalog.path}</p></div><div className="promotion-lane blocked-lane"><span>失败即移除</span><p>{universalAuditReport.negative_control.description}</p><p>{universalAuditReport.negative_control.removed_from_active_catalog ? "错误样本已从隔离活动集合1条删到0条" : "移除测试失败"}。</p>{universalAuditReport.negative_control.isolated_loop_rounds.map(item => <p key={item.round}>循环 {item.round}：输入 {item.input_count} · 移除 {item.removed_count} · 保留 {item.survivor_count}</p>)}<p>错误区：{universalAuditReport.rejection_room.path}</p></div></div><div className="gate-grid">{universalAuditReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.required)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{universalAuditReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">GENERATION 2 · 100 OPERATORS</p><h2>出现100个不同运算符后，程序才停止</h2></div><span className="evidence-chip">{hundredOperatorReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>停止门</p><strong>{hundredOperatorReport.stop_rule.actual_new_operator_count}/{hundredOperatorReport.stop_rule.requested_new_operator_count}</strong><span>{hundredOperatorReport.stop_rule.program_stopped ? "达到100个且全数验证后停止" : "未达到，禁止停止"}</span></article><article className="metric-card accent-violet"><p>新操作码范围</p><strong>OP28–OP127</strong><span>100种规范化系数结构互不相同</span></article><article className="metric-card accent-amber"><p>独立展开重放</p><strong>{hundredOperatorReport.verification.passed_probe_case_count}/{hundredOperatorReport.verification.probe_case_count}</strong><span>另有 {hundredOperatorReport.verification.operator_results.filter(item => item.passed).length}/100 符号证明通过</span></article><article className="metric-card accent-slate"><p>程序长度分布</p><strong>{Object.entries(hundredOperatorReport.evolution.expanded_instruction_length_distribution).map(([length, count]) => `${length}:${count}`).join(" · ")}</strong><span>优先保留最短展开，再按代数效果去重</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>它实际做了什么</span><p>从上一代 {hundredOperatorReport.evolution.seed_operator_count} 个已验证种子中读取匿名操作数角色：{hundredOperatorReport.evolution.operand_roles_discovered_from_seeds.join(" · ")}。</p><p>自动枚举加减微程序，按系数向量合并不同写法；换地址或交换加法顺序不能重复计数。</p><p>没有向搜索器提供100个目标公式或名称。</p></div><div className="promotion-lane blocked-lane"><span>程序停止条件</span>{hundredOperatorReport.gates.map(gate => <p key={gate.gate_id}>{gate.passed ? "通过" : "失败"} · {gate.gate_id}：{String(gate.actual)} / {String(gate.required)}</p>)}</div></div><details><summary>展开查看全部100个新运算符</summary><div className="gate-grid">{hundredOperatorReport.operators.map(operator => <div className="gate-item" key={operator.operator_id}><span className="gate-light passed"/><div><strong>OP{operator.opcode} · {operator.operator_id}</strong><span>{operator.posthoc_effect}</span><span>系数 [{operator.coefficient_vector.join(", ")}] · 原展开 {operator.expanded_instruction_count} 条</span></div></div>)}</div></details><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{hundredOperatorReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">TEN NEW MICRO-OPERATORS</p><h2>上一代：自动归纳10个新运算符后停止</h2></div><span className="evidence-chip">{tenOperatorReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>停止门</p><strong>{tenOperatorReport.stop_rule.actual_new_operator_count}/{tenOperatorReport.stop_rule.requested_new_operator_count}</strong><span>{tenOperatorReport.stop_rule.program_stopped ? "达到10个后程序正常停止" : "尚未达到，程序不得停止"}</span></article><article className="metric-card accent-violet"><p>新操作码</p><strong>OP18–OP27</strong><span>10种效果签名互不相同</span></article><article className="metric-card accent-amber"><p>独立展开重放</p><strong>{tenOperatorReport.verification.passed_probe_case_count}/{tenOperatorReport.verification.probe_case_count}</strong><span>编译语义与原微程序逐项一致</span></article><article className="metric-card accent-slate"><p>已证明来源程序</p><strong>{tenOperatorReport.source_evidence.independently_proven_word_program_count}</strong><span>未向归纳器提供名称或目标效果</span></article></div><div className="gate-grid">{tenOperatorReport.operators.map(operator => <div className="gate-item" key={operator.operator_id}><span className="gate-light passed"/><div><strong>OP{operator.opcode} · {operator.operator_id}</strong><span>{operator.posthoc_effect}</span><span>{operator.supporting_occurrence_count}次出现 · {operator.source_program_count}个已证明来源</span></div></div>)}</div><div className="promotion-lanes"><div className="promotion-lane"><span>成功运算符房间</span><p><strong>{tenOperatorReport.semantic_room.batch_record_count} 条已写入</strong></p><p>{tenOperatorReport.semantic_room.path}</p><p>哈希链：{tenOperatorReport.semantic_room.hash_chained ? "是" : "否"}；加载时重新证明：{tenOperatorReport.semantic_room.proof_replayed_on_load ? "是" : "否"}。</p></div><div className="promotion-lane blocked-lane"><span>程序停止条件</span>{tenOperatorReport.gates.map(gate => <p key={gate.gate_id}>{gate.passed ? "通过" : "失败"} · {gate.gate_id}：{String(gate.actual)} / {String(gate.required)}</p>)}</div></div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{tenOperatorReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">NEW MEMORY OPERATOR</p><h2>从已证明复制链中归纳状态窗口运算符 OP17</h2></div><span className="evidence-chip">{stateWindowReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>新操作码</p><strong>OP {stateWindowReport.invented_operator.opcode}</strong><span>{stateWindowReport.invented_operator.semantic_id}</span></article><article className="metric-card accent-violet"><p>归纳证据宽度</p><strong>{stateWindowReport.invented_operator.observed_widths.join("→")}</strong><span>{stateWindowReport.invented_operator.supporting_occurrence_count} 个已证明复制链</span></article><article className="metric-card accent-amber"><p>未见窗口宽度</p><strong>{stateWindowReport.demonstration.unseen_window_width}</strong><span>封闭测试 {stateWindowReport.sealed_results.filter(item => item.passed).length}/{stateWindowReport.sealed_results.length}</span></article><article className="metric-card accent-slate"><p>指令约简</p><strong>{stateWindowReport.demonstration.expanded_instruction_count}→{stateWindowReport.demonstration.compressed_instruction_count}</strong><span>10条复制指令压成1条</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>事后解释</span><p><strong>{stateWindowReport.posthoc_symbol}</strong></p><p>语义：把连续状态窗口整体左移一格，并把指定源单元追加到窗口末尾。</p><p>它从证明记录 {stateWindowReport.invented_operator.source_record_ids.join(" · ")} 的字码中归纳，没有读取公式名称。</p><p>宽度5演示：{stateWindowReport.demonstration.posthoc_formula}</p></div><div className="promotion-lane blocked-lane"><span>自主验证过程</span>{stateWindowReport.experiment.self_selected_queries.map((query, index) => <p key={index}>实验 {index + 1}：({query.input_row.join(", ")})，{query.distinct_output_count} 类输出 / {query.disagreeing_candidate_pairs} 对分歧</p>)}<p>语义证明 {stateWindowReport.semantic_verification.obligations.filter(item => item.passed).length}/{stateWindowReport.semantic_verification.obligations.length}；错误路由 {stateWindowReport.mistake_ids.length} 条。</p><p>成功记录：{stateWindowReport.demonstration.success_room_record.room_record_id}</p></div></div><div className="gate-grid">{stateWindowReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.threshold)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{stateWindowReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">NEW FREE-VARIABLE FORMULA</p><h2>从匿名五列证据中发现带内部时钟的非齐次递推</h2></div><span className="evidence-chip">{timeForcedReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>严格公式库</p><strong>{timeForcedReport.strict_formula_total_before}→{timeForcedReport.strict_formula_total_after}</strong><span>新增1条，不是历史重分类</span></article><article className="metric-card accent-violet"><p>自主实验</p><strong>{timeForcedReport.experiment.self_selected_query_count}</strong><span>{timeForcedReport.experiment.host_seed_count}条起始 → {timeForcedReport.experiment.total_observation_count}条观测</span></article><article className="metric-card accent-amber"><p>未见参数</p><strong>{timeForcedReport.sealed_results.filter(item => item.passed).length}/{timeForcedReport.sealed_results.length}</strong><span>全部精确通过</span></article><article className="metric-card accent-slate"><p>全房间证明</p><strong>{timeForcedReport.room_proof_obligation_passed_count}/{timeForcedReport.room_proof_obligation_count}</strong><span>本公式 {timeForcedReport.proof.obligations.filter(item => item.passed).length}/{timeForcedReport.proof.obligations.length}</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>事后命名的公式</span><p><strong>{timeForcedReport.formula}</strong></p><p>主状态与内部时钟同时演化；两个系数项通过已归纳语义 {timeForcedReport.invented_semantic_id} 的重复加法执行。</p><p>严格记录：{timeForcedReport.strict_room_record.room_record_id}</p></div><div className="promotion-lane blocked-lane"><span>系统自己选择的实验</span>{timeForcedReport.experiment.self_selected_queries.map((query, index) => <p key={index}>实验 {index + 1}：({query.input_row.join(", ")})，分开 {query.distinct_output_count} 类输出 / {query.disagreeing_candidate_pairs} 对候选</p>)}<p>{timeForcedReport.mistake_ids.length} 条错误路由进入错题库。</p></div></div><div className="gate-grid">{timeForcedReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.threshold)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{timeForcedReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">PROOF-CARRYING REASONING</p><h2>中间结论可保存 · 推理路径可回放 · 反例触发回溯</h2></div><span className="evidence-chip">{reasoningReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>推理深度</p><strong>{reasoningReport.result.reasoning_depth}</strong><span>{reasoningReport.result.reasoning_step_count} 个可执行步骤</span></article><article className="metric-card accent-violet"><p>自主反例</p><strong>{reasoningReport.experiment.self_selected_query_count}</strong><span>{reasoningReport.experiment.host_seed_count} 条起始 → {reasoningReport.experiment.total_observation_count} 条观测</span></article><article className="metric-card accent-amber"><p>未见迁移</p><strong>{reasoningReport.sealed_transfer.passed}/{reasoningReport.sealed_transfer.total}</strong><span>独立逐步重放通过</span></article><article className="metric-card accent-slate"><p>旧三步基线</p><strong>{reasoningReport.fixed_depth_baseline.sealed_passed}/{reasoningReport.fixed_depth_baseline.sealed_total}</strong><span>最多 {reasoningReport.fixed_depth_baseline.maximum_graph_nodes} 个图节点</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>事后解释，不提供给学习器</span><p><strong>{reasoningReport.result.posthoc_interpretation}</strong></p><p>{reasoningReport.reasoner.primitive_operation_count} 个匿名已证明操作，在没有目标图和中间值的情况下形成 {reasoningReport.result.reasoning_step_count} 步路径。</p><p>每一步携带独立证明记录：{reasoningReport.result.component_proof_records.join(" · ")}</p></div><div className="promotion-lane blocked-lane"><span>系统自己选择的区分实验</span>{reasoningReport.experiment.self_selected_queries.map((query, index) => <p key={index}>实验 {index + 1}：输入 ({query.input_row.join(", ")})，分开 {query.distinct_output_count} 类输出 / {query.disagreeing_candidate_pairs} 对候选</p>)}<p>淘汰的 {reasoningReport.mistake_feedback.count} 条路径进入错题库。</p></div></div><div className="gate-grid">{reasoningReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.threshold)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{reasoningReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">LEARNING SYSTEM OPTIMIZATION</p><h2>错题改变策略 · 输入顺序未知 · 系统主动提出实验</h2></div><span className="evidence-chip">{learningReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>策略训练经验</p><strong>{learningReport.policy.success_example_count}/{learningReport.policy.failure_example_count_after}</strong><span>成功程序 / 错误程序</span></article><article className="metric-card accent-violet"><p>自主实验</p><strong>{learningReport.blind_task.self_selected_experiment_count}</strong><span>{learningReport.blind_task.host_seed_observation_count}条起始 → {learningReport.blind_task.total_observation_count}条总观测</span></article><article className="metric-card accent-amber"><p>输入排列搜索</p><strong>{learningReport.blind_task.input_permutations_searched}</strong><span>没有角色名或列映射</span></article><article className="metric-card accent-slate"><p>未见迁移</p><strong>{learningReport.sealed_results.filter(item => item.passed).length}/{learningReport.sealed_results.length}</strong><span>旧固定顺序基线 {learningReport.baseline.sealed_results.filter(item => item.passed).length}/{learningReport.baseline.sealed_results.length}</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>经验策略发生更新</span><p>初始：{learningReport.policy.initial_policy_id}</p><p>新增 {learningReport.policy.new_mistake_ids.length} 条反例后：{learningReport.policy.updated_policy_id}</p><p>策略使用 {learningReport.policy.feature_count} 个透明结构特征，并可持久化重放。</p></div><div className="promotion-lane blocked-lane"><span>模型自己问了什么</span>{learningReport.blind_task.selected_rows.map((row, index) => <p key={index}>实验 {index + 1}：({row.join(", ")})</p>)}<p>实验由候选程序分歧最大化选择，不由宿主预先列出反例。</p></div></div><div className="gate-grid">{learningReport.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.threshold)}</span></div></div>)}</div><div className="finding-strip"><span className="note-icon">i</span><p><strong>仍有边界：</strong>{learningReport.limitations.join("；")}</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">BOTTOM SEMANTIC INVENTION</p><h2>从11条已证明微指令中归纳出新操作码16</h2></div><span className="evidence-chip">{semanticReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>发明语义</p><strong>OP {semanticReport.invented_semantic.opcode}</strong><span>{semanticReport.invented_semantic.semantic_id}</span></article><article className="metric-card accent-violet"><p>证明支持实例</p><strong>{semanticReport.invented_semantic.supporting_occurrence_count}</strong><span>来自已证明重复微代码</span></article><article className="metric-card accent-amber"><p>指令压缩</p><strong>{semanticReport.discovery_summary.equivalent_expanded_instruction_count}→{semanticReport.discovery_summary.compressed_instruction_count}</strong><span>旧上限64 · 已突破</span></article><article className="metric-card accent-slate"><p>未见参数</p><strong>{semanticReport.discovery_summary.sealed_passed}/{semanticReport.discovery_summary.sealed_total}</strong><span>{semanticReport.discovery_summary.cegis_round_count}轮反例 · {semanticReport.discovery_summary.mistakes_recorded}条错题</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>依赖新语义的公式</span><p><strong>{semanticReport.formula}</strong></p><p>操作码16没有被预先赋予乘法含义；它的执行契约来自“按运行时自然计数器反复把源单元累积进目标单元”的已证明微程序。</p><p>严格记录：{semanticReport.strict_room_record.room_record_id}</p></div><div className="promotion-lane blocked-lane"><span>双层证明门</span><p>先证明操作码16与原11指令循环等价，再证明四次调用和四状态移位得到目标递推。</p><p>整个严格房间：{score}。</p><p>错误候选首个反例：预测 {semanticReport.discovery_summary.first_counterexample.predicted}，观测 {semanticReport.discovery_summary.first_counterexample.observed}。</p></div></div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{semanticReport.autonomy_boundary.invented}；{semanticReport.autonomy_boundary.verified}。{semanticReport.autonomy_boundary.host_supplied}。</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">PROGRAM REWRITE INDUCTION</p><h2>从程序差异中归纳改写规则，再把二状态扩展为三状态</h2></div><span className="evidence-chip">{rewriteReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>观察到的状态宽度</p><strong>{rewriteReport.discovery_summary.rewrite_rule.observed_copy_chain_widths.join("→")}</strong><span>由既有证明字码自动提取</span></article><article className="metric-card accent-violet"><p>生成程序长度</p><strong>{rewriteReport.discovery_summary.candidate_instruction_count}</strong><span>当前虚拟机上限 64 指令</span></article><article className="metric-card accent-amber"><p>反例收敛</p><strong>{rewriteReport.discovery_summary.cegis_round_count}</strong><span>轮后路由完全确定</span></article><article className="metric-card accent-slate"><p>未见参数</p><strong>{rewriteReport.discovery_summary.sealed_passed}/{rewriteReport.discovery_summary.sealed_total}</strong><span>另记录 {rewriteReport.discovery_summary.mistakes_recorded} 个错误程序</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>改写后公式</span><p><strong>{rewriteReport.formula}</strong></p><p>规则 {rewriteReport.discovery_summary.rewrite_rule.rule_id}：增加一个运行时初值槽、一个系数槽、复制一个计数累积项，并把状态复制链延长一格。</p><p>严格记录：{rewriteReport.strict_room_record.room_record_id}</p></div><div className="promotion-lane blocked-lane"><span>独立证明</span><p>首个错误路由在 ({rewriteReport.discovery_summary.first_counterexample.inputs.join(", ")}) 上预测 {rewriteReport.discovery_summary.first_counterexample.predicted}，观测为 {rewriteReport.discovery_summary.first_counterexample.observed}。</p><p>当时严格房间：{rewriteScore}。</p><p>{rewriteReport.termination_measure}</p></div></div><div className="finding-strip"><span className="note-icon">i</span><p><strong>自主性边界：</strong>{rewriteReport.autonomy_boundary.learned}；{rewriteReport.autonomy_boundary.applied}。{rewriteReport.autonomy_boundary.host_supplied}。</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">LEARNED MOTIF GROWTH</p><h2>不是再加一条宿主公式目录：从旧程序动机长出新程序</h2></div><span className="evidence-chip">{motifReport.run_id}</span></div><div className="metric-grid"><article className="metric-card accent-cyan"><p>自动抽取动机</p><strong>{motifReport.discovery_summary.learned_motif_count}</strong><span>仅读取程序字码与记录 ID</span></article><article className="metric-card accent-violet"><p>反例收敛轮次</p><strong>{motifReport.discovery_summary.cegis_round_count}</strong><span>错误路由被新证据淘汰</span></article><article className="metric-card accent-amber"><p>未见参数</p><strong>{motifReport.discovery_summary.sealed_passed}/{motifReport.discovery_summary.sealed_total}</strong><span>全部精确通过</span></article><article className="metric-card accent-slate"><p>新增错题</p><strong>{motifReport.discovery_summary.mistakes_recorded}</strong><span>失败候选永久记录</span></article></div><div className="promotion-lanes"><div className="promotion-lane"><span>证明后的公式</span><p><strong>{motifReport.formula}</strong></p><p>程序没有乘法操作码；两个乘积由两段重复加法循环形成，再进行同步状态迁移。</p><p>严格记录：{motifReport.strict_room_record.room_record_id}</p></div><div className="promotion-lane blocked-lane"><span>反例与全域证明</span><p>首个错误候选在输入 ({motifReport.discovery_summary.first_counterexample.inputs.join(", ")}) 上预测 {motifReport.discovery_summary.first_counterexample.predicted}，观测为 {motifReport.discovery_summary.first_counterexample.observed}。</p><p>当时公式房间证明义务：{motifScore}；此前 30 条批次为 407/407。</p><p>{motifReport.termination_measure}</p></div></div><div className="finding-strip"><span className="note-icon">i</span><p><strong>诚实边界：</strong>{motifReport.autonomy_boundary.learned}；{motifReport.autonomy_boundary.grown}。{motifReport.autonomy_boundary.host_supplied}。</p></div></section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">NEW SYNTHESIS</p><h2>本批真正新合成的 20 条自由变量程序</h2></div><span className="evidence-chip">20 NEW / 30 STRICT TOTAL</span></div><div className="gate-grid">{finalReport.batch_new_formulas.map(item => <div className="gate-item" key={item.record_id}><span className="gate-light passed"/><div><strong>{item.formula}</strong><span>{item.mechanism} · {item.record_id}</span></div></div>)}</div></section>

    <section className="content-grid lower-grid">
      <article className="surface promotion-card"><div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLE</p><h2>是什么迫使它放弃 2ⁿ</h2></div><span className="evidence-chip">CEGIS</span></div><div className="finding-strip"><span className="note-icon">!</span><p>输入 <strong>({counterexample.inputs.join(", ")})</strong> 时，第一轮预测 <strong>{counterexample.predicted}</strong>，实际观测为 <strong>{counterexample.observed}</strong>。固定底数程序因此不能入库；第二轮开始同时引用输入 a 与 n。</p></div><div className="run-id"><span>DISCOVERY</span><code>{report.source_discovery_run_id}</code></div></article>
      <article className="surface promotion-card"><div className="section-heading"><div><p className="eyebrow">POSTHOC DECODING</p><h2>{report.formula}</h2></div><span className="status-pill">PROVEN</span></div><div className="promotion-lanes"><div className="promotion-lane"><span>外层</span><p>计数器取运行时 n，结果从 1 开始。</p><p>每轮把结果更新为“a 重复累积旧结果次”。</p></div><div className="promotion-lane blocked-lane"><span>内层</span><p>临时量从 0 开始，每步加运行时 a。</p><p>内层次数由旧结果决定，没有乘法或幂操作码。</p></div></div></article>
    </section>

    <section className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">UNIVERSAL PROOF</p><h2>{report.domain}</h2></div><span className="evidence-chip">{report.proof.verifier_version}</span></div><div className="task-table"><div className="task-row task-header"><span>证明义务</span><span>结论</span><span>依据</span><span>状态</span></div>{report.proof.obligations.filter(item => labels[item.obligation_id]).map(item => <div className="task-row" key={item.obligation_id}><code>{labels[item.obligation_id]}</code><strong className="zero-value">通过</strong><span>{item.evidence}</span><span>{item.passed ? "PROVEN" : "FAILED"}</span></div>)}</div><div className="promotion-lanes"><div className="promotion-lane"><span>不变量</span>{report.invariants.map(item => <p key={item}>• {item}</p>)}</div><div className="promotion-lane blocked-lane"><span>终止性</span><p>{report.termination_measure}</p></div></div></section>

    <section className="content-grid lower-grid">
      <article className="surface task-table-card"><div className="section-heading"><div><p className="eyebrow">CLASSIFICATION FIX</p><h2>固定实例不再冒充参数化公式</h2></div></div><div className="promotion-lanes"><div className="promotion-lane"><span>不计数</span><p>2ⁿ、3ⁿ：固定底数实例。</p><p>(3ⁿ)²：已有程序的可约简组合。</p></div><div className="promotion-lane blocked-lane"><span>计数</span><p>F(a,n)=aⁿ：a 与 n 都是自由运行时输入。</p><p>同一程序通过未见底数并具有全域证明。</p></div></div></article>
      <article className="surface task-table-card"><div className="section-heading"><div><p className="eyebrow">AUTONOMY BOUNDARY</p><h2>这次是谁提供了什么</h2></div></div><div className="promotion-lanes"><div className="promotion-lane"><span>模型选择</span><p>{report.autonomy_boundary.learner_selected}</p></div><div className="promotion-lane blocked-lane"><span>宿主提供</span><p>{report.autonomy_boundary.host_supplied}</p><p>{report.autonomy_boundary.posthoc_only}</p></div></div></article>
    </section>

    <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>仍不能夸大的部分</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>
    <footer><div><span className="footer-mark">AKGM-N0</span><span>固定实例淘汰 · 自由变量迁移 · 嵌套归纳证明</span></div><code>{report.parametric_room_record_id}</code></footer>
  </main>;
}
