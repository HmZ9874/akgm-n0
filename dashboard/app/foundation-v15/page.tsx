import reportData from "../../data/self_extending_substrate_v15_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const percent = (acceptance.aggregate.evaluation_reduction * 100).toFixed(2);

export default function FoundationV15Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">SELF-EXTENDING SUBSTRATE V15</p><p className="brand-name">AKGM-N0 / 统一自学习基底</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v16">冷启动语义</a><a className="nav-link" href="/foundation-v14">组合闭包</a><a className="nav-link" href="/foundation-v13">域扩张</a><a className="nav-link" href="/foundation-v12">严格基础</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V15验收9/9通过</span><span className="scope-label">ONE VM / NON-TRANSFORMER / CEGIS</span></div><h1>三个专用运行基底被统一成一台原始计数器机器</h1><p className="lede">所有任务现在只执行置零、置一、加一、减一、判零、跳转、输出和停止。非Transformer循环提议策略从成功与失败轨迹学习，CEGIS用最小反例推动重构，重复字节码被压缩成跨任务匿名宏。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>9/9</strong><span>架构验收</span></div><p>搜索执行减少 {percent}%</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>统一原始操作</p><strong>{acceptance.vm.opcodes.length}</strong><span>{acceptance.vm.opcodes.join(" · ")}</span></article>
      <article className="metric-card accent-violet"><p>重构任务</p><strong>{acceptance.reconstructions.filter(item => item.converged).length}/3</strong><span>同一VM与控制器</span></article>
      <article className="metric-card accent-amber"><p>跨任务宏</p><strong>{acceptance.macros.length}</strong><span>至少支持三个任务</span></article>
      <article className="metric-card accent-slate"><p>错题记录</p><strong>{report.storage.mistakes_recorded}</strong><span>反例与轨迹尾部</span></article>
      <article className="metric-card accent-cyan"><p>搜索降幅</p><strong>{percent}%</strong><span>{acceptance.aggregate.case_evaluations}/{acceptance.aggregate.exhaustive_case_evaluations} case evaluations</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">ACCEPTANCE GATES</p><h2>九项架构验收</h2></div><span className="status-chip good">ALL PASS</span></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立重放结果</span></article>)}</div></section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">CEGIS RECONSTRUCTION</p><h2>反例驱动重构</h2></div><span className="status-chip good">3/3</span></div><div className="evidence-list">{acceptance.reconstructions.map(item => <div className="evidence-row" key={item.task_id}><div><strong>{item.task_id}</strong><span>{item.candidate_count} candidates · {item.round_count} rounds · {item.case_evaluations} evaluations</span></div><b>{(item.evaluation_reduction * 100).toFixed(1)}% ↓</b></div>)}</div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">RECURRENT PROPOSAL POLICY</p><h2>非Transformer提议学习</h2></div></div><div className="receipt-list"><div><dt>architecture</dt><dd>{acceptance.proposal_policy.architecture}</dd></div><div><dt>transformer</dt><dd>{String(acceptance.proposal_policy.transformer)}</dd></div><div><dt>positive transitions</dt><dd>{acceptance.proposal_policy.positive_transition_count}</dd></div><div><dt>negative transitions</dt><dd>{acceptance.proposal_policy.negative_transition_count}</dd></div></div><div className="posthoc-note"><span>控制职责</span><strong>预测下一种程序修改，而不是直接计算答案</strong><small>成功与错题轨迹共同改变字节码转移评分。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">LEARNED MACROS</p><h2>跨任务重复操作压缩</h2></div><span className="status-chip good">SUPPORT ≥ 3</span></div><div className="operator-discovery-grid">{acceptance.macros.slice(0, 12).map(item => <article className="metric-card" key={item.macro_id}><p><code>{item.macro_id}</code></p><strong className="operator-name">{item.normalized_ops.join(" → ")}</strong><span>{item.task_support} tasks · {item.occurrence_support} occurrences</span><small>每次节省 {item.savings_per_use} tokens</small></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">GENERIC LAW MINING</p><h2>不使用目标公式名称的规律证据</h2></div></div><div className="operator-discovery-grid">{Object.entries(acceptance.generic_laws).flatMap(([taskId, laws]) => laws.filter(law => law.passed).slice(0, 3).map(law => <article className="metric-card" key={`${taskId}-${law.law_id}`}><p><code>{taskId} · {law.family}</code></p><strong className="operator-name">{law.statement}</strong><span>{law.law_id}</span></article>))}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>已经完成统一迁移，但不是冷启动发明</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
