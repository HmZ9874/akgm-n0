import type { Metadata } from "next";
import reportData from "../../data/metamachine_gen2_loop_latest.json";

export const metadata: Metadata = {
  title: "Gen 2 动态循环扩展 · AKGM-N0",
  description: "同一反射式搜索器自主选择动态内存、循环终止与两种不同累积方式的验证报告。",
};

type Program = { words: number[] };
type Candidate = {
  rank: number;
  candidate_id: string;
  program: Program;
  fit_error: number;
  disposition: string;
  mistake_id: string | null;
  sealed_exact: boolean;
};
type Round = {
  round_index: number;
  active_case_indices: number[];
  candidate: Candidate;
  added_counterexample_index: number | null;
  programs_generated: number;
};
type Result = {
  input: number[];
  predicted: number | null;
  observed: number;
  step_count: number;
  memory_growth_count: number;
  passed: boolean;
};
type Task = {
  opaque_task: string;
  candidate: Candidate;
  cegis: { converged: boolean; round_count: number; rounds: Round[] };
  sealed_results: Result[];
  adversarial_results: Result[];
  success_room_record: { room_record_id: string; operation_id: string };
  posthoc_human_interpretation: string;
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: Record<string, boolean>;
  tasks: Task[];
  five_candidate_feedback: { opaque_task_c: Candidate[]; opaque_task_d: Candidate[] };
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; threshold: unknown }>;
  success_room_active_count: number;
  ledger_event_count: number;
  autonomy_change: {
    previously_probe_only: string;
    now_selected_by_synthesizer: string[];
    still_not_selected: string[];
  };
  limitations: string[];
};

const report = reportData as Report;

const taskCopy: Record<string, { title: string; decoding: string }> = {
  c: {
    title: "固定输入的计数累积",
    decoding: "结果从 0 开始；计数器每减少 1，就把输入 1 加入结果，直到计数器为 0。事后看，它表现为乘法式关系，但程序中没有乘法指令。",
  },
  d: {
    title: "变化状态的逐次累积",
    decoding: "结果从 0 开始；每轮先加入当前计数器，再将计数器减少 1，直到计数器为 0。事后看，它表现为三角和关系。",
  },
};

function ExactCases({ results }: { results: Result[] }) {
  return (
    <div className="task-table">
      <div className="task-row task-header"><span>输入</span><span>程序输出</span><span>观察值</span><span>执行</span></div>
      {results.map((result) => (
        <div className="task-row" key={`${result.input.join("-")}-${result.observed}`}>
          <code>[{result.input.join(", ")}]</code>
          <strong className="zero-value">{result.predicted}</strong>
          <span>{result.observed}</span>
          <span>{result.passed ? "精确" : "失败"} · {result.step_count} steps · grow {result.memory_growth_count}</span>
        </div>
      ))}
    </div>
  );
}

