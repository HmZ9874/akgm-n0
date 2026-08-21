import reportData from "../../data/proof_driven_program_construction_v20_latest.json";

type Expr = { op: string; atom?: string; args?: Expr[] };

const report = reportData;
const acceptance = report.acceptance;
const construction = acceptance.construction;
const proofs = acceptance.proofs;
const translations = acceptance.posthoc_capability_translation as Record<string, string>;
const passed = acceptance.proof_obligations.filter(item => item.passed).length;

function renderExpression(expression: Expr): string {
  if (expression.op === "atom") return expression.atom || "?";
  const glyph = expression.op === "omega" ? "SEM" : "MERGE";
  return `${glyph}<${renderExpression(expression.args![0])},${renderExpression(expression.args![1])}>`;
}

export default function FoundationV20Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">PROOF-DRIVEN CONSTRUCTION V20</p><p className="brand-name">AKGM-N0 / 从已证明语义构造新程序</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v21">有向有理数</a><a className="nav-link" href="/foundation-v19">数学发现</a><a className="nav-link" href="/foundation-v18">目标解题</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V20 验收 {passed}/12</span><span className="scope-label">PROVEN SEMANTIC → PROGRAM SEARCH → UNIVERSAL PROOF</span></div><h1>系统开始把已证明的运算组合成更高层数学程序</h1><p className="lede">输入仍然只有 V19 的匿名自然数语义、计数器合并和事件控制。系统重新搜索商余程序，再在正分母整数对上生成 2,176 个候选程序；只有换表示不变、封闭、结合、交换且具有单位元的程序才能进入成功房间。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>4</strong><span>构造并证明</span></div><p>商余 · 方程 · 两个数对运算</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>事件程序搜索</p><strong>{construction.partition_programs_generated}</strong><span>仅 1 个行为类通过证明门</span></article>
      <article className="metric-card accent-violet"><p>数对程序构造</p><strong>{construction.pair_programs_generated}</strong><span>{construction.pair_behavior_classes} 个不同语义类</span></article>
      <article className="metric-card accent-amber"><p>提升数对程序</p><strong>{construction.promoted_pair_operations.length}</strong><span>均有全域证明</span></article>
      <article className="metric-card accent-cyan"><p>方程证明</p><strong>{proofs.equation_solver.passed ? "通过" : "失败"}</strong><span>存在性、正确性、唯一性</span></article>
      <article className="metric-card accent-slate"><p>错误程序拦截</p><strong>{acceptance.mutation_audits.length}</strong><span>缩短变异均有反例</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CONSTRUCTION CHAIN</p><h2>程序是如何逐层长出来的</h2></div><span className="status-chip good">NO NAMED SOLUTION PROGRAM</span></div><div className="operator-discovery-grid"><article className="metric-card"><p>01 / FOUNDATION</p><strong className="operator-name">SEM&lt;x,y&gt;</strong><span>V19 已对所有自然数证明</span></article><article className="metric-card"><p>02 / PARTITION</p><strong className="operator-name">事件计数器 → (q,r)</strong><span>3,072 个程序中唯一通过守恒门</span></article><article className="metric-card"><p>03 / EQUATION</p><strong className="operator-name">残差零门 + 商见证</strong><span>构成自然数方程的判定程序</span></article><article className="metric-card"><p>04 / EQUIVALENCE</p><strong className="operator-name">交叉 SEM 相等</strong><span>把不同整数对合并为同一对象</span></article><article className="metric-card"><p>05 / CLOSURE</p><strong className="operator-name">搜索数对输出程序</strong><span>要求表示无关与代数定律</span></article><article className="metric-card"><p>06 / PROOF</p><strong className="operator-name">符号归一 + 隐藏重放</strong><span>有限搜索不作为最终证明</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROMOTED PROGRAMS</p><h2>真正进入成功房间的程序本体</h2></div></div><div className="operator-discovery-grid">{construction.promoted_pair_operations.map(item => <article className="metric-card" key={item.candidate_id}><p><code>{item.candidate_id}</code></p><strong className="operator-name">({renderExpression(item.program.numerator)}, {renderExpression(item.program.denominator)})</strong><span>identity ({item.law_profile.identity_pair.join(",")}) · invariant {String(item.law_profile.representation_invariant)}</span><small>证明后翻译：{translations[item.candidate_id]}</small></article>)}</div></section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">EQUATION EXECUTION</p><h2>程序实际给出的解与余量</h2></div><span className="status-chip good">SOUND + COMPLETE</span></div><div className="evidence-list">{construction.equation_examples.map(item => <div className="evidence-row" key={`${item.coefficient}-${item.target}`}><div><strong>SEM&lt;{item.coefficient},x&gt; = {item.target}</strong><span>candidate {item.candidate} · residual {item.residual}</span></div><b>{item.solved ? `x=${item.candidate}` : "自然数域无解"}</b></div>)}</div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">POSTHOC TRANSLATION</p><h2>等证明完成后再对应人类数学</h2></div></div><div className="receipt-list"><div><dt>事件二输出程序</dt><dd>欧几里得商余</dd></div><div><dt>残差零见证程序</dt><dd>一元乘法方程</dd></div><div><dt>整数对交叉关系</dt><dd>分数等价</dd></div><div><dt>两个提升程序</dt><dd>非负有理数加法、乘法</dd></div></div><div className="posthoc-note"><span>重要边界</span><strong>名称不是搜索条件</strong><small>学习器保存的是程序结构、行为签名和证明证书。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">UNIVERSAL PROOFS</p><h2>不是样本拟合</h2></div></div><div className="operator-discovery-grid"><article className="metric-card"><p><code>{proofs.partition.semantic_id}</code></p><strong className="operator-name">商余存在且唯一</strong><span>{proofs.partition.universal_statement}</span></article><article className="metric-card"><p><code>{proofs.equation_solver.proof_id}</code></p><strong className="operator-name">方程程序充要且唯一</strong><span>{proofs.equation_solver.universal_statement}</span></article><article className="metric-card"><p><code>{proofs.pair_equivalence.proof_id}</code></p><strong className="operator-name">数对关系是等价关系</strong><span>{proofs.pair_equivalence.universal_statement}</span></article>{proofs.pair_operations.map(item => <article className="metric-card" key={item.proof_id}><p><code>{item.proof_id}</code></p><strong className="operator-name">{item.posthoc_name}</strong><span>{item.universal_statement}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项程序构造验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立验证</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>已经进入方程与有理结构，但还不是完整代数系统</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
