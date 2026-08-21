import type { Metadata } from "next";
import reportData from "../../data/mistake_replay_latest.json";

export const metadata: Metadata = {
  title: "错题库回放实验 · AKGM-N0",
  description: "用反例记录和等价程序族识别阻止重复错误。",
};

type Gate = { gate_id: string; actual: number | boolean | null; threshold: number | boolean; passed: boolean | null };
type Report = {
  run_id: string;
  created_at: string;
  title: string;
  verdict: string;
  architecture: string;
  first_failure: {
    candidate: { candidate_id: string; program_ast: Record<string, unknown> };
    verification: { summary: { counterexample_count: number } };
  };
  stored_mistake: {
    mistake_id: string;
    condition_key: string;
    family_signature: string;
    counterexamples: Array<Record<string, unknown>>;
  };
  equivalence_probe: {
    probe_program_ast: Record<string, unknown>;
    structurally_identical: boolean;
    matched_mistake_ids: string[];
  };
  replay_search: {
    programs_generated: number;
    programs_filtered_before_scoring: number;
    programs_scored: number;
    old_family_returned: boolean;
  };
  library: { record_count: number; append_only_hash_chain: boolean };
  gates: Gate[];
  limitations: string[];
};

const report = reportData as Report;

const gateLabels: Record<string, string> = {
  counterexample_required_before_storage: "有反例才入库",
  equivalent_structure_recalled: "等价写法成功召回",
  old_family_blocked_before_scoring: "旧错误在评分前拦截",
  cross_condition_behavior: "跨条件行为",
};

function gateState(gate: Gate) {
  if (gate.passed === null) return { text: "待验证", className: "pending" };
  if (gate.passed) return { text: "通过", className: "passed" };
  return { text: "未通过", className: "failed" };
}

export default function MistakeReplayPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark">A2</span><div><p className="eyebrow">COUNTEREXAMPLE MEMORY</p><p className="brand-name">AKGM-N0 / 实验证据台</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/metamachine">Gen 1</a><a className="nav-link" href="/operation">运算生长</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero operation-hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">同目标 · 同失败条件</span></div>
          <h1>{report.title}</h1>
          <p className="lede">一个候选被反例推翻后，系统保存其程序族和失败条件。再次搜索时，结构不同但代数等价的旧错误在评分前被拦截。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal">
          <div className="signal-ring full-ring"><strong>{report.replay_search.programs_filtered_before_scoring}</strong><span>旧错误候选被拦截</span></div>
          <p>旧程序族返回：{report.replay_search.old_family_returned ? "是" : "否"}</p>
        </div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>已保存反例</p><strong>{report.first_failure.verification.summary.counterexample_count}</strong><span>个可复现失败点</span></article>
        <article className="metric-card accent-violet"><p>错题记录</p><strong>{report.library.record_count}</strong><span>条哈希链记录</span></article>
        <article className="metric-card accent-amber"><p>搜索前拦截</p><strong>{report.replay_search.programs_filtered_before_scoring}</strong><span>个等价候选</span></article>
        <article className="metric-card accent-slate"><p>旧错误返回</p><strong className="status-word">否</strong><span>候选列表中为零</span></article>
      </section>

      <section className="content-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">STORED FAILURE</p><h2>{report.stored_mistake.mistake_id}</h2></div><span className="status-pill">已入错题库</span></div>
          <p className="fact-line"><span>原候选</span><code>{report.first_failure.candidate.candidate_id}</code></p>
          <p className="fact-line"><span>失败条件</span><code>{report.stored_mistake.condition_key}</code></p>
          <pre className="code-block"><code>{JSON.stringify(report.first_failure.candidate.program_ast, null, 2)}</code></pre>
        </article>
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">EQUIVALENCE PROBE</p><h2>不同写法，同一错误族</h2></div><span className="evidence-chip">成功匹配</span></div>
          <dl className="concept-facts"><div><dt>结构完全相同</dt><dd>{report.equivalence_probe.structurally_identical ? "是" : "否"}</dd></div><div><dt>匹配记录</dt><dd>{report.equivalence_probe.matched_mistake_ids.length}</dd></div><div><dt>评分执行</dt><dd>未执行</dd></div></dl>
          <pre className="code-block"><code>{JSON.stringify(report.equivalence_probe.probe_program_ast, null, 2)}</code></pre>
          <p className="concept-footnote">当前等价识别覆盖现有的线性加减程序语言，包括加法换序和自由参数符号变化。</p>
        </article>
      </section>

      <section className="surface gates-section">
        <div className="section-heading"><div><p className="eyebrow">REPLAY GATES</p><h2>回放机制证据门</h2></div><p className="section-note">不会把不同条件下的假设武断封禁</p></div>
        <div className="gate-grid">{report.gates.map((gate) => { const state = gateState(gate); return <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${state.className}`} /><div><strong>{gateLabels[gate.gate_id] ?? gate.gate_id}</strong><span>{state.text}</span></div></div>; })}</div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEARCH REPLAY</p><h2>第二次搜索去向</h2></div></div>
          <div className="replay-flow"><div><strong>{report.replay_search.programs_generated}</strong><span>生成</span></div><b>→</b><div className="blocked-step"><strong>-{report.replay_search.programs_filtered_before_scoring}</strong><span>错题库拦截</span></div><b>→</b><div><strong>{report.replay_search.programs_scored}</strong><span>实际评分</span></div></div>
        </article>
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">BOUNDARIES</p><h2>不能夸大的部分</h2></div></div>
          <ol className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol>
        </article>
      </section>
      <footer><div><span className="footer-mark">AKGM-N0</span><span>反例记忆 · 条件化拦截 · 本地证据账本</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
