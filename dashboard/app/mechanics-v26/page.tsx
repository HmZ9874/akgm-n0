import reportData from "../../data/planar_rotation_discovery_v26_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const discovery = acceptance.discovery;
const rotationProof = acceptance.proofs.rotation_balance;
const passed = acceptance.proof_obligations.filter(item => item.passed).length;

export default function MechanicsV26Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">PLANAR ROTATION MECHANICS V26</p><p className="brand-name">AKGM-N0 / 二维定向与旋转守恒</p></div></div><div className="run-meta"><a className="nav-link" href="/mechanics-v27">刚体力学 V27</a><a className="nav-link" href="/mechanics-v25">碰撞力学</a><a className="nav-link" href="/physics-v24">惯性响应</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V26 验收 {passed}/12</span><span className="scope-label">ORIENT → WEIGHT → ACT → CONSERVE → FALSIFY</span></div><h1>力学从一维平移进入二维旋转关系</h1><p className="lede">系统只接收匿名二维计数器状态。它从 81 个双线性路由中找出唯一满足交替性、反对称性和坐标定向约定的运算，再从三个权重结构中找到质量加权旋转量。中心作用保持该量，非中心作用产生完全可计算的变化。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{passed}/12</strong><span>严格义务</span></div><p>{rotationProof.central_hidden_replay.length + rotationProof.general_hidden_replay.length}/6 密封案例通过</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>定向运算候选</p><strong>{discovery.bilinear_candidates_generated}</strong><span>唯一选出一个</span></article>
      <article className="metric-card accent-violet"><p>权重候选</p><strong>{discovery.weight_candidates_generated}</strong><span>唯一选出质量权重</span></article>
      <article className="metric-card accent-amber"><p>中心训练</p><strong>{discovery.central_training_cases}</strong><span>旋转量保持</span></article>
      <article className="metric-card accent-cyan"><p>一般作用训练</p><strong>{discovery.general_training_cases}</strong><span>变化量精确平衡</span></article>
      <article className="metric-card accent-slate"><p>错误结构</p><strong>{acceptance.mutation_audits.length}</strong><span>全部反例拒绝</span></article>
    </section>

    <section className="content-grid operation-grid"><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">NEW OPERATION</p><h2>ORB₂ · 二维定向面积运算</h2></div><span className="status-chip good">UNIQUE</span></div><div className="posthoc-note"><span>匿名程序</span><strong><code>{discovery.selected_bilinear.opaque_program}</code></strong><small>满足 ORB&lt;a,a&gt;=ZERO 与 ORB&lt;a,b&gt;=TURN&lt;ORB&lt;b,a&gt;&gt;。</small></div><div className="posthoc-note"><span>证明后翻译</span><strong>x₁y₂ − x₂y₁</strong><small>二维叉积的标量形式；正方向来自明确的坐标约定，不是自然定律。</small></div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">ROTATION QUANTITY</p><h2>L_R · 质量加权旋转量</h2></div><span className="status-chip good">PROVED</span></div><div className="posthoc-note"><span>匿名程序</span><strong><code>{discovery.selected_rotation_quantity.opaque_program}</code></strong></div><div className="posthoc-note"><span>证明后翻译</span><strong>L = m(xvᵧ − yvₓ)</strong><small>平面角动量。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">DISCOVERED BALANCE</p><h2>一般作用与中心作用被统一起来</h2></div></div><div className="operator-discovery-grid"><article className="metric-card"><p>GENERAL</p><strong className="operator-name">ΔL_R = ORB₂(r,J)</strong><span>非中心作用产生角作用量</span></article><article className="metric-card"><p>CENTRAL</p><strong className="operator-name">J ∥ r</strong><span>ORB₂(r,J)=ZERO</span></article><article className="metric-card"><p>CONSERVATION</p><strong className="operator-name">ΔL_R = ZERO</strong><span>中心作用保持旋转量</span></article></div><div className="posthoc-note"><span>物理翻译</span><strong>ΔL = r × J；中心冲量守恒角动量</strong><small>这是冲量关系，还不是连续时间的力矩微分方程。</small></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MECHANICS STACK</p><h2>当前力学能力链</h2></div></div><div className="operator-discovery-grid"><article className="metric-card"><p>V22</p><strong className="operator-name">离散运动状态</strong><span>位置、变化率、作用率</span></article><article className="metric-card"><p>V23</p><strong className="operator-name">多实体世界</strong><span>内部平衡交换</span></article><article className="metric-card"><p>V24</p><strong className="operator-name">F = κma</strong><span>惯性响应与加权守恒</span></article><article className="metric-card"><p>V25</p><strong className="operator-name">弹性碰撞</strong><span>动量式与能量式双守恒</span></article><article className="metric-card"><p>V26</p><strong className="operator-name">二维旋转</strong><span>角作用与中心守恒</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">MUTATION AUDIT</p><h2>四种错误旋转力学</h2></div></div><div className="operator-discovery-grid">{acceptance.mutation_audits.map(item => <article className="metric-card" key={item.mutation}><p><code>{item.mutation}</code></p><strong className="operator-name">{item.rejected ? "已拒绝" : "未拒绝"}</strong><span>存在具体反例</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立证据</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>二维质点旋转关系，不是完整刚体力学</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
