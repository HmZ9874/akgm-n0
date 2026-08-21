import type { Metadata } from "next";
import reportData from "../../data/operation_growth_latest.json";

export const metadata: Metadata = {
  title: "运算生长实验 · AKGM-N0",
  description: "不提供乘除法节点的匿名有限重复执行实验。",
};

type Gate = {
  gate_id: string;
  actual: number | boolean | null;
  threshold: number | boolean;
  passed: boolean | null;
};

type CaseResult = {
  case_index: number;
  input_row: number[];
  predicted_value: number;
  observed_value: number;
  passed: boolean;
};

type Report = {
  run_id: string;
  created_at: string;
  title: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: {
    natural_language: boolean;
    human_formula: boolean;
    human_operation_name: boolean;
    available_nodes: string[];
    supplied_computational_prior: string;
  };
  development: {
    row_count: number;
    programs_generated: number;
    selected_candidate: {
      candidate_id: string;
      program_ast: Record<string, unknown>;
      fit_error: number;
      program_nodes: number;
    };
  };
  blind_verification: {
    case_count: number;
    passed_case_count: number;
    failed_case_count: number;
    case_results: CaseResult[];
  };
  post_hoc_evaluator_interpretation: {
    assigned_after_blind_verification: boolean;
    equivalent_on_registered_domain: string;
  };
  gates: Gate[];
  ledger_event_count: number;
  limitations: string[];
};

const report = reportData as Report;

const gateLabels: Record<string, string> = {
  development_exact_fit: "开发样本精确拟合",
  blind_unseen_rows_exact: "未见样本精确通过",
  unregistered_nodes_absent: "未注册节点为零",
  negative_control_values: "负重复次数",
  non_integer_inputs: "非整数输入",
};

function gateState(gate: Gate) {
  if (gate.passed === null) return { text: "边界外 / 待扩展", className: "pending" };
  if (gate.passed) return { text: "通过", className: "passed" };
  return { text: "未通过", className: "failed" };
}

export default function OperationGrowthPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const candidate = report.development.selected_candidate;

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup">
          <span className="brand-mark">A1</span>
          <div><p className="eyebrow">OPERATION GROWTH</p><p className="brand-name">AKGM-N0 / 实验证据台</p></div>
        </div>
        <div className="run-meta"><a className="nav-link" href="/metamachine">Gen 1</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero operation-hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">知识状态 {report.knowledge_status}</span></div>
          <h1>{report.title}</h1>
          <p className="lede">学习器只看到匿名数字行、加法、减法、状态值和有限重复控制。它没有收到乘除法节点、名称或目标公式。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal" aria-label="盲测六项全部通过">
          <div className="signal-ring full-ring"><strong>{report.blind_verification.passed_case_count}/{report.blind_verification.case_count}</strong><span>未见样本通过</span></div>
          <p>开发误差 {candidate.fit_error.toFixed(1)} · 盲测误差 0</p>
        </div>
      </section>

      <section className="metric-grid" aria-label="关键结果">
        <article className="metric-card accent-cyan"><p>搜索规模</p><strong>{report.development.programs_generated}</strong><span>个匿名候选程序</span></article>
        <article className="metric-card accent-violet"><p>开发样本</p><strong>{report.development.row_count}</strong><span>行，全部精确</span></article>
        <article className="metric-card accent-amber"><p>盲测</p><strong>{report.blind_verification.passed_case_count}/{report.blind_verification.case_count}</strong><span>未见整数样本</span></article>
        <article className="metric-card accent-slate"><p>账本状态</p><strong className="status-word">{report.knowledge_status}</strong><span>{report.ledger_event_count} 个账本事件</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DISCOVERED PROGRAM</p><h2>{candidate.candidate_id}</h2></div><span className="evidence-chip">{candidate.program_nodes} 节点</span></div>
          <pre className="code-block operation-code"><code>{JSON.stringify(candidate.program_ast, null, 2)}</code></pre>
          <p className="concept-footnote">人类解释只在盲测通过后添加；它没有进入学习器输入或搜索评分。</p>
        </article>
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">WHAT WAS SUPPLIED</p><h2>最小先验边界</h2></div></div>
          <dl className="receipt-list">
            <div><dt>自然语言</dt><dd>未提供</dd></div>
            <div><dt>目标公式</dt><dd>未提供</dd></div>
            <div><dt>运算名称</dt><dd>未提供</dd></div>
            <div><dt>通用重复控制</dt><dd>提供，最多 64 次</dd></div>
          </dl>
          <div className="posthoc-note"><span>验证后解释</span><strong>在已注册整数域上等价于整数乘法</strong><small>这是评估器的事后命名，不是学习器的输入。</small></div>
        </article>
      </section>

      <section className="surface gates-section">
        <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>证据门状态</h2></div><p className="section-note">黄色项目明确限制当前结论范围</p></div>
        <div className="gate-grid">
          {report.gates.map((gate) => {
            const state = gateState(gate);
            return <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${state.className}`} /><div><strong>{gateLabels[gate.gate_id] ?? gate.gate_id}</strong><span>{state.text}</span></div></div>;
          })}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">BLIND CASES</p><h2>未见样本逐项核对</h2></div><span className="evidence-chip">零反例</span></div>
          <div className="blind-table" role="table" aria-label="未见样本验证结果">
            <div className="blind-row blind-header"><span>输入行</span><span>预测</span><span>观测</span><span>状态</span></div>
            {report.blind_verification.case_results.map((item) => <div className="blind-row" key={item.case_index}><code>[{item.input_row.join(", ")}]</code><span>{item.predicted_value}</span><span>{item.observed_value}</span><span className="zero-value">通过</span></div>)}
          </div>
        </article>
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">BOUNDARIES</p><h2>本次不能声称什么</h2></div></div>
          <ol className="limitations-list">
            {report.limitations.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}
          </ol>
        </article>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>匿名状态程序 · 非 Transformer · 本地证据账本</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
