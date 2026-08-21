import type { Metadata } from "next";
import reportData from "../../data/adaptive_control_latest.json";

export const metadata: Metadata = {
  title: "匿名循环控制发现 · AKGM-N0",
  description: "从匿名输入输出案例中合成停止条件、状态更新和输出语义。",
};

type Result = { input: number[]; predicted: number; observed: number; step_count: number; passed: boolean };
type Candidate = {
  rank: number;
  candidate_id: string;
  fit_mse: number;
  maximum_steps_used: number;
  training_outputs: number[];
  sealed_exact: boolean;
  disposition: string;
  mistake_id: string | null;
  program: Record<string, unknown>;
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: {
    development_input_rows: number[][];
    development_output_values: number[];
    target_concept_name: boolean;
    target_symbol: boolean;
    target_formula: boolean;
    sealed_cases_visible_during_search: boolean;
    available_value_operations: string[];
    available_guard_sensors: string[];
  };
  search: { programs_generated: number; programs_executed: number; nonhalting_programs: number; behavior_classes: number };
  five_candidate_feedback: Candidate[];
  winner: Candidate & {
    candidate_id: string;
    sealed_results: Result[];
    adversarial_results: Result[];
    posthoc_human_interpretation: string;
  };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_record: { room_record_id: string; operation_id: string };
  limitations: string[];
};

const report = reportData as Report;

function candidateSummary(item: Candidate): string {
  if (item.rank === 1) return "S←输入0；若 S<输入1 则停止；否则 S←S−输入1；输出 S";
  if (item.rank === 2) return "S←1；满足候选条件后递增；输出 S";
  if (item.rank === 3) return "S←输入0；反向停止极性；S←S−输入1；输出 S";
  if (item.rank === 4) return "立即停止并输出常量 1";
  return "S←1；候选等值控制；输出常量 1";
}

export default function AdaptivePage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">S</span><div><p className="eyebrow">ANONYMOUS ADAPTIVE CONTROL</p><p className="brand-name">AKGM-N0 / 自生成循环控制</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/signed">负输入扩展</a><a className="nav-link" href="/multiview">关系与内存</a><a className="nav-link" href="/arena">符号竞技场</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">发现新控制语义</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>没有提供“余数”，程序自己决定何时停止</h1>
          <p className="lede">学习器只得到匿名的两列输入和一列输出。它从初始化、比较方向、停止极性、状态更新与输出的组合中，找出一段可执行循环；任务名称只在全部验证结束后由评估者添加。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>0</strong><span>开发/封存/边界误差</span></div><p>{winner.candidate_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>生成程序</p><strong>{report.search.programs_generated.toLocaleString()}</strong><span>{report.search.behavior_classes} 个行为类</span></article>
        <article className="metric-card accent-violet"><p>封存验证</p><strong>{winner.sealed_results.filter((item) => item.passed).length}/{winner.sealed_results.length}</strong><span>搜索时不可见</span></article>
        <article className="metric-card accent-amber"><p>边界验证</p><strong>{winner.adversarial_results.filter((item) => item.passed).length}/{winner.adversarial_results.length}</strong><span>含 0、1 与长循环</span></article>
        <article className="metric-card accent-slate"><p>成功记录</p><strong className="semantic-id">{report.success_room_record.room_record_id}</strong><span>{report.success_room_record.operation_id}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DISCOVERED EXECUTABLE</p><h2>获胜控制程序</h2></div><span className="evidence-chip">MSE 0</span></div>
          <div className="promotion-flow">
            <div><span>初始化</span><strong>S ← 输入 0</strong></div><b>then</b><div><span>候选停止条件</span><strong>S &lt; 输入 1</strong></div><b>else</b><div className="promoted-step"><span>继续更新</span><strong>S ← S − 输入 1</strong></div>
          </div>
          <div className="posthoc-note"><span>OUTPUT</span><strong>停止后输出 S</strong><small>这段 AST 中不存在 remainder、modulo、除法或商等目标名称。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">EXECUTION TRACE</p><h2>未见案例 (29, 6)</h2></div><span className="status-pill">5 STEPS</span></div>
          <div className="replay-flow"><div><strong>29</strong><span>初始状态</span></div><b>→</b><div><strong>23</strong><span>17 → 11</span></div><b>→</b><div className="blocked-step"><strong>5</strong><span>满足停止条件并输出</span></div></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>封存答案为 5。停止条件和每轮更新均由候选程序定义，不是由评估器逐步指挥。</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE LOGIC STRUCTURES</p><h2>五个候选及其去向</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>控制结构</span><span>MSE</span><span>归档</span></div>
          {report.five_candidate_feedback.map((item) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>{candidateSummary(item)}</span><strong className={item.fit_mse === 0 ? "zero-value" : ""}>{item.fit_mse}</strong><span>{item.disposition === "success_room" ? "成功公式房间" : `错题库 ${item.mistake_id}`}</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>全部未见验证</h2></div></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>输入</span><span>程序输出</span><span>封存值</span><span>步数</span></div>
            {[...winner.sealed_results, ...winner.adversarial_results].map((item) => <div className="blind-row" key={item.input.join("-")}><code>[{item.input.join(", ")}]</code><span>{item.predicted}</span><span>{item.observed}</span><span className="zero-value">{item.step_count}</span></div>)}
          </div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>发现资格门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">BOUNDARY</p><h2>当前能力边界</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>匿名案例 · 自选停止条件 · 自选状态更新 · 封存验证</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
