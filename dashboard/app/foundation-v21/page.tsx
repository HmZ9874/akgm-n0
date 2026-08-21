import reportData from "../../data/directed_rational_construction_v21_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const construction = acceptance.construction;
const proofs = acceptance.proofs;
const passed = acceptance.proof_obligations.filter(item => item.passed).length;
const triple = (value: { positive: number; negative: number; denominator: number }) => `(${value.positive}, ${value.negative}; ${value.denominator})`;

export default function FoundationV21Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">DIRECTED RATIONAL CONSTRUCTION V21</p><p className="brand-name">AKGM-N0 / 用自然计数器创造负方向</p></div></div><div className="run-meta"><a className="nav-link" href="/physics-v22">物理 V22</a><a className="nav-link" href="/foundation-v20">程序构造</a><a className="nav-link" href="/foundation-v19">数学发现</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V21 验收 {passed}/12</span><span className="scope-label">NATURAL COUNTERS → DIRECTION → INVERSE → RING</span></div><h1>系统没有接收负数，却构造出了负方向和有理数环</h1><p className="lede">每个值始终只是三个非负计数器：正向通道、反向通道、正分母。学习器枚举方向路由，独立证明器再验证表示无关性、加法逆元、结合律、交换律与分配律。人类的正负号只在证明完成后用于翻译。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>3/34</strong><span>程序提升</span></div><p>9 个单路由变异全部拒绝</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>候选方向策略</p><strong>{construction.policies_generated}</strong><span>16 合并 + 2 一元 + 16 交互</span></article>
      <article className="metric-card accent-violet"><p>提升程序</p><strong>3</strong><span>合并、相反量、交互</span></article>
      <article className="metric-card accent-amber"><p>全域证明</p><strong>4</strong><span>等价、群、环、方程</span></article>
      <article className="metric-card accent-cyan"><p>错误变异</p><strong>{acceptance.mutation_audits.length}</strong><span>全部有具体反例</span></article>
      <article className="metric-card accent-slate"><p>宿主负数输入</p><strong>0</strong><span>学习器值始终非负</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">REPRESENTATION</p><h2>负方向不是一个预装符号</h2></div><span className="status-chip good">THREE COUNTERS ONLY</span></div><div className="operator-discovery-grid"><article className="metric-card"><p>VALUE</p><strong className="operator-name">(P, N; D)</strong><span>P、N∈自然数，D&gt;0</span></article><article className="metric-card"><p>EQUIVALENCE</p><strong className="operator-name">MERGE(SEM(P₁,D₂), SEM(N₂,D₁))</strong><span>= MERGE(SEM(P₂,D₁), SEM(N₁,D₂))</span></article><article className="metric-card"><p>HUMAN TRANSLATION</p><strong className="operator-name">(P−N)/D</strong><span>只存在于证明后的汇报层</span></article><article className="metric-card"><p>REDUNDANCY</p><strong className="operator-name">(P+k,N+k;D) 等价</strong><span>公共计数质量自动抵消</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROMOTED ROUTERS</p><h2>唯一通过严格门的三条程序</h2></div></div><div className="operator-discovery-grid"><article className="metric-card"><p><code>{construction.selected_combine.candidate_id}</code></p><strong className="operator-name">mask [{construction.selected_combine.policy.positive_mask.map(value => value ? "P" : "N").join(" · ")}]</strong><span>同类方向分别合并</span><small>证明后翻译：有理数加法</small></article><article className="metric-card"><p><code>UNARY ROUTER</code></p><strong className="operator-name">swap(P,N) = {String(construction.selected_inverse.swap_counters)}</strong><span>两次交换恢复原对象</span><small>证明后翻译：加法逆元 / 负号</small></article><article className="metric-card"><p><code>{construction.selected_interact.candidate_id}</code></p><strong className="operator-name">mask [{construction.selected_interact.policy.positive_mask.map(value => value ? "P" : "N").join(" · ")}]</strong><span>同向交互归正，异向交互归反</span><small>证明后翻译：有理数乘法</small></article></div></section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">EQUATION PROGRAM</p><h2>x ⊕ b = c 的构造解</h2></div><span className="status-chip good">EXISTS + UNIQUE</span></div><div className="evidence-list">{construction.equation_examples.map((item, index) => <div className="evidence-row" key={index}><div><strong>x ⊕ {triple(item.bias)} = {triple(item.target)}</strong><span>replay {triple(item.replay)}</span></div><b>x = {triple(item.solution)}</b></div>)}</div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">PROOF STATUS</p><h2>形成了什么结构</h2></div></div><div className="receipt-list"><div><dt>有向等价关系</dt><dd>{proofs.equivalence.passed ? "通过" : "失败"}</dd></div><div><dt>交换加法群</dt><dd>{proofs.additive_group.passed ? "通过" : "失败"}</dd></div><div><dt>交换环</dt><dd>{proofs.commutative_ring.passed ? "通过" : "失败"}</dd></div><div><dt>平移方程唯一解</dt><dd>{proofs.translation_equation.passed ? "通过" : "失败"}</dd></div></div><div className="posthoc-note"><span>数学层级变化</span><strong>从非负有理运算进入带加法逆元的有理代数结构</strong><small>尚未构造非零元素的乘法逆元程序。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MUTATION AUDIT</p><h2>任意单路由翻转都会留下反例</h2></div></div><div className="operator-discovery-grid">{acceptance.mutation_audits.map((item, index) => <article className="metric-card" key={`${item.mutated_program}-${index}`}><p><code>{item.mutated_program}</code></p><strong className="operator-name">{item.rejected ? "已拒绝" : "未拒绝"}</strong><span>来源 {item.source_program}</span><small>{item.counterexample ? "counterexample recorded" : "missing counterexample"}</small></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项 V21 验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立证据</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>已经形成交换环，尚未形成完整域</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
