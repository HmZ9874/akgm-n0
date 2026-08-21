import type { Metadata } from "next";
import reportData from "../../data/trace_memory_latest.json";

export const metadata: Metadata = {
  title: "第二记忆发现 · AKGM-N0",
  description: "在已验证控制器的匿名转移轨迹上合成新的可执行记忆语义。",
};

type Result = {
  input: number[];
  adapted_inputs: number[] | null;
  predicted: number | null;
  observed: number;
  parent_output: number | null;
  final_memory: number | null;
  priority_transitions: number | null;
  base_transitions: number | null;
  passed: boolean;
};
type Candidate = {
  rank: number;
  candidate_id: string;
  fit_mse: number;
  disposition: string;
  mistake_id: string | null;
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: { parent_operation_id: string; host_step_count_as_output: boolean };
  search: { programs_generated: number; programs_executed: number; programs_rejected: number; behavior_classes: number };
  five_candidate_feedback: Candidate[];
  winner: Candidate & { candidate_id: string; development_results: Result[]; sealed_results: Result[]; adversarial_results: Result[] };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_record: { room_record_id: string; operation_id: string };
  success_room_active_count: number;
  limitations: string[];
};

const report = reportData as Report;
const candidateSummaries = [
  "M₀=0；优先转移 M←M−1；基础转移 M←M+1；输出 M",
  "M₀=0；优先转移 M←M−1；基础转移 M←M−(−1)；等价",
  "M₀=1；其余近似获胜程序；整体偏高 1",
  "M₀=−1；两类更新方向正确；整体偏低 1",
  "M₀=1；用加上 −1 编码下降；整体偏高 1",
];

export default function TraceMemoryPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;
  const validations = [...winner.sealed_results, ...winner.adversarial_results];
  const passed = validations.filter((item) => item.passed).length;
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">M₂</span><div><p className="eyebrow">TRACE MEMORY SYNTHESIS</p><p className="brand-name">AKGM-N0 / 第二记忆发现</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/decimal">小数结构发现</a><a className="nav-link" href="/adapter">输入适配器</a><a className="nav-link" href="/signed">符号分支</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">第二记忆程序通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>程序自己增加第二个记忆单元，并创造新的输出</h1>
          <p className="lede">没有提供乘法、除法、余数、商或目标公式。候选程序只接收父控制器的两类匿名转移事件，自行决定第二记忆的初值、两种更新方式和最终读取位置。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>0</strong><span>25 个案例总误差</span></div><p>{winner.candidate_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>记忆程序</p><strong>{report.search.programs_generated.toLocaleString()}</strong><span>{report.search.behavior_classes} 个行为类别</span></article>
        <article className="metric-card accent-violet"><p>封存 + 对抗</p><strong>{passed}/{validations.length}</strong><span>全部未参与搜索</span></article>
        <article className="metric-card accent-amber"><p>成功房间</p><strong>{report.success_room_active_count}</strong><span>当前有效公式总数</span></article>
        <article className="metric-card accent-slate"><p>新增记录</p><strong className="semantic-id">{report.success_room_record.room_record_id}</strong><span>{report.success_room_record.operation_id}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DISCOVERED MEMORY MACHINE</p><h2>获胜的第二状态程序</h2></div><span className="evidence-chip">MSE 0</span></div>
          <div className="promotion-flow">
            <div><span>开始</span><strong>M ← 0</strong></div><b>priority</b><div><span>优先转移</span><strong>M ← M − 1</strong></div><b>base</b><div><span>基础转移</span><strong>M ← M + 1</strong></div><b>halt</b><div className="promoted-step"><span>新输出</span><strong>RETURN M</strong></div>
          </div>
          <div className="posthoc-note"><span>IMPORTANT</span><strong>没有把宿主 step_count 暴露成答案</strong><small>父操作 {report.learner_received.parent_operation_id}；计数行为来自候选程序新建的可执行记忆，而不是读取现成步数。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">TWO OUTPUTS FROM ONE RUN</p><h2>封存案例 (−29, −6)</h2></div><span className="status-pill">EXACT</span></div>
          <div className="replay-flow"><div><strong>−29, −6</strong><span>原输入</span></div><b>→</b><div><strong>5 次优先转移</strong><span>父状态被修正</span></div><b>→</b><div className="blocked-step"><strong>M = −5</strong><span>新记忆输出</span></div></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>同一次运行中，父程序最终输出 1，而新程序输出 −5；这不是换名字，而是从轨迹生成了不同的可执行结果。</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE DISTINCT STRUCTURES</p><h2>五个候选反馈</h2></div><span className="evidence-chip">1 成功 / 1 等价 / 3 错题</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>第二记忆结构</span><span>MSE</span><span>归档</span></div>
          {report.five_candidate_feedback.map((item, index) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>{candidateSummaries[index]}</span><strong className={item.fit_mse === 0 ? "zero-value" : ""}>{item.fit_mse}</strong><span>{item.disposition === "success_room" ? "成功公式房间" : item.disposition === "equivalent_success_not_admitted" ? "等价成功，不重复入库" : `错题库 ${item.mistake_id}`}</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>未见输入验证</h2></div></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>输入</span><span>优先 / 基础转移</span><span>父输出</span><span>新输出 / 目标</span></div>
            {validations.map((item) => <div className="blind-row" key={item.input.join("-")}><code>[{item.input.join(", ")}]</code><span>{item.priority_transitions} / {item.base_transitions}</span><span>{item.parent_output}</span><span className="zero-value">{item.predicted} / {item.observed}</span></div>)}
          </div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>新计算资格门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">BOUNDARY</p><h2>当前可证明范围</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>父控制复用 · 第二记忆自建 · 双事件更新 · 新输出语义</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
