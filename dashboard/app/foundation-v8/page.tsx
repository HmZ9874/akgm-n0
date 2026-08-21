import reportData from "../../data/foundation_expansion_v8_latest.json";

const report = reportData;
const foundation = report.foundation;
const candidateLabels = ["有理商候选", "范数组合候选", "反演候选", "极限候选"];

export default function FoundationV8Page() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">FOUNDATION EXPANSION V8</p><p className="brand-name">AKGM-N0 / 新基础第17–20层</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/foundation-v9">新基础21–24</a><a className="nav-link" href="/meta-autonomy">自主探索</a><a className="nav-link" href="/operator-500">500运算</a><a className="nav-link" href="/foundation">基础1–16</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy">
        <div className="verdict-row"><span className="verdict-badge">4个新基础通过</span><span className="scope-label">ANONYMOUS SEARCH + UNIVERSAL PROOF</span></div>
        <h1>数学基础谱系从16层推进到20层</h1>
        <p className="lede">搜索只接收匿名有理数对、单位范数点、正向运算轨迹和收缩序列，没有接收除法、三角、对数或极限名称。独立证明器在搜索结束后才赋予数学解释。</p>
        <div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{report.verdict}</code></div>
      </div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>20</strong><span>基础层级</span></div><p>新增4层</p></div>
    </section>

    <section className="metric-grid meta-score-grid">
      {foundation.expansion.candidate_counts.map((count, index) => <article className="metric-card accent-cyan" key={candidateLabels[index]}>
        <p>{candidateLabels[index]}</p><strong>{count}</strong><span>精确候选 {foundation.expansion.exact_counts[index]}</span>
      </article>)}
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">NEW FOUNDATIONS</p><h2>第17–20层独立证明</h2></div><span className="status-chip good">ALL PASS</span></div>
      <div className="operator-discovery-grid">
        {foundation.proof.foundations.map((item) => <article className="metric-card" key={item.semantic_id}>
          <p><code>LEVEL {item.foundation_level} · {item.semantic_id}</code></p>
          <strong className="operator-name">{item.posthoc_name}</strong>
          <span>{item.universal_statement}</span>
          <small>{item.obligations.filter((value) => value.passed).length}/{item.obligations.length} proof obligations</small>
        </article>)}
      </div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>局部基础突破，不等于完整分析学</h2></div></div>
      <ul>{foundation.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      <p className="digest-line">内容摘要 <code>{foundation.content_digest}</code></p>
    </section>
  </main>;
}
