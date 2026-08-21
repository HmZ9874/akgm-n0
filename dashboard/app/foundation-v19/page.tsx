import reportData from "../../data/autonomous_math_discovery_v19_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const discovery = acceptance.discovery;
const concept = acceptance.induced_concept;
const obligationsPassed = acceptance.proof_obligations.filter(item => item.passed).length;
const sampleTheorems = acceptance.theorem_proofs.slice(0, 18);
const sampleErrors = acceptance.rejected_conjectures.slice(0, 8);

export default function FoundationV19Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">AUTONOMOUS MATHEMATICS V19</p><p className="brand-name">AKGM-N0 / 猜想—反例—全域证明</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v20">程序构造</a><a className="nav-link" href="/foundation-v18">目标解题</a><a className="nav-link" href="/foundation-v17">自主研究</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V19 验收 {obligationsPassed}/12</span><span className="scope-label">DISCOVER → CONJECTURE → FALSIFY → PROVE → INDUCE</span></div><h1>系统第一次从匿名计算语义走到了可证明的数学结构</h1><p className="lede">学习器只从自然数计数器、0/1、寄存器搬运与循环控制出发；没有收到乘法程序、目标公式、素数定义或数列下一项。它先选择匿名二元语义，再生成等式候选；独立验证器把成立的式子证明到所有自然数，把错误式子的具体反例写入错题库。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{acceptance.theorem_proofs.length}/80</strong><span>全域证明</span></div><p>{acceptance.rejected_conjectures.length} 条错误式已拦截</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>匿名程序搜索</p><strong>{discovery.programs_generated}</strong><span>{discovery.behavior_classes} 个不同语义类</span></article>
      <article className="metric-card accent-violet"><p>自主生成表达式</p><strong>{discovery.expressions_enumerated}</strong><span>变量、0、1 与 SEM 组合</span></article>
      <article className="metric-card accent-amber"><p>普遍成立公式</p><strong>{acceptance.theorem_proofs.length}</strong><span>不是有限样本拟合</span></article>
      <article className="metric-card accent-cyan"><p>反例淘汰</p><strong>{acceptance.rejected_conjectures.length}</strong><span>全部进入错题库</span></article>
      <article className="metric-card accent-slate"><p>新概念外推</p><strong>{concept.generated_no_internal_witness.length}</strong><span>1–40 中不可内部合成</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">AUTONOMOUS RESEARCH CHAIN</p><h2>这次巨大进步发生在哪里</h2></div><span className="status-chip good">NO NAMED MATH TARGET</span></div><div className="operator-discovery-grid"><article className="metric-card"><p>01 / CREATE</p><strong className="operator-name">枚举 4,608 个计数程序</strong><span>输入中没有“乘法”目标或答案</span></article><article className="metric-card"><p>02 / CONJECTURE</p><strong className="operator-name">组合 280 个匿名表达式</strong><span>按行为重合自动提出恒等式</span></article><article className="metric-card"><p>03 / ATTACK</p><strong className="operator-name">主动构造相近错误式</strong><span>发现一个反例即拒绝</span></article><article className="metric-card"><p>04 / PROVE</p><strong className="operator-name">归纳不变量 + 符号正规化</strong><span>把有限观察升级为全域定理</span></article><article className="metric-card"><p>05 / CONCEPT</p><strong className="operator-name">按内部合成见证重新分类数字</strong><span>不是预测下一个数</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROVEN FORMULA ROOM</p><h2>成功公式房间（匿名语言）</h2></div><span className="status-chip good">EXACT NORMAL FORM</span></div><div className="operator-discovery-grid">{sampleTheorems.map(item => <article className="metric-card" key={item.theorem_id}><p><code>{item.theorem_id}</code></p><strong className="operator-name">{item.opaque_statement}</strong><span>正规式：{item.left_normal_form}</span><small>{item.proof_method}</small></article>)}</div></section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">INDUCED NUMBER CONCEPT</p><h2>对 1, 3, 5, 7, 11, 13, 17 的新解释</h2></div><span className="status-chip good">STRUCTURAL, NOT SEQUENTIAL</span></div><div className="evidence-list"><div className="evidence-row"><div><strong>边界</strong><span>不进入两种因子类别</span></div><b>{concept.source_partition.boundary.join(", ")}</b></div><div className="evidence-row"><div><strong>存在内部合成见证</strong><span>可由两个更小且大于 1 的数经 SEM 合成</span></div><b>{concept.source_partition.has_internal_witness.join(", ") || "无"}</b></div><div className="evidence-row"><div><strong>没有内部合成见证</strong><span>系统由可执行定义判定</span></div><b>{concept.source_partition.no_internal_witness.join(", ")}</b></div></div><div className="posthoc-note"><span>证明后的人类解释</span><strong>SEM 等价于自然数乘法；“无内部见证”等价于素数</strong><small>这些名称只写进汇报，未传给学习器。</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">TRANSFER</p><h2>系统自行生成的新实例</h2></div></div><div className="receipt-list"><div><dt>扫描域</dt><dd>1–40</dd></div><div><dt>无内部见证</dt><dd>{concept.generated_no_internal_witness.join(", ")}</dd></div><div><dt>输入之外的新值</dt><dd>2, 19, 23, 29, 31, 37</dd></div><div><dt>下一项预测</dt><dd>未使用</dd></div></div><div className="posthoc-note"><span>可证明闭包</span><strong>任意 a,b&gt;1，SEM&lt;a,b&gt; 必有见证 (a,b)</strong><small>这是一条量化定理，不是枚举到 40 的经验规律。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MISTAKE ROOM</p><h2>错误公式不会被“奖励后保留”</h2></div></div><div className="operator-discovery-grid">{sampleErrors.map(item => <article className="metric-card" key={item.conjecture_id}><p><code>{item.conjecture_id}</code></p><strong className="operator-name">{item.opaque_statement}</strong><span>反例：{Object.entries(item.counterexample.environment).map(([key, value]) => `${key}=${value}`).join(", ")}</span><small>左={item.counterexample.left} · 右={item.counterexample.right}</small></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项数学发现验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>可独立重放</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>是真正的定理发现进步，但还不是现代数学家</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
