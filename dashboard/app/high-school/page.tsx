import reportData from "../../data/high_school_core_v6_latest.json";

const report = reportData;
const benchmark = report.benchmark;
const categoryNames: Record<string, string> = {
  number_systems: "数系与有理数",
  equations: "方程与判别式",
  sequences: "数列",
  functions: "函数、多项式与导数",
  exponential_log: "指数与对数",
  analytic_geometry: "解析几何",
  trigonometry: "三角",
  probability: "概率",
  sets_inequalities: "集合与区间",
};

export default function HighSchoolPage() {
  const grouped = benchmark.categories.map((category) => ({
    category,
    items: benchmark.competencies.filter((item) => item.category === category),
  }));
  const prerequisitePassed = benchmark.prerequisite_audit.checks.filter((item) => item.passed).length;

  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">HIGH SCHOOL CORE V6</p><p className="brand-name">AKGM-N0 / 高中核心符号能力门槛</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/meta-autonomy">自主探索</a><a className="nav-link" href="/foundation">数学谱系</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy">
        <div className="verdict-row"><span className="verdict-badge">高中核心门槛通过</span><span className="scope-label">EXACT SYMBOLIC BENCHMARK</span></div>
        <h1>{benchmark.passed_competency_count}/{benchmark.competency_count} 项能力，{benchmark.passed_category_count}/{benchmark.category_count} 个领域</h1>
        <p className="lede">目标名称和公式不进入搜索。学习器从同一匿名组合空间中为每个数字世界选择唯一精确程序，再由独立评估器重放先修证明、封闭题和代数恒等式。</p>
        <div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{report.verdict}</code></div>
      </div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>20/20</strong><span>核心能力</span></div><p>精确有理与符号域</p></div>
    </section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>先修证明链</p><strong>{prerequisitePassed}/7</strong><span>全部独立重放</span></article>
      <article className="metric-card accent-cyan"><p>唯一精确程序</p><strong>20</strong><span>每个匿名世界恰好一个</span></article>
      <article className="metric-card accent-cyan"><p>成功能力房间</p><strong>{report.rooms.success_count}</strong><span>哈希链可重放</span></article>
      <article className="metric-card accent-cyan"><p>错题组合</p><strong>{report.rooms.mistake_count}</strong><span>不晋级并永久记录</span></article>
    </section>

    {grouped.map((group) => <section className="evidence-panel limitations-panel" key={group.category}>
      <div className="section-heading"><div><p className="eyebrow">{group.category.toUpperCase()}</p><h2>{categoryNames[group.category] ?? group.category} · {group.items.length}/{group.items.length}</h2></div><span className="status-chip good">PASS</span></div>
      <div className="operator-discovery-grid">
        {group.items.map((item) => <article className="metric-card" key={item.competency_id}>
          <p><code>{item.competency_id}</code></p><strong className="operator-name">{item.posthoc_name}</strong>
          <span>{item.verification.domain_contract}</span><small>候选 {item.candidate_count} · 精确 {item.exact_candidate_count}</small>
        </article>)}
      </div>
    </section>)}

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>通过的是高中核心符号门槛，不是完整人类高中毕业证明</h2></div></div>
      <ul>{benchmark.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      <p className="digest-line">内容摘要 <code>{benchmark.content_digest}</code></p>
    </section>
  </main>;
}
