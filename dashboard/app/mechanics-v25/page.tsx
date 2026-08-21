import reportData from "../../data/collision_mechanics_discovery_v25_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const discovery = acceptance.discovery;
const passed = acceptance.proof_obligations.filter(item => item.passed).length;

export default function MechanicsV25Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">COLLISION MECHANICS V25</p><p className="brand-name">AKGM-N0 / 双实体碰撞与双守恒力学</p></div></div><div className="run-meta"><a className="nav-link" href="/mechanics-v26">旋转力学 V26</a><a className="nav-link" href="/physics-v24">惯性响应</a><a className="nav-link" href="/physics-worlds-v23">自主世界</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V25 验收 {passed}/12</span><span className="scope-label">COLLIDE → SEARCH → CONSERVE → FALSIFY → PROVE</span></div><h1>系统构造了双实体碰撞程序，并发现第二种守恒量</h1><p className="lede">学习器获得的只是四个匿名三计数器通道及碰撞前后状态。它没有得到质量、速度、动量、能量或弹性碰撞公式。两个输出通道各自从 1280 个程序中唯一选出；同时，V24 的线性加权守恒继续成立，并新增唯一的二次加权守恒。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{passed}/12</strong><span>严格义务</span></div><p>{acceptance.proofs.collision_programs.hidden_replay.length}/4 密封碰撞通过</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>每个输出候选</p><strong>{discovery.candidates_per_output}</strong><span>可执行路由程序</span></article>
      <article className="metric-card accent-violet"><p>碰撞程序</p><strong>{discovery.selected_programs.length}</strong><span>两个实体各一个</span></article>
      <article className="metric-card accent-amber"><p>二次候选</p><strong>{discovery.quadratic_invariant_candidates}</strong><span>只有一个守恒</span></article>
      <article className="metric-card accent-cyan"><p>训练碰撞</p><strong>{discovery.collision_training_cases}</strong><span>参数不等、含分数与反向</span></article>
      <article className="metric-card accent-slate"><p>错误碰撞</p><strong>{acceptance.mutation_audits.length}</strong><span>全部反例拒绝</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CONSTRUCTED PROGRAMS</p><h2>唯一通过的两个碰撞输出</h2></div><span className="status-chip good">2 / 2560 SELECTED</span></div><div className="operator-discovery-grid">{discovery.selected_programs.map(item => <article className="metric-card" key={item.program_id}><p>OUTPUT q{item.output_channel}</p><strong className="operator-name"><code>{item.opaque_program}</code></strong><span>{item.training_cases} 个匿名碰撞一致</span><small>{item.program_id}</small></article>)}</div><div className="posthoc-note"><span>证明后翻译</span><strong>一维完全弹性双体碰撞更新</strong><small>碰撞公式没有作为学习器输入；它只在有限四原子路由语法中搜索。</small></div></section>

    <section className="content-grid operation-grid"><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">LINEAR INVARIANT</p><h2>P_L · 线性加权总量</h2></div><span className="status-chip good">INHERITED</span></div><div className="posthoc-note"><span>匿名程序</span><strong><code>{discovery.inherited_linear_invariant.opaque_program}</code></strong></div><div className="posthoc-note"><span>物理翻译</span><strong>m₁v₁ + m₂v₂</strong><small>总动量式量。</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">QUADRATIC INVARIANT</p><h2>E_Q · 二次加权总量</h2></div><span className="status-chip good">NEW</span></div><div className="posthoc-note"><span>匿名程序</span><strong><code>{discovery.selected_quadratic_invariant.opaque_program}</code></strong></div><div className="posthoc-note"><span>物理翻译</span><strong>m₁v₁² + m₂v₂²</strong><small>等于传统总动能的两倍；仅凭守恒无法识别常规的 1/2 系数。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MECHANICS LOOP</p><h2>当前已经形成的力学闭环</h2></div></div><div className="operator-discovery-grid"><article className="metric-card"><p>01</p><strong className="operator-name">惯性参数 m</strong><span>实体对作用的响应尺度</span></article><article className="metric-card"><p>02</p><strong className="operator-name">响应 F = κma</strong><span>V24 匿名响应程序</span></article><article className="metric-card"><p>03</p><strong className="operator-name">内部交换</strong><span>相反作用保持线性加权总量</span></article><article className="metric-card"><p>04</p><strong className="operator-name">碰撞程序</strong><span>直接构造两个碰撞后状态</span></article><article className="metric-card"><p>05</p><strong className="operator-name">双守恒筛选</strong><span>P_L 与 E_Q 同时保持</span></article><article className="metric-card"><p>06</p><strong className="operator-name">碰撞类别区分</strong><span>粘连碰撞保持 P_L、破坏 E_Q</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MUTATION AUDIT</p><h2>四种错误力学已进入错题库</h2></div></div><div className="operator-discovery-grid">{acceptance.mutation_audits.map(item => <article className="metric-card" key={item.mutation}><p><code>{item.mutation}</code></p><strong className="operator-name">{item.rejected ? "已拒绝" : "未拒绝"}</strong><span>密封反例</span><small>{item.counterexample?.experiment_id}</small></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立证据</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>力学已扩展，但没有夸大</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
