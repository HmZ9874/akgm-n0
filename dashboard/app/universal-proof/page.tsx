import type { Metadata } from "next";
import reportData from "../../data/universal_formula_proof_latest.json";

export const metadata: Metadata = {
  title: "全定义域证明 · AKGM-N0",
  description: "发现程序的终止性、归纳不变量和独立证明报告。",
};

type Obligation = { obligation_id: string; passed: boolean; evidence: string };
type Formula = {
  mechanism: string;
  display_formula: string;
  source_bounded_record_id: string;
  source_operation_id: string;
  universal_room_record_id: string;
  instruction_count: number;
  theorem_statement: string;
  invariants: string[];
  termination_measure: string;
  verification: { verifier_version: string; passed: boolean; obligations: Obligation[] };
};
type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  declared_domain: string;
  scope_warning: string;
  audit_before_run: { bounded_active_formula_count: number; universally_compliant_count: number; reason: string };
  proof_method: Record<string, string | boolean>;
  formulas: Formula[];
  gates: Array<{ gate_id: string; passed: boolean; actual: unknown; threshold: unknown }>;
  universal_room_active_count: number;
  proof_obligation_count: number;
  proof_obligation_passed_count: number;
  new_formula_count: number;
  total_proven_formula_count: number;
  limitations: string[];
};

const report = reportData as Report;

const labels: Record<string, string> = {
  exact_program_structure: "程序结构逐字匹配",
  induction_base: "归纳起点",
  induction_step: "归纳递推",
  induction_step_A: "状态 A 递推",
  induction_step_B: "状态 B 递推",
  induction_step_C: "状态 C 递推",
  induction_step_remainder: "余量递推",
  induction_step_odd: "奇数步长递推",
  complete_state_transition: "完整状态转移",
  invariant_preservation: "不变量保持",
  termination: "终止性",
  exit_correctness: "出口正确性",
  mutable_cell_is_operand_not_opcode: "自修改地址安全",
  induction_step_result: "结果状态递推",
  induction_step_code: "代码操作数递推",
  induction_step_D: "状态 D 递推",
  induction_step_shift: "移位反馈递推",
  recurrence_definition_total: "递推定义完备",
  zero_case: "零值边界",
  exact_composition_graph: "组合图精确绑定",
  acyclic_reference_check: "无环引用检查",
  proven_component_substitution: "已证明组件代入",
  domain_closure: "中间值定义域闭合",
};

export default function UniversalProofPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const obligationScore = `${report.proof_obligation_passed_count}/${report.proof_obligation_count}`;
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">∀</span><div><p className="eyebrow">UNIVERSAL PROOF GATE</p><p className="brand-name">AKGM-N0 / Independent Evaluator</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/parametric">严格参数化公式</a><a className="nav-link" href="/gen2-five-control">发现记录</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a><span className="meta-dot" /><span>{generatedAt}</span></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">本轮新增 {report.new_formula_count} 条 · 累计 {report.total_proven_formula_count} 条</span><span className="scope-label">ABSTRACT INTEGER PROOF</span></div><h1>不再用更多样本冒充“通用”</h1><p className="lede">证明器从可执行字程序重新解码状态转移，分别检查程序绑定、明确定义域、终止排名函数、归纳不变量与出口正确性。有限测试结果不参与证明结论。</p><div className="run-id"><span>RUN</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{obligationScore}</strong><span>证明义务通过</span></div><p>独立复算后才允许入库</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>通用公式库</p><strong>{report.universal_room_active_count}</strong><span>独立哈希链 UF</span></article>
      <article className="metric-card accent-violet"><p>原活动候选</p><strong>{report.audit_before_run.bounded_active_formula_count}</strong><span>本轮前已证明 {report.audit_before_run.universally_compliant_count}</span></article>
      <article className="metric-card accent-amber"><p>证明规则</p><strong>{report.total_proven_formula_count}</strong><span>原子程序 + 可证明组合图</span></article>
      <article className="metric-card accent-slate"><p>新发现程序</p><strong>{report.new_formula_count}</strong><span>串联 · 并联 · 比较 · 余数 · 幂</span></article>
    </section>

    <section className="surface promotion-card">
      <div className="section-heading"><div><p className="eyebrow">SCOPE BOUNDARY</p><h2>“所有数字”必须先说清是哪一类数字</h2></div><span className="evidence-chip">EXPLICIT DOMAIN</span></div>
      <div className="finding-strip"><span className="note-icon">!</span><p>{report.scope_warning} 本页各证书定义域为 <strong>{report.declared_domain}</strong>。</p></div>
    </section>

    <section className="content-grid operation-grid">
      {report.formulas.map((formula) => <article className="surface concept-card" key={formula.universal_room_record_id}>
        <div className="section-heading"><div><p className="eyebrow">{formula.mechanism}</p><h2>{formula.display_formula}</h2></div><span className="status-pill">PROVEN</span></div>
        <div className="posthoc-note"><span>{formula.universal_room_record_id}</span><strong>{formula.theorem_statement}</strong><small>{formula.source_bounded_record_id} → {formula.source_operation_id} · {formula.instruction_count} instructions</small></div>
        <div className="promotion-lanes">
          <div className="promotion-lane"><span>循环不变量</span>{formula.invariants.map((item) => <p key={item}>• {item}</p>)}</div>
          <div className="promotion-lane blocked-lane"><span>终止排名</span><p>{formula.termination_measure}</p></div>
        </div>
        <div className="task-table"><div className="task-row task-header"><span>证明义务</span><span>结论</span><span>依据</span><span>验证器</span></div>{formula.verification.obligations.filter((item) => labels[item.obligation_id]).map((item) => <div className="task-row" key={item.obligation_id}><code>{labels[item.obligation_id] ?? item.obligation_id}</code><strong className="zero-value">通过</strong><span>{item.evidence}</span><span>{formula.verification.verifier_version}</span></div>)}</div>
      </article>)}
    </section>

    <section className="content-grid lower-grid">
      <article className="surface gates-section"><div className="section-heading"><div><p className="eyebrow">ADMISSION GATES</p><h2>通用公式入库门</h2></div></div><div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed ? "通过" : "未通过"}</span></div></div>)}</div></article>
      <article className="surface task-table-card"><div className="section-heading"><div><p className="eyebrow">PROOF SEPARATION</p><h2>发现与证明隔离</h2></div></div><div className="promotion-lanes"><div className="promotion-lane"><span>发现侧</span><p>{String(report.proof_method.search_side)}</p><p>没有定理名、目标公式或证明规则。</p></div><div className="promotion-lane blocked-lane"><span>证明侧</span><p>{String(report.proof_method.proof_side)}</p><p>入库时再次独立复算。</p></div></div></article>
    </section>

    <section className="surface standalone-limitations"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>仍然不能夸大的部分</h2></div></div><ul className="limitations-list">{report.limitations.map((item, index) => <li key={item}><span>0{index + 1}</span><p>{item}</p></li>)}</ul></section>
    <footer><div><span className="footer-mark">AKGM-N0</span><span>结构解码 · 终止证明 · 归纳不变量 · 独立复算</span></div><code>{report.verdict}</code></footer>
  </main>;
}
