import reportData from "../../data/strict_fold_foundation_v12_latest.json";

const report = reportData;
const selected = report.discovery.selected;
const proof = report.proof;
const profile = selected.iteration_profile;

const checks = [
  ["同时依赖底数和次数", profile.depends_on_base_and_count],
  ["零次返回单位元", profile.zero_count_returns_prior_identity],
  ["后继只调用一次已学语义", profile.successor_is_one_prior_semantic_application],
  ["次数组合保持同态", profile.count_composition_is_homomorphic],
  ["单位底数保持不变", profile.prior_identity_base_is_fixed],
  ["底数组合保持同态", profile.base_composition_is_homomorphic],
] as const;

export default function FoundationV12Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">STRICT FOLD DISCOVERY V12</p><p className="brand-name">AKGM-N0 / 迭代组合基础</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v13">全部域扩张</a><a className="nav-link" href="/foundation-v11">商余基础</a><a className="nav-link" href="/foundation-v10">乘法基础</a><a className="nav-link" href="/meta-autonomy">自主探索</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">1个迭代基础通过</span><span className="scope-label">OPAQUE SEMANTIC FOLD</span></div><h1>没有提供幂目标，程序学会了重复组合</h1><p className="lede">候选只选择循环输入、初始状态、已验证黑盒语义的两个参数来源和输出位置。系统没有获得幂或指数操作码；行为通过迭代同态检测和全称归纳之后，才命名为自然数幂。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{selected.candidate_id}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>3</strong><span>V10–V12严格基础</span></div><p>{proof.derived_normal_form}</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>生成程序</p><strong>{report.discovery.programs_generated}</strong><span>匿名折叠控制器</span></article>
      <article className="metric-card accent-violet"><p>不同行为</p><strong>{report.discovery.behavior_classes}</strong><span>执行后去重</span></article>
      <article className="metric-card accent-amber"><p>有序通过行为</p><strong>{report.discovery.promotable_behavior_classes}</strong><span>输入交换后等价</span></article>
      <article className="metric-card accent-cyan"><p>结构轨道</p><strong>{report.discovery.promotable_semantic_orbits_under_input_renaming}</strong><span>实际提升的新基础</span></article>
      <article className="metric-card accent-slate"><p>全称证明</p><strong>{proof.obligations.filter(item => item.passed).length}/{proof.obligations.length}</strong><span>归纳、终止与同态</span></article>
    </section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">SELECTED FOLD</p><h2>发现的程序结构</h2></div><span className="status-chip good">PROVEN</span></div><pre className="code-block operation-code">{JSON.stringify(selected.program, null, 2)}</pre><div className="posthoc-note"><span>证明后命名</span><strong>{proof.posthoc_name}</strong><small>{proof.universal_statement}</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">ITERATION LAWS</p><h2>六项性质全部成立</h2></div></div><div className="evidence-list">{checks.map(([label, passed]) => <div className="evidence-row" key={label}><div><strong>{label}</strong><span>通用折叠行为检测</span></div><b>{passed ? "PASS" : "FAIL"}</b></div>)}</div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">INDUCTIVE PROOF</p><h2>对所有 b,n∈N成立</h2></div><span className="status-chip good">13/13</span></div><div className="operator-discovery-grid">{proof.obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>{item.evidence}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>准确分类</h2></div></div><ul><li>没有目标输出、幂公式、幂或指数操作码。</li><li>V10语义以不透明且已证明的二元黑盒形式提供给候选。</li><li>折叠语法、候选枚举、同态检测器和归纳证明器仍由主机提供。</li><li>两个有序通过行为只是输入角色互换，只计为一个结构基础。</li><li>属于受限语法内的目标无关结构发现，不声称人类未知数学。</li></ul><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
