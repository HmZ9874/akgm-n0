import type { Metadata } from "next";
import reportData from "../../data/signed_control_latest.json";

export const metadata: Metadata = {
  title: "负输入控制分支发现 · AKGM-N0",
  description: "复用正域控制器并从匿名负数案例中合成优先修复分支。",
};

type Result = { input: number[]; predicted: number; observed: number; step_count: number; passed: boolean };
type Candidate = {
  rank: number;
  candidate_id: string;
  fit_mse: number;
  maximum_steps_used: number;
  sealed_exact: boolean;
  disposition: string;
  mistake_id: string | null;
  program: { priority_branch: { guard: Record<string, unknown>; update_when_triggered: Record<string, unknown> } };
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  evaluator_posthoc_convention: string;
  learner_received: {
    development_input_rows: number[][];
    development_output_values: number[];
    target_concept_name: boolean;
    target_formula: boolean;
    signed_rule_description: boolean;
    sealed_cases_visible_during_search: boolean;
    parent_operation_id: string;
  };
  search: { programs_generated: number; programs_executed: number; nonhalting_programs: number; behavior_classes: number };
  five_candidate_feedback: Candidate[];
  winner: Candidate & { sealed_results: Result[]; adversarial_results: Result[]; posthoc_human_interpretation: string };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_record: { room_record_id: string; operation_id: string };
  limitations: string[];
};

const report = reportData as Report;

const summaries = [
  "若 ¬(−1<S)，则 S←S+输入1，再重启控制周期",
  "若 ¬(0<S)，则 S←1−S，再重启",
  "若 S<0，则 S←1−S，再重启",
  "若 S<−1，则 S←S+输入1，再重启",
  "若 ¬(1<S)，则 S←S+1，再重启",
];

export default function SignedPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;
  const allValidation = [...winner.sealed_results, ...winner.adversarial_results];
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">±</span><div><p className="eyebrow">SIGNED CONTROL EXTENSION</p><p className="brand-name">AKGM-N0 / 负输入分支发现</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/adapter">负第二输入</a><a className="nav-link" href="/adaptive">正域控制器</a><a className="nav-link" href="/multiview">关系与内存</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">负输入扩展通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>没有给负数规则，程序自己增加优先分支</h1>
          <p className="lede">学习器加载上一轮成功控制器，只看到新的匿名负数案例。它自行选择分支比较、触发极性和状态更新；获胜分支先把负状态推进到非负区间，再把控制权交还给原程序。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>0</strong><span>三组验证总误差</span></div><p>{winner.candidate_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>分支程序</p><strong>{report.search.programs_generated}</strong><span>{report.search.behavior_classes} 个行为类</span></article>
        <article className="metric-card accent-violet"><p>封存验证</p><strong>{winner.sealed_results.filter((item) => item.passed).length}/{winner.sealed_results.length}</strong><span>含正数保持测试</span></article>
        <article className="metric-card accent-amber"><p>边界验证</p><strong>{winner.adversarial_results.filter((item) => item.passed).length}/{winner.adversarial_results.length}</strong><span>含 −256、−1 与零</span></article>
        <article className="metric-card accent-slate"><p>成功记录</p><strong className="semantic-id">{report.success_room_record.room_record_id}</strong><span>{report.success_room_record.operation_id}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">SYNTHESIZED PRIORITY BRANCH</p><h2>新发现的负状态处理</h2></div><span className="evidence-chip">MSE 0</span></div>
          <div className="promotion-flow">
            <div><span>候选编码</span><strong>¬(−1 &lt; S)</strong></div><b>integer</b><div><span>事后等价</span><strong>S &lt; 0</strong></div><b>then</b><div className="promoted-step"><span>分支更新</span><strong>S ← S + 输入 1</strong></div>
          </div>
          <div className="posthoc-note"><span>RETURN TO PARENT</span><strong>更新后重新开始控制周期</strong><small>当分支不触发时，交还给父操作 {report.learner_received.parent_operation_id}。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">UNSEEN TRACE</p><h2>封存案例 (−29, 6)</h2></div><span className="status-pill">5 STEPS</span></div>
          <div className="replay-flow"><div><strong>−29</strong><span>初始状态</span></div><b>→</b><div><strong>−23</strong><span>−17 → −11 → −5</span></div><b>→</b><div className="blocked-step"><strong>1</strong><span>交还父控制器并输出</span></div></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>程序输出 1，与封存值一致；该案例及路径均未参与分支搜索。</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE BRANCH STRUCTURES</p><h2>五个分支候选</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>分支控制</span><span>MSE</span><span>归档</span></div>
          {report.five_candidate_feedback.map((item, index) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>{summaries[index]}</span><strong className={item.fit_mse === 0 ? "zero-value" : ""}>{item.fit_mse}</strong><span>{item.disposition === "success_room" ? "成功公式房间" : `错题库 ${item.mistake_id}`}</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>未见负数验证</h2></div></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>输入</span><span>程序输出</span><span>封存值</span><span>步数</span></div>
            {allValidation.map((item) => <div className="blind-row" key={item.input.join("-")}><code>[{item.input.join(", ")}]</code><span>{item.predicted}</span><span>{item.observed}</span><span className="zero-value">{item.step_count}</span></div>)}
          </div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>负输入发现资格</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">BOUNDARY</p><h2>当前负数语义边界</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>成功控制器复用 · 自选优先分支 · 负输入封存验证</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
