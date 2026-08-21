import reportData from "../../data/rigid_body_mechanics_v27_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const discovery = acceptance.discovery;
const graph = acceptance.mechanics_capability_graph;
const passed = acceptance.proof_obligations.filter(item => item.passed).length;

export default function MechanicsV27Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">RIGID-BODY MECHANICS V27</p><p className="brand-name">AKGM-N0 / 刚体惯性与完整力学控制器</p></div></div><div className="run-meta"><a className="nav-link" href="/mechanics-v28">连续动力学 V28</a><a className="nav-link" href="/mechanics-v26">旋转力学</a><a className="nav-link" href="/mechanics-v25">碰撞力学</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V27 验收 {passed}/12</span><span className="scope-label">COMPOSE → RESPOND → ROTATE → AUDIT → SELECT GAP</span></div><h1>系统发现了固定轴多质点刚体力学，但拒绝虚报“完整力学”</h1><p className="lede">匿名刚体由多个三通道点组成。系统从 12 个聚合程序中唯一找到能够解释所有角响应的结构，并把 V25 的双守恒碰撞迁移到旋转状态。同时，完整性控制器逐项检查十五个力学领域；任何缺项都禁止宣称完成。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{graph.verified_domains}/{graph.total_domains}</strong><span>力学领域</span></div><p>下一缺口：{graph.next_selected_gap}</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>聚合候选</p><strong>{discovery.aggregate_candidates_generated}</strong><span>唯一选出一个</span></article>
      <article className="metric-card accent-violet"><p>角权重候选</p><strong>{discovery.angular_weight_candidates_generated}</strong><span>唯一选出 AGG</span></article>
      <article className="metric-card accent-amber"><p>已验证领域</p><strong>{graph.verified_domains}</strong><span>共 {graph.total_domains} 项</span></article>
      <article className="metric-card accent-cyan"><p>平行轴案例</p><strong>{acceptance.proofs.parallel_axis.hidden_replay.length}</strong><span>全部恒等通过</span></article>
      <article className="metric-card accent-slate"><p>错误结构</p><strong>{acceptance.mutation_audits.length}</strong><span>全部反例拒绝</span></article>
    </section>

    <section className="content-grid operation-grid"><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">DISCOVERED AGGREGATE</p><h2>I_R · 点集转动惯量</h2></div><span className="status-chip good">UNIQUE</span></div><div className="posthoc-note"><span>匿名程序</span><strong><code>{discovery.selected_aggregate.opaque_program}</code></strong></div><div className="posthoc-note"><span>证明后翻译</span><strong>I = Σᵢ mᵢ(xᵢ²+yᵢ²)</strong><small>固定轴点质量转动惯量。</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">ANGULAR RESPONSE</p><h2>L_B · 刚体角动量</h2></div><span className="status-chip good">PROVED</span></div><div className="posthoc-note"><span>匿名程序</span><strong><code>{discovery.selected_angular_quantity.opaque_program}</code></strong></div><div className="posthoc-note"><span>证明后翻译</span><strong>Δω = Jθ/I　·　L = Iω</strong><small>角作用改变角状态；聚合加权状态恰好改变 Jθ。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">DERIVED MECHANICS</p><h2>由同一聚合结构推演出的关系</h2></div></div><div className="operator-discovery-grid"><article className="metric-card"><p>INERTIA</p><strong className="operator-name">I = Σmᵢrᵢ²</strong><span>多点结构的角响应尺度</span></article><article className="metric-card"><p>RESPONSE</p><strong className="operator-name">IΔω = Jθ</strong><span>角作用平衡</span></article><article className="metric-card"><p>ANGULAR TOTAL</p><strong className="operator-name">L = Iω</strong><span>角动量</span></article><article className="metric-card"><p>QUADRATIC TOTAL</p><strong className="operator-name">E₂ = Iω²</strong><span>传统转动动能的两倍</span></article><article className="metric-card"><p>AXIS SHIFT</p><strong className="operator-name">I_O = I_CM + Md²</strong><span>由平方展开证明</span></article><article className="metric-card"><p>ANGULAR COLLISION</p><strong className="operator-name">L 与 E₂ 双守恒</strong><span>V25 程序迁移到转动状态</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MECHANICS COMPLETENESS GATE</p><h2>“完整”必须逐项有证据</h2></div><span className="status-chip">{graph.full_mechanics_claim_allowed ? "COMPLETE" : "INCOMPLETE — CLAIM BLOCKED"}</span></div><div className="operator-discovery-grid">{graph.domains.map(item => <article className={`metric-card ${item.status === "verified" ? "accent-cyan" : "accent-slate"}`} key={item.capability_id}><p><code>{item.capability_id}</code></p><strong className="operator-name">{item.capability}</strong><span>{item.status === "verified" ? `已验证 · ${item.evidence_version}` : "尚未发现"}</span></article>)}</div><div className="boundary-box"><p>下一项自主研究</p><code>{graph.next_selected_gap}</code><span>{graph.selection_reason}</span></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立证据</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>当前不是完整力学</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
