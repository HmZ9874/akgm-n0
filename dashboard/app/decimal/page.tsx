import type { Metadata } from "next";
import reportData from "../../data/radix_memory_latest.json";

export const metadata: Metadata = {
  title: "小数结构发现 · AKGM-N0",
  description: "从匿名非整数输出中搜索多级余量循环与位置权重。",
};

type Stage = { stage_index: number; input_residual: string; scaled_residual: string; emitted_count: number; next_residual: string; stage_weight: string };
type Result = { input: number[]; predicted: string | null; observed: string; integer_memory: number | null; initial_residual: string | null; stages: Stage[]; passed: boolean };
type Candidate = { rank: number; candidate_id: string; fit_mse: number; maximum_absolute_error: number; coherence_error: number; disposition: string; mistake_id: string | null; program: { cycle: { width: number; stage_weights: string[] } } };
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: { parent_operation_id: string; cycle_width_candidates: number[]; named_radix: boolean; multiply_operation: boolean; divide_operation: boolean };
  search: { programs_generated: number; programs_executed: number; programs_rejected: number; behavior_classes: number };
  five_candidate_feedback: Candidate[];
  winner: Candidate & { candidate_id: string; development_results: Result[]; sealed_results: Result[]; adversarial_results: Result[] };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_record: { room_record_id: string; operation_id: string };
  success_room_active_count: number;
  limitations: string[];
};

const report = reportData as Report;

export default function DecimalDiscoveryPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;
  const validation = [...winner.sealed_results, ...winner.adversarial_results];
  const example = winner.adversarial_results.find((item) => item.input[0] === 255) ?? winner.adversarial_results[0];
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">.001</span><div><p className="eyebrow">MULTISTAGE RESIDUAL MEMORY</p><p className="brand-name">AKGM-N0 / 小数结构发现</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/trace">第二记忆</a><a className="nav-link" href="/adapter">输入适配器</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">三位非整数结构通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>它从匿名循环候选中选出了十进位结构</h1>
          <p className="lede">学习器没有收到“小数”“十进制”、乘法或除法。它只看到整数输入与匿名非整数输出，在循环宽度 2 到 12 之间搜索，并自行组合多级位置权重。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>29/29</strong><span>开发、封存、对抗精确</span></div><p>{winner.candidate_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>候选程序</p><strong>{report.search.programs_generated.toLocaleString()}</strong><span>{report.search.behavior_classes.toLocaleString()} 个不同行为</span></article>
        <article className="metric-card accent-violet"><p>自行选择宽度</p><strong>{winner.program.cycle.width}</strong><span>搜索范围 {report.learner_received.cycle_width_candidates[0]}–{report.learner_received.cycle_width_candidates.at(-1)}</span></article>
        <article className="metric-card accent-amber"><p>位置权重</p><strong className="semantic-id">{winner.program.cycle.stage_weights.join(" · ")}</strong><span>内部一致性误差 0</span></article>
        <article className="metric-card accent-slate"><p>成功记录</p><strong className="semantic-id">{report.success_room_record.room_record_id}</strong><span>{report.success_room_record.operation_id} · 房间共 {report.success_room_active_count}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DISCOVERED MULTISTAGE PROGRAM</p><h2>获胜循环的执行结构</h2></div><span className="evidence-chip">EXACT DECIMAL</span></div>
          <div className="promotion-flow">
            <div><span>父程序</span><strong>读取整数记忆 Q 与余量 R</strong></div><b>repeat 10</b><div><span>生成下一状态</span><strong>R′ ← R 重复相加 10 次</strong></div><b>call</b><div><span>复用父操作</span><strong>得到位置计数 d 与新余量</strong></div><b>emit</b><div className="promoted-step"><span>逐级权重</span><strong>0.1 → 0.01 → 0.001</strong></div>
          </div>
          <div className="posthoc-note"><span>NO TARGET OPERATION</span><strong>候选程序内部仍然只有重复相加和父程序调用</strong><small>父操作 {report.learner_received.parent_operation_id}；没有乘法节点或除法节点。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">ADVERSARIAL TRACE</p><h2>对抗案例 ({example.input.join(", ")})</h2></div><span className="status-pill">{example.predicted}</span></div>
          <div className="replay-flow"><div><strong>Q={example.integer_memory}, R={example.initial_residual}</strong><span>整数记忆与初始余量</span></div>{example.stages.map((stage) => <div key={stage.stage_index}><strong>{stage.emitted_count} × {stage.stage_weight}</strong><span>第 {stage.stage_index + 1} 级；新余量 {stage.next_residual}</span></div>)}<div className="blocked-step"><strong>{example.predicted}</strong><span>最终新输出</span></div></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>人类事后读取为 31 + 0.8 + 0.07 + 0.005；候选执行时使用的是按次数重复累加，不是乘法。</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE PROGRAM STRUCTURES</p><h2>五个候选反馈</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>宽度与位置权重</span><span>最大误差</span><span>归档</span></div>
          {report.five_candidate_feedback.map((item) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>宽度 {item.program.cycle.width}；[{item.program.cycle.stage_weights.join(", ")}]</span><strong className={item.maximum_absolute_error === 0 ? "zero-value" : ""}>{item.maximum_absolute_error}</strong><span>{item.disposition === "success_room" ? "成功公式房间" : `错题库 ${item.mistake_id}`}</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>未见非整数输出</h2></div></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>输入</span><span>整数记忆</span><span>位置计数</span><span>程序 / 封存</span></div>
            {validation.map((item) => <div className="blind-row" key={item.input.join("-")}><code>[{item.input.join(", ")}]</code><span>{item.integer_memory}</span><span>{item.stages.map((stage) => stage.emitted_count).join(" · ")}</span><span className="zero-value">{item.predicted} / {item.observed}</span></div>)}
          </div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>小数结构资格门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">BOUNDARY</p><h2>这次还不能夸大的部分</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>匿名循环宽度 · 多级余量 · 位置权重 · 精确非整数输出</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