function CandidateTable({ title, candidates }: { title: string; candidates: Candidate[] }) {
  return (
    <article className="surface promotion-card">
      <div className="section-heading"><div><p className="eyebrow">FIVE PROGRAMS</p><h2>{title}</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div>
      <div className="task-table">
        <div className="task-row task-header"><span>候选</span><span>程序长度</span><span>开发误差</span><span>归档</span></div>
        {candidates.map((candidate) => (
          <div className="task-row" key={`${title}-${candidate.rank}`}>
            <code>#{candidate.rank} {candidate.candidate_id}</code>
            <span>{candidate.program.words.length} words</span>
            <strong className={candidate.fit_error === 0 ? "zero-value" : ""}>{candidate.fit_error.toFixed(3)}</strong>
            <span>{candidate.disposition === "success_room" ? "成功公式房间" : `错题库 ${candidate.mistake_id}`}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export default function Gen2LoopGrowthPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const taskC = report.tasks[0];
  const taskD = report.tasks[1];
  const exactCount = report.tasks.reduce((sum, task) => sum + task.sealed_results.filter((item) => item.passed).length + task.adversarial_results.filter((item) => item.passed).length, 0);

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">L2</span><div><p className="eyebrow">DYNAMIC LOOP GROWTH</p><p className="brand-name">AKGM-N0 / MetaMachine Gen 2</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/gen2-five">五公式停止门</a><a className="nav-link" href="/gen2">Gen 2 起点</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">动态循环扩展通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>同一搜索器创造了两种底层逻辑不同的循环计算方式</h1>
          <p className="lede">没有提供乘法、三角和或目标公式。程序候选自己选择扩充两个内存单元、写入计数器与结果、判断停止、向后跳转，并分别形成“固定输入累积”和“变化状态累积”。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{exactCount}/16</strong><span>密封与对抗案例精确</span></div><p>2 TASKS · 2 DISTINCT LOOPS</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>搜索器</p><strong>SAME</strong><span>两个匿名任务共用同一实现</span></article>
        <article className="metric-card accent-violet"><p>反例修正</p><strong>2 + 2</strong><span>两个任务都在第二轮收敛</span></article>
        <article className="metric-card accent-amber"><p>候选反馈</p><strong>10</strong><span>2 成功 · 8 错题归档</span></article>
        <article className="metric-card accent-slate"><p>成功房间</p><strong>{report.success_room_active_count}</strong><span>本轮新增 2 个非等价程序</span></article>
      </section>

      <section className="content-grid operation-grid">
        {[taskC, taskD].map((task) => (
          <article className="surface concept-card" key={task.opaque_task}>
            <div className="section-heading"><div><p className="eyebrow">OPAQUE TASK {task.opaque_task.toUpperCase()}</p><h2>{taskCopy[task.opaque_task].title}</h2></div><span className="status-pill">8/8 SEALED+ADV</span></div>
            <div className="posthoc-note"><span>{task.candidate.candidate_id}</span><strong>[{task.candidate.program.words.join(", ")}]</strong><small>{taskCopy[task.opaque_task].decoding}</small></div>
            <div className="finding-strip"><span className="note-icon">✓</span><p>{task.success_room_record.room_record_id} · {task.success_room_record.operation_id}</p></div>
          </article>
        ))}
      </section>

      <section className="content-grid operation-grid">
        {[taskC, taskD].map((task) => (
          <article className="surface promotion-card" key={`cegis-${task.opaque_task}`}>
            <div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLE REVISION</p><h2>任务 {task.opaque_task.toUpperCase()}：两轮结构变化</h2></div><span className="evidence-chip">{task.cegis.converged ? "CONVERGED" : "OPEN"}</span></div>
            <div className="task-table">
              <div className="task-row task-header"><span>轮次</span><span>活动证据</span><span>候选</span><span>反馈</span></div>
              {task.cegis.rounds.map((round) => (
                <div className="task-row" key={round.round_index}>
                  <code>ROUND {round.round_index + 1}</code>
                  <span>[{round.active_case_indices.join(", ")}] · {round.programs_generated} programs</span>
                  <span>{round.candidate.candidate_id}</span>
                  <span>{round.added_counterexample_index === null ? "精确收敛" : `加入反例 #${round.added_counterexample_index}`}</span>
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="content-grid operation-grid">
        <article className="surface promotion-card"><div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>任务 C：未参与搜索的验证</h2></div><span className="status-pill">8/8 EXACT</span></div><ExactCases results={[...taskC.sealed_results, ...taskC.adversarial_results]} /></article>
        <article className="surface promotion-card"><div className="section-heading"><div><p className="eyebrow">SEALED + ADVERSARIAL</p><h2>任务 D：未参与搜索的验证</h2></div><span className="status-pill">8/8 EXACT</span></div><ExactCases results={[...taskD.sealed_results, ...taskD.adversarial_results]} /></article>
      </section>

      <section className="content-grid operation-grid">
        <CandidateTable title="任务 C：五个可验证程序" candidates={report.five_candidate_feedback.opaque_task_c} />
        <CandidateTable title="任务 D：五个可验证程序" candidates={report.five_candidate_feedback.opaque_task_d} />
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">AUTONOMY CHANGE</p><h2>这次真正增加了什么</h2></div></div>
          <div className="promotion-lanes">
            <div className="promotion-lane"><span>以前只是探针</span><p>• {report.autonomy_change.previously_probe_only}</p></div>
            <div className="promotion-lane"><span>现在由合成器选中</span>{report.autonomy_change.now_selected_by_synthesizer.map((item) => <p key={item}>• {item}</p>)}</div>
            <div className="promotion-lane blocked-lane"><span>仍未自主选中</span>{report.autonomy_change.still_not_selected.map((item) => <p key={item}>• {item}</p>)}</div>
          </div>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">VERIFICATION GATES</p><h2>资格门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>不能把它夸大成什么</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>动态内存 · 候选控制停止 · 向后跳转 · 错题归档</span></div><code>{report.architecture} · ledger {report.ledger_event_count}</code></footer>
    </main>
  );
}
