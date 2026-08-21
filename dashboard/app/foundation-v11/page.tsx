import reportData from "../../data/strict_partition_foundation_v11_latest.json";

const report = reportData;
const selected = report.discovery.selected;
const proof = report.proof;
const profile = selected.conservation_profile;

const checks = [
  ["守恒重构", profile.reconstructs_stream_with_prior_binary_semantic],
  ["残量严格有界", profile.residual_is_strictly_bounded],
  ["零残量对应精确边界", profile.zero_residual_matches_exact_boundary],
  ["第一状态单调", profile.first_state_is_monotone_in_stream],
  ["确定性重放", profile.deterministic_replay],
] as const;

export default function FoundationV11Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">STRICT PARTITION DISCOVERY V11</p><p className="brand-name">AKGM-N0 / 二输出基础探索</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v12">幂的新基础</a><a className="nav-link" href="/foundation-v10">乘法基础</a><a className="nav-link" href="/meta-autonomy">自主探索</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">1个二输出基础通过</span><span className="scope-label">NO DIVISION OPCODE</span></div><h1>没有提供除法目标，程序形成了商余分解</h1><p className="lede">系统只获得单位增减、空事件、条件策略位和六个自然数计数器。候选行为先被执行和去重；只有能够唯一重构原数量并留下严格小于分组单位的残量，才进入全称证明。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{selected.candidate_id}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>2</strong><span>V10–V11严格基础</span></div><p>{proof.derived_normal_form.join(" · ")}</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>生成程序</p><strong>{report.discovery.programs_generated}</strong><span>匿名事件控制策略</span></article>
      <article className="metric-card accent-violet"><p>安全执行</p><strong>{report.discovery.programs_executed}</strong><span>正分组单位域</span></article>
      <article className="metric-card accent-amber"><p>行为类别</p><strong>{report.discovery.behavior_classes}</strong><span>二输出指纹去重</span></article>
      <article className="metric-card accent-cyan"><p>提升行为</p><strong>{report.discovery.promotable_behavior_classes}</strong><span>全部守恒门槛通过</span></article>
      <article className="metric-card accent-slate"><p>全称证明</p><strong>{proof.obligations.filter(item => item.passed).length}/{proof.obligations.length}</strong><span>归纳、终止与唯一性</span></article>
    </section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">EVENT CONTROLLER</p><h2>发现的匿名策略</h2></div><span className="status-chip good">PROVEN</span></div><pre className="code-block operation-code">{JSON.stringify(selected.program, null, 2)}</pre><div className="posthoc-note"><span>证明后命名</span><strong>{proof.posthoc_name}</strong><small>{proof.universal_statement}</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">CONSERVATION GATES</p><h2>五项通用性质</h2></div></div><div className="evidence-list">{checks.map(([label, passed]) => <div className="evidence-row" key={label}><div><strong>{label}</strong><span>独立行为重放</span></div><b>{passed ? "PASS" : "FAIL"}</b></div>)}</div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">UNIVERSAL PROOF</p><h2>对所有 n∈N、d∈N⁺成立</h2></div><span className="status-chip good">UNIQUE</span></div><div className="operator-discovery-grid">{proof.obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>{item.evidence}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>准确分类</h2></div></div><ul><li>未提供商、余数目标输出，也没有除法、取模操作码。</li><li>V10证明的二元语义只在行为产生后用于守恒验证，没有参与候选执行。</li><li>事件控制语法、策略位枚举和不变量证明器仍由主机提供。</li><li>属于受限语法内的目标无关结构发现，不声称是人类未知数学。</li></ul><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
