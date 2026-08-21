import reportData from "../../data/autonomous_operator_research_v7_500_latest.json";

const report = reportData;
const research = report.research;

export default function Operator500Page() {
  const byTerms = [2, 3, 4].map((termCount) => ({
    termCount,
    count: research.operators.filter((item) => item.normal_form.length === termCount).length,
  }));

  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">AUTONOMOUS OPERATOR RESEARCH V7</p><p className="brand-name">AKGM-N0 / 无目标500运算闭包研究</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/meta-autonomy">自主探索</a><a className="nav-link" href="/high-school">高中门槛</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy">
        <div className="verdict-row"><span className="verdict-badge">500/500 已验证</span><span className="scope-label">TARGET-FREE EXACT CLOSURE</span></div>
        <h1>500条新入库运算，程序、支持结构、整数行为三重不同</h1>
        <p className="lede">研究器没有接收目标公式，只从两个匿名输入以及已证明的加法、乘法开始扩展。常数变化、系数变化、整体倍乘和相同单项式支持的变体全部禁止计数。</p>
        <div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{report.verdict}</code></div>
      </div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>500</strong><span>派生运算</span></div><p>整数二元多项式域</p></div>
    </section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>审查支持结构</p><strong>{research.supports_considered}</strong><span>无目标闭包候选</span></article>
      <article className="metric-card accent-cyan"><p>不同程序</p><strong>{research.unique_program_count}</strong><span>计算图摘要去重</span></article>
      <article className="metric-card accent-cyan"><p>不同底层支持</p><strong>{research.unique_support_count}</strong><span>禁止同支持换系数</span></article>
      <article className="metric-card accent-cyan"><p>错题/重复库</p><strong>{report.rooms.mistake_count}</strong><span>约简后不晋级</span></article>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">DIVERSITY AUDIT</p><h2>按单项式数量分布</h2></div><span className="status-chip good">NO PARAMETER PADDING</span></div>
      <div className="metric-grid room-metrics">
        {byTerms.map((item) => <div className="metric-card" key={item.termCount}><p>{item.termCount} 项结构</p><strong>{item.count}</strong><span>不同支持集合</span></div>)}
      </div>
      <div className="boundary-box"><p>新颖性口径</p><span>“新”只表示此前不在当前模型的验证运算房间；不表示人类未知，也不表示500个新数学基础。</span></div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">VERIFIED OPERATORS</p><h2>全部500条成功记录</h2></div><span className="status-chip good">整数域通用证明</span></div>
      <div className="operator-discovery-grid">
        {research.operators.map((item) => <article className="metric-card" key={item.operator_id}>
          <p><code>#{item.discovery_rank} · {item.operator_id}</code></p>
          <strong className="operator-name">{item.posthoc_formula}</strong>
          <span>节点 {item.token_cost} · 单项式 {item.normal_form.length}</span>
          <small>{item.verification.declared_domain}</small>
        </article>)}
      </div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">HONEST SCOPE</p><h2>500条是派生运算，不是基础数学数量</h2></div></div>
      <ul>{research.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      <p className="digest-line">内容摘要 <code>{research.content_digest}</code></p>
    </section>
  </main>;
}
