import type { Metadata } from "next";
import reportData from "../../data/metamachine_gen2_five_latest.json";

export const metadata: Metadata = {
  title: "五个成功新公式 · AKGM-N0",
  description: "MetaMachine Gen 2 五个互不等价成功程序的停止门报告。",
};

type Candidate = { rank: number; candidate_id: string; fit_error: number; disposition: string; mistake_id: string | null; program: { words: number[] } };
type Round = { round_index: number; active_case_indices: number[]; candidate: Candidate; added_counterexample_index: number | null; programs_generated: number };
type Result = { input: number[]; predicted: number | null; observed: number; step_count: number; passed: boolean };
type Task = {
  opaque_task: string;
  mechanism: string;
  candidate: Candidate;
  cegis: { round_count: number; rounds: Round[] };
  sealed_results: Result[];
  adversarial_results: Result[];
  success_room_record: { room_record_id: string; operation_id: string };
  mechanism_evidence: { grow_operand: number; jump_count: number };
};
type Report = {
  run_id: string;
  created_at: string;
  architecture: string;
  knowledge_status: string;
  stop_rule: { minimum_new_successful_formulas: number; actual: number; satisfied: boolean };
  tasks: Task[];
  five_candidate_feedback_per_task: Record<string, Candidate[]>;
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_active_count: number;
  mistake_feedback_count: number;
  ledger_event_count: number;
  autonomy_accounting: { host_supplied: string[]; learner_selected: string[]; posthoc_only: string[] };
  limitations: string[];
};

const report = reportData as Report;

const formulaCopy: Record<string, { title: string; formula: string; logic: string }> = {
  e: { title: "自反馈扩张", formula: "s₀ = 1；s ← s + s → 2ⁿ", logic: "一个状态把自身重新加入自身；没有乘法或幂指令。" },
  f: { title: "双状态耦合递推", formula: "(a,b)₀=(0,0)；(a,b)←(a+b,a+1) → 0,1,1,2,3…", logic: "两个状态同步计算后再提交，旧值不会被提前覆盖。" },
  g: { title: "变化差分累积", formula: "(a,b)₀=(1,2)；(a,b)←(a+b,b+2) → n²+n+1", logic: "结果累加变化状态；第二状态以证据常量推进。" },
  h: { title: "互补翻转", formula: "s₀ = 0；s ← 1 − s → 0,1,0,1…", logic: "不是余数指令，而是状态在两个值之间反复改写。" },
  i: { title: "嵌套计数累积", formula: "外层改变计数器；内层重复累积当前结果 → n!", logic: "两个向后跳转形成嵌套循环；没有乘法指令。" },
};

