import type { Metadata } from "next";
import reportData from "../../data/second_input_adapter_latest.json";

export const metadata: Metadata = {
  title: "第二输入符号适配 · AKGM-N0",
  description: "从匿名混合符号案例中合成条件输入适配器。",
};

type Result = { input: number[]; adapted_inputs: number[] | null; predicted: number | null; observed: number; step_count: number | null; passed: boolean };
type Candidate = {
  rank: number;
  candidate_id: string;
  fit_mse?: number;
  search_failure: boolean;
  disposition: string;
  mistake_id: string | null;
  reason?: string;
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: { development_input_rows: number[][]; development_output_values: number[]; parent_operation_id: string };
  search: { programs_generated: number; programs_executed: number; nonhalting_programs: number; behavior_classes: number };
  five_candidate_feedback: Candidate[];
  winner: Candidate & { candidate_id: string; sealed_results: Result[]; adversarial_results: Result[] };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_record: { room_record_id: string; operation_id: string };
  limitations: string[];
};

const report = reportData as Report;

const candidateSummaries = [
  "若 ¬(−1<y)，令 y′=0−y；否则 y′=y",
  "若 y<0，令 y′=0−y；否则 y′=y（等价写法）",
  "等值触发后令 y′=y−x；出现不停止反例",
  "按 x 与 y 的顺序判断后适配；出现不停止反例",
  "保持 y 不变；负的 y 导致不停止",
];

export default function AdapterPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;
  const validation = [...winner.sealed_results, ...winner.adversarial_results];
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">|y|</span><div><p className="eyebrow">CONDITIONAL INPUT ADAPTER</p><p className="brand-name">AKGM-N0 / 第二输入符号适配</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/trace">第二记忆发现</a><a className="nav-link" href="/signed">负第一输入分支</a><a className="nav-link" href="/adaptive">基础控制器</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">负第二输入扩展通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>程序先改写输入，再复用已经成功的控制器</h1>
          <p className="lede">模型没有收到绝对值或负除数规则。它从混合正负案例中选择一个条件和一个输入表达式，把第二输入适配为父程序可以处理的形式，然后调用已验证操作。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>0</strong><span>开发/封存/边界误差</span></div><p>{winner.candidate_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>适配候选</p><strong>{report.search.programs_generated}</strong><span>{report.search.programs_executed} 个可完成执行</span></article>
        <article className="metric-card accent-violet"><p>封存验证</p><strong>{winner.sealed_results.filter((item) => item.passed).length}/{winner.sealed_results.length}</strong><span>四种符号组合</span></article>
        <article className="metric-card accent-amber"><p>边界验证</p><strong>{winner.adversarial_results.filter((item) => item.passed).length}/{winner.adversarial_results.length}</strong><span>包含 ±256 与 ±1</span></article>
        <article className="metric-card accent-slate"><p>成功记录</p><strong className="semantic-id">{report.success_room_record.room_record_id}</strong><span>{report.success_room_record.operation_id}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DISCOVERED ADAPTER</p><h2>获胜输入适配程序</h2></div><span className="evidence-chip">MSE 0</span></div>
          <div className="promotion-flow">
            <div><span>候选编码</span><strong>¬(−1 &lt; y)</strong></div><b>integer</b><div><span>事后等价</span><strong>y &lt; 0</strong></div><b>then</b><div className="promoted-step"><span>适配第二输入</span><strong>y′ ← 0 − y</strong></div>
          </div>
          <div className="posthoc-note"><span>CALL VERIFIED PARENT</span><strong>{report.learner_received.parent_operation_id}(x, y′)</strong><small>若分支不触发则 y′=y。零作为第二输入仍被拒绝。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">UNSEEN ADAPTATION</p><h2>封存案例 (−29, −6)</h2></div><span className="status-pill">EXACT</span></div>
          <div className="replay-flow"><div><strong>−6</strong><span>原第二输入</span></div><b>→</b><div className="blocked-step"><strong>6</strong><span>适配后的第二输入</span></div><b>→</b><div><strong>1</strong><span>父控制器输出</span></div></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>适配后的完整输入为 [−29, 6]，程序输出 1，与封存值一致。</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE ADAPTER STRUCTURES</p><h2>五个适配候选</h2></div><span className="evidence-chip">1 成功 / 1 等价 / 3 错题</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>适配结构</span><span>MSE</span><span>归档</span></div>
          {report.five_candidate_feedback.map((item, index) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>{candidateSummaries[index]}</span><strong className={item.fit_mse === 0 ? "zero-value" : ""}>{item.fit_mse ?? "不停止"}</strong><span>{item.disposition === "success_room" ? "成功公式房间" : item.disposition === "equivalent_success_not_admitted" ? "等价成功，不重复入库" : `错题库 ${item.mistake_id}`}</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>混合符号验证</h2></div></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>原输入</span><span>适配输入</span><span>程序/封存</span><span>步数</span></div>
            {validation.map((item) => <div className="blind-row" key={item.input.join("-")}><code>[{item.input.join(", ")}]</code><code>[{item.adapted_inputs?.join(", ")}]</code><span>{item.predicted} / {item.observed}</span><span className="zero-value">{item.step_count}</span></div>)}
          </div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>适配器资格门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">BOUNDARY</p><h2>当前适配范围</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>条件输入改写 · 成功程序复用 · 混合符号验证 · 零明确拒绝</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
