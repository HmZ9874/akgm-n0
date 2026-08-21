import reportData from "../../data/strict_foundation_expansion_v13_latest.json";

const report = reportData;

export default function FoundationV13Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">STRICT FOUNDATION EXPANSION V13</p><p className="brand-name">AKGM-N0 / 全基础域扩张</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v14">组合代数闭包</a><a className="nav-link" href="/foundation-v12">幂基础</a><a className="nav-link" href="/foundation-v11">商余基础</a><a className="nav-link" href="/foundation-v10">乘法基础</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">3/3基础完成扩张</span><span className="scope-label">VERIFIED DOMAIN CLOSURE</span></div><h1>三个严格基础都进入了更大的数域</h1><p className="lede">系统没有重新发明基础，而是为每个已证明语义枚举最小符号、修正或倒数策略，并检查原有守恒律、递推律和唯一性是否在新数域继续成立。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{report.verdict}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>3</strong><span>已验证域扩张</span></div><p>新基础计数 +0</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>基础覆盖</p><strong>{report.summary.foundations_expanded}/{report.summary.foundations_considered}</strong><span>V10、V11、V12</span></article>
      <article className="metric-card accent-violet"><p>证明义务</p><strong>{report.summary.proof_obligations_passed}/{report.summary.proof_obligations_total}</strong><span>符号分支与隐藏重放</span></article>
      <article className="metric-card accent-amber"><p>域扩张</p><strong>{report.summary.verified_domain_extensions}</strong><span>全部进入成功记录</span></article>
      <article className="metric-card accent-slate"><p>新增基础</p><strong>{report.summary.new_foundations_claimed}</strong><span>避免重复计数</span></article>
      <article className="metric-card accent-cyan"><p>分类</p><strong className="status-word">闭包</strong><span>verified domain closure</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">ALL EXPANSIONS</p><h2>每个基础的搜索与证明</h2></div><span className="status-chip good">ALL PASS</span></div><div className="operator-discovery-grid">{report.expansions.map(item => <article className="metric-card" key={item.source}><p><code>{item.source} · {item.proof.expansion_id}</code></p><strong className="operator-name">{item.proof.posthoc_name}</strong><span>{item.proof.domain}</span><small>{item.search.policies_generated} policies · {item.search.behavior_classes} behaviors · {item.search.passing_behavior_classes} pass</small></article>)}</div></section>

    <section className="content-grid lower-grid">{report.expansions.map(item => <article className="surface comparison-card" key={`${item.source}-proof`}><div className="section-heading"><div><p className="eyebrow">{item.source} UNIVERSAL PROOF</p><h2>{item.proof.posthoc_name}</h2></div><span className="status-chip good">{item.proof.obligations.filter(obligation => obligation.passed).length}/{item.proof.obligations.length}</span></div><p className="lede">{item.proof.universal_statement}</p><div className="evidence-list">{item.proof.obligations.map(obligation => <div className="evidence-row" key={obligation.obligation_id}><div><strong>{obligation.obligation_id}</strong><span>{obligation.evidence}</span></div><b>{obligation.passed ? "PASS" : "FAIL"}</b></div>)}</div></article>)}</section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>扩张不等于新基础</h2></div></div><ul><li>整数、有理数的表示方法和策略搜索语法由主机提供。</li><li>候选没有目标输出行，但只在有限策略空间中搜索。</li><li>证明覆盖整个声明域，不只是有限测试数据。</li><li>三项结果记录为域闭包，不增加严格基础数量。</li><li>不声称获得人类未知数学。</li></ul><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
