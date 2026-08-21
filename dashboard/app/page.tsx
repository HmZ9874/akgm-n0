import type { Metadata } from "next";
import reportData from "../data/latest.json";

export const metadata: Metadata = {
  title: "AKGM-N0 · 实验汇报",
  description: "匿名概念形成、验证证据与搜索成本对照。",
};

type Gate = {
  gate_id: string;
  threshold: number | boolean;
  actual: number | boolean | null;
  passed: boolean | null;
};

type Candidate = {
  candidate_id: string;
  program_ast: Record<string, unknown>;
  parameters: Record<string, number>;
  validation_mse: number;
  program_nodes: number;
};

type Report = {
  run_id: string;
  created_at: string;
  title: string;
  verdict: string;
  claim_scope: string;
  architecture: string;
  development: {
    task_count: number;
    all_tasks_exactly_solved: boolean;
    tasks: Array<{
      task_id: string;
      private_evaluator_parameters: number[];
      programs_generated: number;
      selected_candidate: Candidate;
    }>;
  };
  concept: {
    concept_id: string;
    definition_ast: Record<string, unknown>;
    support_task_count: number;
    occurrence_count: number;
    definition_nodes: number;
    description_gain: number;
    human_interpretation: string | null;
    knowledge_id: string;
    ledger_status: string;
  };
  transfer: {
    without_library_deep: { programs_generated: number; exact_candidate: Candidate };
    without_library_shallow: { programs_generated: number; exact_candidate_found: boolean };
    with_library_shallow: { programs_generated: number; exact_candidate: Candidate };
    search_cost_reduction: number;
    program_size_reduction: number;
  };
  gates: Gate[];
  ledger_event_count: number;
  limitations: string[];
};

const report = reportData as Report;

const gateLabels: Record<string, string> = {
  cross_task_support: "跨任务支持",
  positive_description_gain: "描述长度收益",
  minimum_search_cost_reduction: "搜索成本下降",
  held_out_exact_recovery_with_library: "持出任务精确恢复",
  noise_stability: "噪声稳定性",
  blind_registered_benchmark: "预注册盲评",
};

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function verdictText(value: string) {
  return value === "conditionally_passed" ? "有条件通过" : value;
}

function gateState(gate: Gate) {
  if (gate.passed === null) return { text: "待验证", className: "pending" };
  if (gate.passed) return { text: "通过", className: "passed" };
  return { text: "未通过", className: "failed" };
}

