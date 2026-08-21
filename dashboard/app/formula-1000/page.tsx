import reportData from "../../data/thousand_parametric_formulas_latest.json";

type Formula = {
  formula_id: string;
  operator_id: string;
  opcode: number;
  formula: string;
  coefficient_vector: number[];
  expanded_instruction_count: number;
  universal_proof_passed: boolean;
};

type Report = {
  run_id: string;
  verdict: string;
  stop_rule: { requested_new_formula_count: number; actual_new_formula_count: number; program_stopped: boolean };
  declared_scope: { formula_class: string; formal_domain: string; universal_statement: string; not_claimed: string };
  discovery: {
    historical_semantics_excluded: number;
    first_opcode: number;
    last_opcode: number;
    formula_names_given_to_search: boolean;
    target_formulas_given_to_search: boolean;
    selection_rule: string;
    instruction_length_distribution: Record<string, number>;
  };
  verification: {
    proof_method: string;
    finite_sampling_used_as_universal_proof: boolean;
    formula_proof_count: number;
    formula_count: number;
    hidden_replay_passed_count: number;
    hidden_replay_count: number;
  };
  formulas: Formula[];
  rooms: { success: string; mistakes: string; success_batch_count: number; mistake_record_count: number; hash_chained: boolean; proof_replayed_on_success_room_load: boolean };
  gates: Array<{ gate_id: string; passed: boolean; actual: number | boolean; required: number | boolean }>;
  limitations: string[];
};

const report = reportData as Report;

export default function ThousandFormulaPage() {
  const samples = [...report.formulas.slice(0, 10), report.formulas[499], report.formulas[999]];
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">1K</span><div><p className="eyebrow">MASS UNIVERSAL FORMULA SEARCH</p><p className="brand-name">AKGM-N0 / 第三代参数公式库</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/foundation">数学发展谱系</a><a className="nav-link" href="/parametric">参数公式</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">组合程序库（非基础发现）</span><span className="scope-label">OP132–OP1131</span></div><h1>1000个不同的加减组合语义</h1><p className="lede">这些程序仍可执行、可证明和可复用，但全部共享仿射加减底层逻辑，因此已从“基础数学发现”中移除。</p><div className="run-id"><span>RUN</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{report.verification.formula_proof_count}/{report.verification.formula_count}</strong><span>全称证明</span></div><p>{report.declared_scope.formula_class}</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>真正新增</p><strong>{report.stop_rule.actual_new_formula_count}</strong><span>达到停止门后结束</span></article>
      <article className="metric-card accent-violet"><p>跨代重复</p><strong>0</strong><span>历史 {report.discovery.historical_semantics_excluded} 条已排除</span></article>
      <article className="metric-card accent-amber"><p>隐藏重放</p><strong>{report.verification.hidden_replay_passed_count}/{report.verification.hidden_replay_count}</strong><span>只作交叉检查，不冒充证明</span></article>
      <article className="metric-card accent-slate"><p>错题记录</p><strong>{report.rooms.mistake_record_count}</strong><span>重复与语义伪造均不计数</span></article>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">UNIVERSAL PROOF CONTRACT</p><h2>“所有数字”被限定为明确的代数定义域</h2></div><span className="evidence-chip">非有限样本证明</span></div>
      <div className="promotion-lanes"><div className="promotion-lane"><span>全称命题</span><p>{report.declared_scope.universal_statement}</p><p>{report.declared_scope.formal_domain}</p></div><div className="promotion-lane blocked-lane"><span>不夸大</span><p>{report.declared_scope.not_claimed}</p><p>{report.verification.proof_method}</p></div></div>
      <div className="gate-grid">{report.gates.map(gate => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`}/><div><strong>{gate.gate_id}</strong><span>{String(gate.actual)} / {String(gate.required)}</span></div></div>)}</div>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">AUDITABLE SAMPLE</p><h2>公式样本：自由变量，不是固定数字特例</h2></div><span className="evidence-chip">完整目录 1000 条</span></div>
      <div className="gate-grid">{samples.map(item => <div className="gate-item" key={item.formula_id}><span className="gate-light passed"/><div><strong>OP{item.opcode} · {item.formula_id}</strong><span>{item.formula}</span><span>系数 [{item.coefficient_vector.join(", ")}] · 展开 {item.expanded_instruction_count} 条</span></div></div>)}</div>
    </section>

    <section className="content-grid lower-grid"><article className="surface"><div className="section-heading"><div><p className="eyebrow">PERSISTENCE</p><h2>成功公式房间</h2></div></div><p>{report.rooms.success}</p><p>哈希链：{report.rooms.hash_chained ? "是" : "否"}；载入时重放证明：{report.rooms.proof_replayed_on_success_room_load ? "是" : "否"}</p></article><article className="surface limitations-card"><div className="section-heading"><div><p className="eyebrow">BOUNDARIES</p><h2>这1000条不代表什么</h2></div></div><ol className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol></article></section>

    <footer><div><span className="footer-mark">AKGM-N0</span><span>非 Transformer · 精确语义去重 · 全称证明</span></div><code>{report.run_id}</code></footer>
  </main>;
}
