import type { Metadata } from "next";
import reportData from "../../data/metamachine_gen2_latest.json";

export const metadata: Metadata = {
  title: "MetaMachine Gen 2 · AKGM-N0",
  description: "统一代码数据内存、自修改执行与任务无关反例搜索里程碑。",
};

type Result = { input: number[]; predicted: number | null; observed: number; passed: boolean; visited_instruction_ids: number[] };
type Candidate = { rank: number; candidate_id: string; fit_error: number; disposition: string; mistake_id: string | null; program: { words: number[] } };
type Round = { round_index: number; active_case_indices: number[]; candidate: Candidate; added_counterexample_index: number | null; programs_generated: number };
type Task = { opaque_task: string; candidate: Candidate; cegis: { converged: boolean; round_count: number; rounds: Round[] }; sealed_results: Result[]; success_room_record: { room_record_id: string; operation_id: string }; posthoc_human_interpretation: string };
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  kernel: { word_width: number; opcode_count: number; unified_code_data_memory: boolean; candidate_controlled_halt: boolean; self_modification_probe: { output: number; modifications: unknown[]; passed: boolean }; dynamic_growth_probe: { output: number; growth: unknown[]; passed: boolean } };
  learner_received: { same_searcher_source_for_both_tasks: boolean; counterexample_feedback: string; sealed_cases_visible_during_search: boolean };
  tasks: Task[];
  five_candidate_feedback: { opaque_task_a: Candidate[]; opaque_task_b: Candidate[] };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_active_count: number;
  autonomy_accounting: { human_supplied: string[]; system_generated: string[]; capability_only_not_yet_autonomously_selected: string[] };
  limitations: string[];
};

const report = reportData as Report;

function CandidateTable({ title, candidates }: { title: string; candidates: Candidate[] }) {
  return <article className="surface promotion-card"><div className="section-heading"><div><p className="eyebrow">FIVE WORD PROGRAMS</p><h2>{title}</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div><div className="task-table"><div className="task-row task-header"><span>候选</span><span>字程序</span><span>误差</span><span>归档</span></div>{candidates.map((item) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>[{item.program.words.join(", ")}]</span><strong className={item.fit_error === 0 ? "zero-value" : ""}>{item.fit_error.toFixed(3)}</strong><span>{item.disposition === "success_room" ? "成功公式房间" : `错题库 ${item.mistake_id}`}</span></div>)}</div></article>;
}

export default function MetaMachineGen2Page() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const taskA = report.tasks[0];
  const taskB = report.tasks[1];
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">G2</span><div><p className="eyebrow">REFLECTIVE WORD MACHINE</p><p className="brand-name">AKGM-N0 / MetaMachine Gen 2</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/gen2-loop">动态循环扩展</a><a className="nav-link" href="/metamachine">Gen 1</a><a className="nav-link" href="/trace">第二记忆</a><a className="nav-link" href="/decimal">小数结构</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">Gen 2 第一里程碑通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>代码和数据进入同一内存，反例可以改变程序结构</h1>
          <p className="lede">同一个搜索器处理两个没有名称的任务：任务 A 生成直线程序；任务 B 从只适用于非负数的猜想开始，收到两个反例后，在第三轮生成条件跳转程序。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>2/2</strong><span>同一搜索器任务通过</span></div><p>16 OPCODES · WORD WIDTH 2</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>统一内存</p><strong>{report.kernel.unified_code_data_memory ? "CODE=DATA" : "FAILED"}</strong><span>字宽 {report.kernel.word_width}</span></article>
        <article className="metric-card accent-violet"><p>自修改探针</p><strong>{report.kernel.self_modification_probe.passed ? "PASS" : "FAIL"}</strong><span>运行时改写未来代码并输出 {report.kernel.self_modification_probe.output}</span></article>
        <article className="metric-card accent-amber"><p>动态扩容探针</p><strong>{report.kernel.dynamic_growth_probe.passed ? "PASS" : "FAIL"}</strong><span>新增单元后写入并输出 {report.kernel.dynamic_growth_probe.output}</span></article>
        <article className="metric-card accent-slate"><p>成功房间</p><strong>{report.success_room_active_count}</strong><span>本轮新增 2 条字程序</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">OPAQUE TASK A</p><h2>一轮得到直线程序</h2></div><span className="status-pill">5/5 SEALED</span></div>
          <div className="posthoc-note"><span>{taskA.candidate.candidate_id}</span><strong>[{taskA.candidate.program.words.join(", ")}]</strong><small>事后解码：读取输入 0 → 叠加输入 1 → 输出 → 自主停止。</small></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>{taskA.success_room_record.room_record_id} · {taskA.success_room_record.operation_id}</p></div>
        </article>
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">OPAQUE TASK B</p><h2>反例推动条件分支出现</h2></div><span className="status-pill">5/5 SEALED</span></div>
          <div className="posthoc-note"><span>{taskB.candidate.candidate_id}</span><strong>[{taskB.candidate.program.words.join(", ")}]</strong><small>事后解码：读取输入 → 负值跳转 → 非负直接输出；负值路径连续两次减去原输入后输出。</small></div>
          <div className="finding-strip"><span className="note-icon">✓</span><p>{taskB.success_room_record.room_record_id} · {taskB.success_room_record.operation_id}</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLE-GUIDED REVISION</p><h2>任务 B 的三轮程序变化</h2></div><span className="evidence-chip">同一搜索器源码</span></div>
        <div className="task-table"><div className="task-row task-header"><span>轮次</span><span>活动案例</span><span>候选程序</span><span>反馈</span></div>{taskB.cegis.rounds.map((round) => <div className="task-row" key={round.round_index}><code>ROUND {round.round_index + 1}</code><span>[{round.active_case_indices.join(", ")}]</span><span>{round.candidate.candidate_id}</span><span>{round.added_counterexample_index === null ? "收敛" : `加入反例 #${round.added_counterexample_index}`}</span></div>)}</div>
      </section>

      <section className="content-grid operation-grid">
        <CandidateTable title="任务 A：五个候选" candidates={report.five_candidate_feedback.opaque_task_a} />
        <CandidateTable title="任务 B：五个候选" candidates={report.five_candidate_feedback.opaque_task_b} />
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">AUTONOMY ACCOUNTING</p><h2>谁提供了什么</h2></div></div>
          <div className="promotion-lanes"><div className="promotion-lane"><span>人类提供</span>{report.autonomy_accounting.human_supplied.map((item) => <p key={item}>• {item}</p>)}</div><div className="promotion-lane"><span>系统生成</span>{report.autonomy_accounting.system_generated.map((item) => <p key={item}>• {item}</p>)}</div><div className="promotion-lane blocked-lane"><span>尚未自主选择</span>{report.autonomy_accounting.capability_only_not_yet_autonomously_selected.map((item) => <p key={item}>• {item}</p>)}</div></div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">MILESTONE GATES</p><h2>Gen 2 资格门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>第一里程碑还没有做到什么</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>统一字内存 · 候选停止 · 反例修正 · 多任务同搜索器</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
