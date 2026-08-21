import reportData from "../../data/strict_counter_foundation_v10_latest.json";

const report = reportData;
const selected = report.discovery.selected;
const proof = report.proof;
const laws = selected.algebraic_profile;

const lawRows = [
  ["依赖两个输入", laws.depends_on_both_inputs],
  ["交叉输入作用", laws.has_cross_input_interaction],
  ["交换律", laws.commutative],
  ["结合律", laws.associative],
  ["恒等元 = 1", laws.identity === 1],
  ["零元 = 0", laws.annihilator === 0],
  ["左分配律", laws.left_distributive_over_previously_verified_combine],
  ["右分配律", laws.right_distributive_over_previously_verified_combine],
  ["单调性", laws.monotone],
] as const;

export default function FoundationV10Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">STRICT COUNTER DISCOVERY V10</p><p className="brand-name">AKGM-N0 / 无目标基础探索</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v11">商余新基础</a><a className="nav-link" href="/foundation-v9">V9能力测试</a><a className="nav-link" href="/meta-autonomy">自主探索</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">1个严格基础通过</span><span className="scope-label">TARGET-FREE / UNIVERSAL PROOF</span></div><h1>没有提供乘法目标，程序组合出了乘法</h1><p className="lede">搜索器只获得自然数计数器、加一、减一、判空、循环和四个寄存器。程序先匿名产生行为；通过九项通用代数性质和循环不变量之后，才被命名为自然数乘法。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{selected.candidate_id}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>1</strong><span>可提升行为</span></div><p>{proof.derived_normal_form}</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>生成程序</p><strong>{report.discovery.programs_generated}</strong><span>两层计数循环枚举</span></article>
      <article className="metric-card accent-violet"><p>实际执行</p><strong>{report.discovery.programs_executed}</strong><span>安全边界内终止</span></article>
      <article className="metric-card accent-amber"><p>不同计算行为</p><strong>{report.discovery.behavior_classes}</strong><span>按输出指纹去重</span></article>
      <article className="metric-card accent-cyan"><p>全称证明</p><strong>{proof.obligations.filter(item => item.passed).length}/{proof.obligations.length}</strong><span>循环不变量与终止性</span></article>
      <article className="metric-card accent-slate"><p>原始指令节点</p><strong>{selected.primitive_node_count}</strong><span>无乘除法操作码</span></article>
    </section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">DISCOVERED PROGRAM</p><h2>程序真实执行结构</h2></div><span className="status-chip good">PROVEN</span></div><pre className="code-block operation-code">{JSON.stringify(selected.program, null, 2)}</pre><div className="posthoc-note"><span>证明后命名</span><strong>{proof.posthoc_name}</strong><small>{proof.universal_statement}</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">GENERIC LAW DETECTOR</p><h2>九项性质全部成立</h2></div></div><div className="evidence-list">{lawRows.map(([label, passed]) => <div className="evidence-row" key={label}><div><strong>{label}</strong><span>通用检测器逐项重放</span></div><b>{passed ? "PASS" : "FAIL"}</b></div>)}</div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">UNIVERSAL INVARIANT</p><h2>不是有限样本拟合</h2></div><span className="status-chip good">{proof.obligations.length} OBLIGATIONS</span></div><div className="operator-discovery-grid">{proof.obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>{item.evidence}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>本次成果的准确分类</h2></div></div><ul><li>没有数字目标行、没有命名公式目标、没有乘法或除法操作码。</li><li>寄存器、单位增减、两层循环语法和代数性质检测器仍由主机提供。</li><li>因此这是“目标无关、受限语法内的结构发现”，不是无限制创造计算语义。</li><li>这是模型自身的新基础，不声称是人类尚未发现的新数学。</li></ul><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
