import type { Metadata } from "next";
import reportData from "../../data/indexed_semantic_reuse_latest.json";

export const metadata: Metadata = {
  title: "有序关系复用实验 · AKGM-N0",
  description: "位置、差分工作区与匿名成功语义的组合验证。",
};

type Node = {
  op: string;
  args?: Node[];
  constant?: number;
  operation_id?: string;
};

type Candidate = {
  rank: number;
  candidate_id: string;
  program: Node;
  fit_mse: number;
  maximum_absolute_error: number;
  exact: boolean;
  logic_signature: string;
  disposition: string;
};

type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: {
    numeric_values: number[];
    target_formula: boolean;
    natural_language_math_concepts: boolean;
    intrinsic_multiply_node: boolean;
    intrinsic_divide_node: boolean;
    sealed_extension_visible_during_search: boolean;
    opaque_success_room_operation_ids: string[];
  };
  derived_workspace: {
    construction: string;
    first_layer: number[];
    second_layer: number[];
  };
  control_without_success_room: {
    programs_generated: number;
    behavior_classes: number;
    exact_candidate_found: boolean;
    best_candidate: Candidate;
  };
  search_with_success_room: {
    programs_generated: number;
    programs_executed: number;
    behavior_classes: number;
    exact_candidate_found: boolean;
  };
  five_candidate_feedback: Candidate[];
  winner: Candidate & {
    parent_operation_ids: string[];
    sealed_extension: Array<{ index: number; predicted: number; observed: number }>;
  };
  gates: Array<{ gate_id: string; passed: boolean }>;
  success_room_record: { room_record_id: string; operation_id: string } | null;
  mistake_record_ids: string[];
  limitations: string[];
};

const report = reportData as Report;

function renderProgram(node: Node): string {
  if (node.op === "q_index") return "i";
  if (node.op === "q_constant") return String(node.constant);
  const [left, right] = node.args ?? [];
  if (!left || !right) return node.op;
  if (node.op === "q_add") return `(${renderProgram(left)} + ${renderProgram(right)})`;
  if (node.op === "q_subtract") return `(${renderProgram(left)} − ${renderProgram(right)})`;
  if (node.op === "q_semantic_call") return `SEM⟨${renderProgram(left)}, ${renderProgram(right)}⟩`;
  return node.op;
}

export default function IndexedPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">i</span><div><p className="eyebrow">INDEXED SEMANTIC REUSE</p><p className="brand-name">AKGM-N0 / 有序关系实验</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/probe">最新探测</a><a className="nav-link" href="/arena">符号竞技场</a><a className="nav-link" href="/semantic">空符号实验</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>没有乘法节点，调用自己发现的匿名程序</h1>
          <p className="lede">输入仍然只是七个有顺序的数字。搜索先建立相邻差分工作区，再把位置与成功房间中的匿名可执行语义组合；目标公式、数学概念和封存答案均未进入搜索。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>0</strong><span>训练与封存误差</span></div><p>{winner.candidate_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>输入数字</p><strong>7</strong><span>{report.learner_received.numeric_values.join(" · ")}</span></article>
        <article className="metric-card accent-violet"><p>无库对照</p><strong>{report.control_without_success_room.exact_candidate_found ? "命中" : "失败"}</strong><span>{report.control_without_success_room.programs_generated.toLocaleString()} 个结构</span></article>
        <article className="metric-card accent-amber"><p>匿名语义复用</p><strong>{report.search_with_success_room.exact_candidate_found ? "命中" : "失败"}</strong><span>{report.search_with_success_room.behavior_classes} 个行为类</span></article>
        <article className="metric-card accent-slate"><p>错题入库</p><strong>{report.mistake_record_ids.length}</strong><span>种不同底层结构</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DERIVED WORKSPACE</p><h2>框架自己生成的中间层</h2></div><span className="evidence-chip">只用相邻相减</span></div>
          <dl className="receipt-list">
            <div><dt>原始层</dt><dd>{report.learner_received.numeric_values.join(", ")}</dd></div>
            <div><dt>第一层</dt><dd>{report.derived_workspace.first_layer.join(", ")}</dd></div>
            <div><dt>第二层</dt><dd>{report.derived_workspace.second_layer.join(", ")}</dd></div>
            <div><dt>生成规则</dt><dd>{report.derived_workspace.construction}</dd></div>
          </dl>
          <div className="posthoc-note"><span>WINNING EXECUTABLE</span><strong>{renderProgram(winner.program)}</strong><small>{winner.parent_operation_ids.join(", ")} · SEM 只是成功房间操作编号的显示名；其含义来自程序和验证记录，不来自符号本身。</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">SEALED EXTENSION</p><h2>搜索后才打开的五项验证</h2></div><span className="status-pill">5 / 5 EXACT</span></div>
          <div className="blind-table">
            <div className="blind-row blind-header"><span>位置</span><span>程序输出</span><span>封存值</span><span>误差</span></div>
            {winner.sealed_extension.map((item) => <div className="blind-row" key={item.index}><strong>{item.index}</strong><span>{item.predicted}</span><span>{item.observed}</span><span className="zero-value">{Math.abs(item.predicted - item.observed)}</span></div>)}
          </div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE DISTINCT LOGIC STRUCTURES</p><h2>本轮五个可执行候选</h2></div><span className="evidence-chip">1 成功 / 4 错题</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>结构</span><span>MSE</span><span>去向</span></div>
          {report.five_candidate_feedback.map((item) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><code title={item.logic_signature}>{renderProgram(item.program)}</code><strong className={item.exact ? "zero-value" : ""}>{item.fit_mse}</strong><span>{item.exact ? "成功公式房间" : "错题库"}</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">CONTROL</p><h2>缺口修补前后对照</h2></div></div>
          <dl className="receipt-list">
            <div><dt>仅加减时精确命中</dt><dd>{report.control_without_success_room.exact_candidate_found ? "是" : "否"}</dd></div>
            <div><dt>接入匿名成功语义后</dt><dd>{report.search_with_success_room.exact_candidate_found ? "精确命中" : "未命中"}</dd></div>
            <div><dt>目标公式提供</dt><dd>{report.learner_received.target_formula ? "是" : "否"}</dd></div>
            <div><dt>内置乘除节点</dt><dd>{report.learner_received.intrinsic_multiply_node || report.learner_received.intrinsic_divide_node ? "有" : "没有"}</dd></div>
            <div><dt>成功房间记录</dt><dd>{report.success_room_record?.room_record_id ?? "未写入"}</dd></div>
          </dl>
        </article>

        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>本轮验证门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>位置关系 · 差分工作区 · 匿名语义复用 · 独立封存验证</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