function CandidateTable({ task }: { task: Task }) {
  const candidates = report.five_candidate_feedback_per_task[`opaque_task_${task.opaque_task}`];
  return (
    <article className="surface promotion-card">
      <div className="section-heading"><div><p className="eyebrow">TASK {task.opaque_task.toUpperCase()} · FIVE PROGRAMS</p><h2>{formulaCopy[task.opaque_task].title}</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div>
      <div className="task-table">
        <div className="task-row task-header"><span>候选</span><span>长度</span><span>误差</span><span>去向</span></div>
        {candidates.map((candidate) => <div className="task-row" key={candidate.candidate_id}><code>#{candidate.rank} {candidate.candidate_id}</code><span>{candidate.program.words.length} words</span><strong className={candidate.fit_error === 0 ? "zero-value" : ""}>{candidate.fit_error.toFixed(3)}</strong><span>{candidate.disposition === "success_room" ? "成功公式房间" : `错题库 ${candidate.mistake_id}`}</span></div>)}
      </div>
    </article>
  );
}

export default function Gen2FivePage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const verifiedCases = report.tasks.reduce((sum, task) => sum + [...task.sealed_results, ...task.adversarial_results].filter((item) => item.passed).length, 0);
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">5X</span><div><p className="eyebrow">FIVE-SUCCESS STOP GATE</p><p className="brand-name">AKGM-N0 / MetaMachine Gen 2</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/gen2-five-control">第二批五公式</a><a className="nav-link" href="/gen2-loop">循环扩展</a><a className="nav-link" href="/gen2">Gen 2</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">五个成功新公式门通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>不是五个候选：是五个通过盲测且互不等价的新程序</h1>
          <p className="lede">同一搜索器从匿名数字表中选择单状态自反馈、双状态同步递推、变化差分、互补翻转和嵌套循环。公式名称只在验证完成后由人类解释。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>5/5</strong><span>停止门满足</span></div><p>{verifiedCases}/40 SEALED + ADVERSARIAL</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>成功程序</p><strong>{report.stop_rule.actual}</strong><span>结构与行为均去重</span></article>
        <article className="metric-card accent-violet"><p>成功房间</p><strong>{report.success_room_active_count}</strong><span>本轮由 13 增至 18</span></article>
        <article className="metric-card accent-amber"><p>候选反馈</p><strong>25</strong><span>5 成功 · {report.mistake_feedback_count} 错题</span></article>
        <article className="metric-card accent-slate"><p>反例轮次</p><strong>{report.tasks.reduce((sum, task) => sum + task.cegis.round_count, 0)}</strong><span>五个任务共用同一搜索器</span></article>
      </section>

      <section className="content-grid operation-grid">
        {report.tasks.map((task) => (
          <article className="surface concept-card" key={task.opaque_task}>
            <div className="section-heading"><div><p className="eyebrow">OPAQUE TASK {task.opaque_task.toUpperCase()}</p><h2>{formulaCopy[task.opaque_task].title}</h2></div><span className="status-pill">8/8 EXACT</span></div>
            <div className="posthoc-note"><span>{task.candidate.candidate_id}</span><strong>{formulaCopy[task.opaque_task].formula}</strong><small>{formulaCopy[task.opaque_task].logic}</small></div>
            <div className="finding-strip"><span className="note-icon">✓</span><p>{task.success_room_record.room_record_id} · {task.success_room_record.operation_id} · grow {task.mechanism_evidence.grow_operand} · jump {task.mechanism_evidence.jump_count}</p></div>
          </article>
        ))}
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLE-GUIDED SYNTHESIS</p><h2>10 轮结构修正记录</h2></div><span className="evidence-chip">SAME SEARCH INSTANCE</span></div>
        <div className="task-table"><div className="task-row task-header"><span>任务 / 轮次</span><span>活动证据</span><span>候选</span><span>反馈</span></div>{report.tasks.flatMap((task) => task.cegis.rounds.map((round) => <div className="task-row" key={`${task.opaque_task}-${round.round_index}`}><code>{task.opaque_task.toUpperCase()} · ROUND {round.round_index + 1}</code><span>[{round.active_case_indices.join(", ")}] · {round.programs_generated} programs</span><span>{round.candidate.candidate_id}</span><span>{round.added_counterexample_index === null ? "精确收敛" : `加入反例 #${round.added_counterexample_index}`}</span></div>))}</div>
      </section>

      <section className="content-grid operation-grid">{report.tasks.map((task) => <CandidateTable task={task} key={`feedback-${task.opaque_task}`} />)}</section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card"><div className="section-heading"><div><p className="eyebrow">AUTONOMY ACCOUNTING</p><h2>谁提供了什么</h2></div></div><div className="promotion-lanes"><div className="promotion-lane"><span>宿主提供</span>{report.autonomy_accounting.host_supplied.map((item) => <p key={item}>• {item}</p>)}</div><div className="promotion-lane"><span>学习器选择</span>{report.autonomy_accounting.learner_selected.map((item) => <p key={item}>• {item}</p>)}</div><div className="promotion-lane blocked-lane"><span>仅事后命名</span>{report.autonomy_accounting.posthoc_only.map((item) => <p key={item}>• {item}</p>)}</div></div></article>
        <article className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">STOP GATES</p><h2>全部资格门</h2></div></div><div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div></article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>仍然不能夸大的部分</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>
      <footer><div><span className="footer-mark">AKGM-N0</span><span>五个成功才停止 · 行为去重 · 密封验证 · 错题归档</span></div><code>{report.architecture} · ledger {report.ledger_event_count}</code></footer>
    </main>
  );
}
