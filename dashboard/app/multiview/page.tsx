import type { Metadata } from "next";
import reportData from "../../data/multiview_relational_latest.json";

export const metadata: Metadata = {
  title: "多视角关系图 · AKGM-N0",
  description: "关系超图、候选控制程序与可寻址动态内存实验。",
};

type Fact = { fact_id: string; assertion: string; instruction: { op: string } };
type Candidate = {
  rank: number;
  candidate_id: string;
  kind: string;
  logic_signature: string;
  coverage_count: number;
  readable_steps: string[];
  exact: boolean;
  disposition: string;
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  learner_received: { numeric_values: number[]; opaque_semantic_operation_ids: string[]; memory_address_choices: string; instruction_order: string };
  views: {
    relation_graph: { fact_count: number; covered_values: number[]; uncovered_values: number[] };
    sequence_difference_workspace: { first_layer: number[]; second_layer: number[] };
  };
  exact_relation_facts: Fact[];
  five_program_feedback: Candidate[];
  gates: Array<{ gate_id: string; passed: boolean }>;
  formula_success_room_record: null;
  limitations: string[];
};

const report = reportData as Report;

const kindLabels: Record<string, string> = {
  graph_control: "关系图控制程序",
  generated_address_reuse: "新地址复用程序",
  direct: "单步关系程序",
};

export default function MultiViewPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const graph = report.views.relation_graph;
  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark gen1-mark">R</span><div><p className="eyebrow">MULTI-VIEW RELATIONAL MACHINE</p><p className="brand-name">AKGM-N0 / 关系图与动态内存</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/adaptive">自生成循环</a><a className="nav-link" href="/probe">单序列失败报告</a><a className="nav-link" href="/indexed">有序关系</a><a className="nav-link" href="/arena">符号竞技场</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid operation-hero">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">发现局部结构</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>从一条序列，扩展成可执行关系图</h1>
          <p className="lede">新工作区允许候选程序选择数字地址、执行操作、把结果追加到内存，再由下一条指令读取新地址。它找到了十条精确局部关系并连接七个数字，同时明确保留未连接的 17。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal"><div className="signal-ring"><strong>7/8</strong><span>关系图覆盖</span></div><p>{graph.fact_count} 条精确局部事实</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>精确关系事实</p><strong>{graph.fact_count}</strong><span>全部可重新执行</span></article>
        <article className="metric-card accent-violet"><p>已连接数字</p><strong>{graph.covered_values.length}</strong><span>{graph.covered_values.join(" · ")}</span></article>
        <article className="metric-card accent-amber"><p>未连接数字</p><strong>{graph.uncovered_values.join(", ")}</strong><span>没有被隐藏或强行拟合</span></article>
        <article className="metric-card accent-slate"><p>控制程序</p><strong>{report.five_program_feedback.length}</strong><span>五种不同底层结构</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">RELATION HYPERGRAPH</p><h2>关系图中的精确边</h2></div><span className="evidence-chip">{graph.fact_count} exact</span></div>
          <div className="blind-table">
            {report.exact_relation_facts.map((fact) => <div className="blind-row" key={fact.fact_id}><code>{fact.fact_id}</code><strong>{fact.assertion}</strong><span>{fact.instruction.op}</span><span className="zero-value">通过</span></div>)}
          </div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">DYNAMIC MEMORY TRACE</p><h2>新地址被下一步读取</h2></div><span className="status-pill">EXECUTABLE</span></div>
          <div className="replay-flow">
            <div><strong>64−56</strong><span>写入新地址 M8 = 8</span></div><b>→</b><div className="blocked-step"><strong>M8+23</strong><span>读取 M8，写入 M9 = 31</span></div>
          </div>
          <div className="finding-strip"><span className="note-icon">i</span><p>地址与指令顺序由候选程序选择；第二步并非重新读取原始的 8，而是读取第一步刚生成的内存地址。</p></div>
        </article>
      </section>

      <section className="surface promotion-card">
        <div className="section-heading"><div><p className="eyebrow">FIVE VERIFIED LOCAL PROGRAMS</p><h2>五种不同控制结构</h2></div><span className="scope-label">局部证据，不进入公式房间</span></div>
        <div className="task-table">
          <div className="task-row task-header"><span>候选</span><span>类型</span><span>覆盖</span><span>执行步骤</span></div>
          {report.five_program_feedback.map((item) => <div className="task-row" key={item.candidate_id}><code>#{item.rank} {item.candidate_id}</code><span>{kindLabels[item.kind] ?? item.kind}</span><strong>{item.coverage_count}</strong><code title={item.logic_signature}>{item.readable_steps.join(" ; ")}</code></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>为什么没有进入成功公式房间</h2></div></div>
          <ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>架构修补验收</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>多视角 · 关系超图 · 候选寻址 · 追加内存 · 局部证据边界</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
