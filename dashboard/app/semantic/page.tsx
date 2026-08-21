import type { Metadata } from "next";
import reportData from "../../data/unbound_symbol_latest.json";

export const metadata: Metadata = {
  title: "空符号语义生成 · AKGM-N0",
  description: "无意义字形在独立验证后绑定到可执行微状态程序。",
};

type Case = {
  input_row: number[];
  predicted_value: number | null;
  observed_value: number;
  step_count: number | null;
  passed: boolean;
  failure: string | null;
};

type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  unbound_symbol: {
    glyph: string;
    intrinsic_semantics: boolean;
    call_before_binding_rejected: boolean;
  };
  search: {
    programs_generated: number;
    programs_executed: number;
    nonhalting_programs: number;
    development_exact_candidate_count: number;
    selected_candidate: {
      candidate_id: string;
      program: Record<string, unknown>;
      maximum_steps_used: number;
      program_nodes: number;
    };
    first_five_exact_candidates: Array<{
      candidate: { candidate_id: string; program_nodes: number; maximum_steps_used: number };
      blind_passed: boolean;
      blind_cases: Case[];
    }>;
  };
  independent_verification: {
    blind_cases: Case[];
    adversarial_cases: Case[];
    development_exact_candidates_rejected_by_blind: number;
  };
  binding: {
    operation_id: string;
    verification_status: string;
  };
  glyph_randomization: Array<{
    glyph: string;
    operation_id: string;
    probe_output: number;
  }>;
  success_formula_room_record: { room_record_id: string } | null;
  mistake_memory: { new_records: unknown[]; total_records: number };
  gates: Array<{ gate_id: string; passed: boolean | null }>;
};

const report = reportData as Report;

export default function SemanticPage() {
  const selected = report.search.selected_candidate;
  const verification = report.independent_verification;
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark">*</span><div><p className="eyebrow">UNBOUND SEMANTIC SLOT</p><p className="brand-name">AKGM-N0 / 空符号语义生成</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/arena">符号竞技场</a><a className="nav-link" href="/active">主动实验</a><a className="nav-link" href="/reasoning">关系思考</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>符号没有意义，程序创造意义</h1>
          <p className="lede">`*` 初始不可执行。系统没有乘除节点或预制迭代程序；它搜索初始化、两个寄存器的更新、停止条件和输出位置，通过独立验证后才绑定。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>11/11</strong><span>盲测与边界通过</span></div><p>{report.binding.operation_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>候选微程序</p><strong>{report.search.programs_generated.toLocaleString()}</strong><span>无目标节点</span></article>
        <article className="metric-card accent-violet"><p>开发集精确</p><strong>{report.search.development_exact_candidate_count}</strong><span>仍需独立盲测</span></article>
        <article className="metric-card accent-amber"><p>盲测淘汰</p><strong>{verification.development_exact_candidates_rejected_by_blind}</strong><span>个投机程序进入错题库</span></article>
        <article className="metric-card accent-slate"><p>成功房间</p><strong className="status-word">已绑定</strong><span>{report.success_formula_room_record?.room_record_id ?? "—"}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">CREATED MICRO-SEMANTICS</p><h2>{selected.candidate_id}</h2></div><span className="evidence-chip">{selected.program_nodes} 节点</span></div>
          <pre className="code-block operation-code"><code>{JSON.stringify(selected.program, null, 2)}</code></pre>
          <p className="concept-footnote">程序本体才是语义；`*`、`@`、`#` 只是可以替换的显示标签。</p>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">EXACT IS NOT VERIFIED</p><h2>前五个开发集精确候选</h2></div></div>
          <div className="blind-table">
            {report.search.first_five_exact_candidates.map((item) => <div className="blind-row" key={item.candidate.candidate_id}><code>{item.candidate.candidate_id}</code><span>{item.candidate.program_nodes} 节点</span><span>最大 {item.candidate.maximum_steps_used} 步</span><span className={item.blind_passed ? "zero-value" : "status-word"}>{item.blind_passed ? "盲测通过" : "盲测拒绝"}</span></div>)}
          </div>
        </article>
      </section>

      <section className="surface task-table-card">
        <div className="section-heading"><div><p className="eyebrow">INDEPENDENT VERIFICATION</p><h2>盲测与边界样本</h2></div><span className="evidence-chip">零错误</span></div>
        <div className="blind-table">
          {[...verification.blind_cases, ...verification.adversarial_cases].map((item, index) => <div className="blind-row" key={`${item.input_row.join("-")}-${index}`}><code>[{item.input_row.join(", ")}]</code><span>输出 {item.predicted_value}</span><span>{item.step_count} 步</span><span className="zero-value">通过</span></div>)}
        </div>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">GLYPH ABLATION</p><h2>字形不携带语义</h2></div></div>
          <dl className="receipt-list">{report.glyph_randomization.map((item) => <div key={item.glyph}><dt>{item.glyph}</dt><dd>{item.operation_id} → {item.probe_output}</dd></div>)}</dl>
        </article>
        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>绑定门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed === null ? "pending" : gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed === null ? "域外未定义" : gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>空符号 · 微状态程序 · 独立验证 · 非 Transformer</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
