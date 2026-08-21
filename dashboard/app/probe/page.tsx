import type { Metadata } from "next";
import reportData from "../../data/ordered_relation_probe_latest.json";

export const metadata: Metadata = {
  title: "数字关系探测 · AKGM-N0",
  description: "有序数字集合的诚实失败、五候选与反例报告。",
};

type Node = { op: string; args?: Node[]; constant?: number; operation_id?: string };
type Candidate = {
  rank: number;
  candidate_id: string;
  program: Node;
  fit_mse: number;
  maximum_absolute_error: number;
  training_outputs: number[];
  logic_signature: string;
  disposition: string;
  mistake_id: string | null;
  counterexamples: Array<{ index: number; predicted: number; observed: number }>;
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  learner_received: { numeric_values: number[]; opaque_semantic_operation_ids: string[] };
  derived_workspace: { first_layer: number[]; second_layer: number[]; construction: string };
  control_without_library: { programs_generated: number; best_fit_mse: number; exact: boolean };
  search_with_library: { programs_generated: number; behavior_classes: number; best_fit_mse: number; best_maximum_absolute_error: number; exact: boolean };
  five_candidate_feedback: Candidate[];
  success_room_record: null;
  limitations: string[];
};

const report = reportData as Report;

function expression(node: Node): string {
  if (node.op === "q_index") return "i";
  if (node.op === "q_constant") return String(node.constant);
  const [left, right] = node.args ?? [];
  if (!left || !right) return node.op;
  if (node.op === "q_add") return `(${expression(left)} + ${expression(right)})`;
  if (node.op === "q_subtract") return `(${expression(left)} − ${expression(right)})`;
  if (node.op === "q_semantic_call") return `SEM⟨${expression(left)}, ${expression(right)}⟩`;
  return node.op;
}

export default function ProbePage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const best = report.five_candidate_feedback[0];
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark">?</span><div><p className="eyebrow">ORDERED RELATION PROBE</p><p className="brand-name">AKGM-N0 / 数字关系探测</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/multiview">多视角关系图</a><a className="nav-link" href="/indexed">上次成功实验</a><a className="nav-link" href="/arena">符号竞技场</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="scope-label">未发现精确关系</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>没有命中，就不把近似答案叫作发现</h1>
          <p className="lede">本轮将八个数字的顺序关系交给同一套组合搜索。匿名成功语义降低了误差，但五个不同结构都留下已知反例，因此全部进入错题库，成功公式房间保持不变。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal"><div className="signal-ring"><strong>{report.search_with_library.best_fit_mse}</strong><span>当前最低 MSE</span></div><p>最大单点误差 {report.search_with_library.best_maximum_absolute_error}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>给定数字</p><strong>{report.learner_received.numeric_values.length}</strong><span>{report.learner_received.numeric_values.join(" · ")}</span></article>
        <article className="metric-card accent-violet"><p>无库最低 MSE</p><strong>{report.control_without_library.best_fit_mse}</strong><span>{report.control_without_library.programs_generated.toLocaleString()} 个结构</span></article>
        <article className="metric-card accent-amber"><p>有库最低 MSE</p><strong>{report.search_with_library.best_fit_mse}</strong><span>仍不满足精确门</span></article>
        <article className="metric-card accent-slate"><p>写入错题库</p><strong>{report.five_candidate_feedback.length}</strong><span>成功房间新增 0</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">ADJACENT SUBTRACTION</p><h2>自动建立的差分工作区</h2></div></div>
          <dl className="receipt-list">
            <div><dt>原始层</dt><dd>{report.learner_received.numeric_values.join(", ")}</dd></div>
            <div><dt>第一层</dt><dd>{report.derived_workspace.first_layer.join(", ")}</dd></div>
            <div><dt>第二层</dt><dd>{report.derived_workspace.second_layer.join(", ")}</dd></div>
          </dl>
          <div className="posthoc-note"><span>BEST FAILED CANDIDATE</span><strong>{expression(best.program)}</strong><small>输出：{best.training_outputs.join(", ")}；它没有覆盖给定数据，所以只是一道已记录的错题。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLES</p><h2>最佳候选的已知反例</h2></div><span className="status-pill">{best.counterexamples.length} FAILED</span></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>位置</span><span>程序输出</span><span>给定值</span><span>结果</span></div>
            {best.counterexamples.map((item) => <div className="blind-row" key={item.index}><strong>{item.index}</strong><span>{item.predicted}</span><span>{item.observed}</span><span className="status-word">不等</span></div>)}
          </div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE DISTINCT LOGIC STRUCTURES</p><h2>五个候选，五组可核验输出</h2></div><span className="scope-label">全部拒绝</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>程序</span><span>MSE</span><span>归档</span></div>
          {report.five_candidate_feedback.map((item) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><code title={item.training_outputs.join(", ")}>{expression(item.program)}</code><strong>{item.fit_mse}</strong><code>{item.mistake_id}</code></div>)}
        </div>
      </section>

      <section className="surface standalone-limitations">
        <div className="section-heading"><div><p className="eyebrow">BOUNDARY</p><h2>本轮结论边界</h2></div></div>
        <ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>关系探测失败 · 五候选反例 · 错题入库 · 成功房间零新增</span></div><code>{report.learner_received.opaque_semantic_operation_ids.join(", ")}</code></footer>
    </main>
  );
}
