import type { Metadata } from "next";
import reportData from "../../data/metamachine_latest.json";

export const metadata: Metadata = {
  title: "MetaMachine Gen 1 · AKGM-N0",
  description: "不提供算术、循环或结构化存储操作的匿名状态语义生长实验。",
};

type Gate = { gate_id: string; passed: boolean | null; actual: number | boolean | null; threshold: number | boolean };
type Report = {
  run_id: string;
  created_at: string;
  title: string;
  knowledge_status: string;
  architecture: string;
  learner_received: {
    arithmetic_operations: string[];
    structured_storage_operations: string[];
    repetition_operations: string[];
    supplied_substrate: string[];
  };
  development: {
    trace_count: number;
    maximum_trace_length: number;
    programs_generated: number;
    programs_scored_after_canonicalization: number;
    selected_candidate: {
      candidate_id: string;
      program: { state_count: number; initial_state_id: number; transition_table: number[][]; output_table: number[] };
      fit_error: number;
      reachable_state_count: number;
    };
  };
  blind_verification: { case_count: number; passed_case_count: number; failed_case_count: number; exhaustive_lengths: number[]; additional_lengths: number[] };
  structural_findings: { reachable_state_count: number; reachable_nontrivial_cycle: boolean; distinct_internal_state_reuse: boolean; host_supplied_repetition_instruction: boolean; host_supplied_completion: boolean };
  promoted_semantic: { operation_id: string; knowledge_id: string; ledger_status: string; replay_passed: boolean; definition: Record<string, unknown> };
  gates: Gate[];
  limitations: string[];
};

const report = reportData as Report;

const gateLabels: Record<string, string> = {
  development_exact: "开发轨迹精确",
  exhaustive_unseen_lengths_3_to_8: "长度 3–8 穷举盲测",
  maximum_registered_length_64: "64 步边界",
  reachable_nontrivial_state_cycle: "可达双状态回路",
  distinct_internal_state_reuse: "内部状态复用",
  promoted_operation_replay: "新语义调用回放",
  autonomous_completion: "自主停止",
  dynamic_storage_topology: "动态存储结构",
};

function gateState(gate: Gate) {
  if (gate.passed === null) return { text: "尚未证明", className: "pending" };
  if (gate.passed) return { text: "通过", className: "passed" };
  return { text: "未通过", className: "failed" };
}

export default function MetaMachinePage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const candidate = report.development.selected_candidate;
  const transitions = candidate.program.transition_table;
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">G1</span><div><p className="eyebrow">EMERGENT EXECUTABLE SEMANTICS</p><p className="brand-name">MetaMachine Gen 1 / 实验证据台</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/gen2">MetaMachine Gen 2</a><a className="nav-link" href="/">Gen 0</a><a className="nav-link" href="/operation">运算生长</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero operation-hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">首个证据门通过</span><span className="scope-label">状态 {report.knowledge_status}</span></div>
          <h1>{report.title}</h1>
          <p className="lede">没有提供算术、循环指令或现成存储结构。系统从匿名轨迹中搜索出一个具有回边的两状态网络，并将它提升为可调用的新语义。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{report.blind_verification.passed_case_count}/{report.blind_verification.case_count}</strong><span>未见轨迹通过</span></div><p>失败案例 {report.blind_verification.failed_case_count}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>匿名状态图</p><strong>{report.development.programs_generated.toLocaleString("zh-CN")}</strong><span>个候选被生成</span></article>
        <article className="metric-card accent-violet"><p>学习阶段</p><strong>{report.development.trace_count}</strong><span>条轨迹，最长 {report.development.maximum_trace_length} 步</span></article>
        <article className="metric-card accent-amber"><p>盲评阶段</p><strong>{report.blind_verification.case_count}</strong><span>条轨迹，最长 64 步</span></article>
        <article className="metric-card accent-slate"><p>新匿名语义</p><strong className="semantic-id">{report.promoted_semantic.operation_id}</strong><span>回放调用已通过</span></article>
      </section>

      <section className="content-grid metamachine-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">EMERGENT STATE GRAPH</p><h2>{candidate.candidate_id}</h2></div><span className="evidence-chip">误差 {candidate.fit_error.toFixed(1)}</span></div>
          <div className="state-network" aria-label="发现的两状态转移网络">
            <div className="state-node"><span>STATE</span><strong>0</strong><small>输出 {candidate.program.output_table[0]}</small></div>
            <div className="transition-stack"><p><b>符号 0</b><span>0 → {transitions[0][0]}</span><span>1 → {transitions[1][0]}</span></p><p><b>符号 1</b><span>0 → {transitions[0][1]}</span><span>1 → {transitions[1][1]}</span></p></div>
            <div className="state-node alternate"><span>STATE</span><strong>1</strong><small>输出 {candidate.program.output_table[1]}</small></div>
          </div>
          <div className="finding-strip"><span className="gate-light passed" /><p>系统生成了可达的双状态回路：状态可以被反复访问，而不是一次性前向执行。</p></div>
        </article>

        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">INPUT RECEIPT</p><h2>这次到底提供了什么</h2></div></div>
          <dl className="receipt-list"><div><dt>算术操作</dt><dd>{report.learner_received.arithmetic_operations.length} 个</dd></div><div><dt>循环操作</dt><dd>{report.learner_received.repetition_operations.length} 个</dd></div><div><dt>结构化存储操作</dt><dd>{report.learner_received.structured_storage_operations.length} 个</dd></div><div><dt>原始底座</dt><dd>符号、状态编号、转移表</dd></div></dl>
          <div className="posthoc-note"><span>必须诚实保留的边界</span><strong>输入结束仍由宿主决定</strong><small>本轮证明了自创状态回路和一位状态记忆；尚未证明自主停止。</small></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">SEMANTIC PROMOTION</p><h2>从候选网络变成下一层基础操作</h2></div><span className="status-pill">{report.promoted_semantic.ledger_status}</span></div>
        <div className="promotion-flow"><div><span>状态网络</span><strong>{candidate.candidate_id}</strong></div><b>验证</b><div><span>盲评证据</span><strong>{report.blind_verification.passed_case_count}/{report.blind_verification.case_count}</strong></div><b>提升</b><div className="promoted-step"><span>匿名新语义</span><strong>{report.promoted_semantic.operation_id}</strong></div></div>
      </section>

      <section className="surface gates-section">
        <div className="section-heading"><div><p className="eyebrow">GEN 1 EVIDENCE GATES</p><h2>已证明与未证明</h2></div><p className="section-note">黄色门决定当前状态仍是 bounded</p></div>
        <div className="gate-grid">{report.gates.map((gate) => { const state = gateState(gate); return <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${state.className}`} /><div><strong>{gateLabels[gate.gate_id] ?? gate.gate_id}</strong><span>{state.text}</span></div></div>; })}</div>
      </section>

      <section className="surface limitations-card standalone-limitations">
        <div className="section-heading"><div><p className="eyebrow">BOUNDARIES</p><h2>本次不能夸大的部分</h2></div></div>
        <ol className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol>
      </section>
      <footer><div><span className="footer-mark">GEN 1</span><span>匿名状态语义 · 非 Transformer · 可调用操作提升</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