export default function Home() {
  const baselineCount = report.transfer.without_library_deep.programs_generated;
  const libraryCount = report.transfer.with_library_shallow.programs_generated;
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup">
          <span className="brand-mark">A0</span>
          <div>
            <p className="eyebrow">AUTONOMOUS KNOWLEDGE GENESIS</p>
            <p className="brand-name">AKGM-N0 / 实验证据台</p>
          </div>
        </div>
        <div className="run-meta">
          <a className="nav-link" href="/metamachine">MetaMachine Gen 1</a><a className="nav-link" href="/operation">运算生长</a><span className="meta-dot" /><span>{generatedAt}</span>
        </div>
      </header>

      <section className="hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row">
            <span className="verdict-badge">{verdictText(report.verdict)}</span>
            <span className="scope-label">限定课程内结论</span>
          </div>
          <h1>{report.title}</h1>
          <p className="lede">
            系统没有接收概念名称或目标公式。它从四个匿名任务的精确程序中抽取重复子程序，
            将其作为匿名原语用于新的持出任务。
          </p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal" aria-label={`搜索空间减少 ${percent(report.transfer.search_cost_reduction)}`}>
          <div className="signal-ring">
            <strong>{percent(report.transfer.search_cost_reduction)}</strong>
            <span>搜索空间减少</span>
          </div>
          <p>{baselineCount} → {libraryCount} 个候选程序</p>
        </div>
      </section>

      <section className="metric-grid" aria-label="关键结果">
        <article className="metric-card accent-cyan"><p>跨任务支持</p><strong>{report.concept.support_task_count}</strong><span>个独立开发任务</span></article>
        <article className="metric-card accent-violet"><p>描述长度收益</p><strong>+{report.concept.description_gain}</strong><span>MDL 单位</span></article>
        <article className="metric-card accent-amber"><p>程序尺寸下降</p><strong>{percent(report.transfer.program_size_reduction)}</strong><span>7 → 5 个节点</span></article>
        <article className="metric-card accent-slate"><p>知识状态</p><strong className="status-word">{report.concept.ledger_status}</strong><span>{report.ledger_event_count} 个账本事件</span></article>
      </section>

      <section className="content-grid">
        <article className="surface comparison-card">
          <div className="section-heading">
            <div><p className="eyebrow">TRANSFER TEST</p><h2>有库 / 无库对照</h2></div>
            <span className="evidence-chip">持出任务误差 0</span>
          </div>
          <div className="bar-chart" role="img" aria-label="候选程序数量对比">
            <div className="bar-row">
              <div className="bar-label"><span>无概念库</span><strong>{baselineCount}</strong></div>
              <div className="bar-track"><div className="bar baseline" style={{ width: "100%" }} /></div>
              <small>需要搜索到 7 节点深度</small>
            </div>
            <div className="bar-row">
              <div className="bar-label"><span>使用匿名原语</span><strong>{libraryCount}</strong></div>
              <div className="bar-track"><div className="bar library" style={{ width: `${(libraryCount / baselineCount) * 100}%` }} /></div>
              <small>5 节点内精确恢复</small>
            </div>
          </div>
          <div className="comparison-note"><span className="note-icon">!</span><p>同样限制为 5 个节点时，无概念库版本没有找到精确程序；加入匿名原语后找到。</p></div>
        </article>

        <article className="surface concept-card">
          <div className="section-heading">
            <div><p className="eyebrow">ANONYMOUS PRIMITIVE</p><h2>{report.concept.concept_id}</h2></div>
            <span className="status-pill">{report.concept.ledger_status}</span>
          </div>
          <dl className="concept-facts">
            <div><dt>出现次数</dt><dd>{report.concept.occurrence_count}</dd></div>
            <div><dt>定义节点</dt><dd>{report.concept.definition_nodes}</dd></div>
            <div><dt>人类解释</dt><dd>{report.concept.human_interpretation ?? "未指定"}</dd></div>
          </dl>
          <pre className="code-block"><code>{JSON.stringify(report.concept.definition_ast, null, 2)}</code></pre>
          <p className="concept-footnote">接纳依据来自执行、压缩和迁移证据，不依赖人类命名。</p>
        </article>
      </section>

      <section className="surface gates-section">
        <div className="section-heading">
          <div><p className="eyebrow">EVIDENCE GATES</p><h2>证据门状态</h2></div>
          <p className="section-note">待验证门使本次结论保持“有条件通过”</p>
        </div>
        <div className="gate-grid">
          {report.gates.map((gate) => {
            const state = gateState(gate);
            return (
              <div className="gate-item" key={gate.gate_id}>
                <span className={`gate-light ${state.className}`} />
                <div><strong>{gateLabels[gate.gate_id] ?? gate.gate_id}</strong><span>{state.text}</span></div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading">
            <div><p className="eyebrow">DEVELOPMENT SET</p><h2>形成证据</h2></div>
            <span className="evidence-chip">{report.development.task_count}/{report.development.task_count} 精确</span>
          </div>
          <div className="task-table" role="table" aria-label="开发任务结果">
            <div className="task-row task-header" role="row"><span>任务</span><span>候选数</span><span>节点</span><span>验证误差</span></div>
            {report.development.tasks.map((task) => (
              <div className="task-row" role="row" key={task.task_id}>
                <code>{task.task_id}</code><span>{task.programs_generated}</span><span>{task.selected_candidate.program_nodes}</span><span className="zero-value">{task.selected_candidate.validation_mse.toFixed(1)}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">BOUNDARIES</p><h2>不能夸大的部分</h2></div></div>
          <ol className="limitations-list">
            {report.limitations.map((limitation, index) => (
              <li key={limitation}><span>{String(index + 1).padStart(2, "0")}</span><p>{limitation}</p></li>
            ))}
          </ol>
        </article>
      </section>

      <footer>
        <div><span className="footer-mark">AKGM-N0</span><span>程序搜索 · 非 Transformer · 本地证据账本</span></div>
        <code>{report.architecture}</code>
      </footer>
    </main>
  );
}
