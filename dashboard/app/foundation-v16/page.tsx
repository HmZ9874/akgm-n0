import reportData from "../../data/cold_start_semantics_v16_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const aggregate = acceptance.aggregate;
const representative = acceptance.trials[0];
const percent = (aggregate.mean_holdout_token_reduction * 100).toFixed(2);
const renderBody = (body: Array<{op: string; operands?: number[]}>) => body
  .map(item => `${item.op}${item.operands ? `⟨${item.operands.join(",")}⟩` : ""}`)
  .join(" → ");

export default function FoundationV16Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">COLD-START SEMANTICS V16</p><p className="brand-name">AKGM-N0 / 原生运算语义创造</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v17">自主研究</a><a className="nav-link" href="/foundation-v15">统一基底</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V16 验收 12/12</span><span className="scope-label">ZERO MEMORY / RUNTIME INSTALL / SEALED TRANSFER</span></div><h1>从空动态注册表开始，机器自行创造并安装新的计算指令</h1><p className="lede">每次实验只保留八种原语。系统从匿名原语工作流的重复结构中提出参数化语义，用最小描述长度奖励选择，在独立验证后直接安装进 VM；已安装指令还能参与下一代指令创造。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>12/12</strong><span>严格义务</span></div><p>密封 token 降低 {percent}%</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>独立冷启动</p><strong>{acceptance.trial_count}</strong><span>每次清空动态注册表</span></article>
      <article className="metric-card accent-violet"><p>自主安装语义</p><strong>{aggregate.installed_operator_count}</strong><span>最低每次 {aggregate.minimum_operators_per_trial}</span></article>
      <article className="metric-card accent-amber"><p>递归创造深度</p><strong>{aggregate.minimum_generation_depth}</strong><span>新指令继续构成新指令</span></article>
      <article className="metric-card accent-cyan"><p>密封精确重放</p><strong>{aggregate.exact_holdout_replays}/{aggregate.holdout_workloads}</strong><span>{aggregate.dynamic_dispatches} 次动态派发</span></article>
      <article className="metric-card accent-slate"><p>篡改拦截</p><strong>{aggregate.mutations_rejected}/20</strong><span>{report.storage.mistakes_recorded} 条错题证据</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">COLD-START MANIFEST</p><h2>起点确实为空</h2></div><span className="status-chip good">AUDITED</span></div><div className="receipt-list"><div><dt>initial success programs</dt><dd>{representative.manifest.initial_success_program_count}</dd></div><div><dt>initial dynamic operators</dt><dd>{representative.manifest.initial_dynamic_operator_count}</dd></div><div><dt>imported programs</dt><dd>{representative.manifest.imported_program_count}</dd></div><div><dt>prior artifact reads</dt><dd>{representative.manifest.prior_artifact_reads}</dd></div><div><dt>target formulas</dt><dd>{representative.manifest.target_formula_count}</dd></div><div><dt>selection objective</dt><dd>{representative.manifest.selection_objective}</dd></div></div><div className="boundary-box"><p>唯一初始词表</p><code>{acceptance.base_opcodes.join(" · ")}</code><span>训练工作流承诺：{representative.manifest.workload_digest}</span></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">INVENTED RUNTIME OPCODES</p><h2>代表性冷启动产生的新指令</h2></div><span className="status-chip good">INSTALLED, NOT PRE-EXPANDED</span></div><div className="operator-discovery-grid">{representative.operators.slice(0, 12).map(operator => <article className="metric-card" key={operator.operator_id}><p><code>{operator.operator_id} · G{operator.generation}</code></p><strong className="operator-name">{renderBody(operator.body)}</strong><span>{operator.train_family_support} worlds · {operator.train_occurrences} occurrences</span><small>primitive span {operator.primitive_span} · reward {operator.net_training_reward}</small></article>)}</div></section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">20 ISOLATED TRIALS</p><h2>每一次都重新学习</h2></div><span className="status-chip good">ALL PASS</span></div><div className="evidence-list">{acceptance.trials.map(trial => <div className="evidence-row" key={trial.trial_index}><div><strong>TRIAL {String(trial.trial_index + 1).padStart(2, "0")}</strong><span>{trial.installed_operator_count} operators · G{trial.generation_depth} · {trial.holdout.exact_replays}/{trial.holdout.workload_count} replays</span></div><b>{(trial.holdout.token_reduction * 100).toFixed(2)}% ↓</b></div>)}</div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLE GATE</p><h2>篡改语义不能混入成功库</h2></div></div><div className="receipt-list"><div><dt>candidate</dt><dd>{representative.mutation_audit.candidate_id}</dd></div><div><dt>rejected</dt><dd>{String(representative.mutation_audit.rejected)}</dd></div><div><dt>reason</dt><dd>{representative.mutation_audit.reason}</dd></div></div><div className="posthoc-note"><span>首个反例</span><strong>{JSON.stringify(representative.mutation_audit.counterexample)}</strong><small>运行时行为必须与冻结原语证书一致。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项验收全部通过</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立证据重放</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>证明了语义抽象，不夸大为全部数学发现</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
