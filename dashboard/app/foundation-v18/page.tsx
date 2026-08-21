import reportData from "../../data/goal_driven_planner_v18_latest.json";

const report = reportData;
const acceptance = report.acceptance;
const aggregate = acceptance.aggregate;
const sampleProblems = acceptance.runs[0].problems.slice(0, 8);
const reduction = (aggregate.token_reduction * 100).toFixed(2);
const stateText = (state: number[]) => `(${state.join(", ")})`;

export default function FoundationV18Page() {
  return <main>
    <header className="masthead"><div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">GOAL-DRIVEN PLANNER V18</p><p className="brand-name">AKGM-N0 / 自创工具驱动解题</p></div></div><div className="run-meta"><a className="nav-link" href="/foundation-v19">数学发现</a><a className="nav-link" href="/foundation-v17">自主研究</a><a className="nav-link" href="/foundation-v16">冷启动语义</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div></header>

    <section className="hero panel-grid operation-hero"><div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">V18 验收 12/12</span><span className="scope-label">UNSEEN GOAL / UNIFORM-COST PLAN / INDEPENDENT REPLAY</span></div><h1>自主发现的运算现在能够被规划器组合起来解题</h1><p className="lede">每道题只给初始状态、目标状态和计数边界，不提供解法程序。规划器在八种原语与自主安装语义组成的状态图中寻找最短运行时程序；每一步都由独立验证器重新执行。</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code><code>{acceptance.classification}</code></div></div><div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>108/108</strong><span>解出并验证</span></div><p>计划 token 降低 {reduction}%</p></div></section>

    <section className="metric-grid meta-score-grid">
      <article className="metric-card accent-cyan"><p>未见目标问题</p><strong>{aggregate.problem_count}</strong><span>三套独立研究库</span></article>
      <article className="metric-card accent-violet"><p>调用自创语义</p><strong>{aggregate.dynamic_use_problem_count}/108</strong><span>不是只用旧原语求解</span></article>
      <article className="metric-card accent-amber"><p>计划变短</p><strong>{aggregate.improved_problem_count}/108</strong><span>相对原语最短基线</span></article>
      <article className="metric-card accent-cyan"><p>运行时 token</p><strong>{aggregate.learned_tokens}</strong><span>原语基线 {aggregate.baseline_tokens}</span></article>
      <article className="metric-card accent-slate"><p>错误计划拦截</p><strong>{aggregate.wrong_plans_rejected}/3</strong><span>截断计划进入错题库</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PLANNING PIPELINE</p><h2>从目标到可重放程序</h2></div><span className="status-chip good">NO SOLUTION WITNESS</span></div><div className="operator-discovery-grid"><article className="metric-card"><p>01 / INPUT</p><strong className="operator-name">初始状态 + 目标状态 + 边界</strong><span>题目中没有隐藏程序</span></article><article className="metric-card"><p>02 / ACTIONS</p><strong className="operator-name">八原语 + V17 自创指令</strong><span>所有动作均可执行</span></article><article className="metric-card"><p>03 / SEARCH</p><strong className="operator-name">一致代价状态图规划</strong><span>最小化运行时指令数量</span></article><article className="metric-card"><p>04 / REPLAY</p><strong className="operator-name">逐步重放状态变化</strong><span>任何不连续立即形成反例</span></article></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">SAMPLE SOLUTIONS</p><h2>真实生成的目标与程序</h2></div></div><div className="operator-discovery-grid">{sampleProblems.map(item => <article className="metric-card" key={item.problem.problem_id}><p><code>{item.problem.problem_id}</code></p><strong className="operator-name">{stateText(item.problem.initial_state)} → {stateText(item.problem.goal_state)}</strong><span>baseline {item.baseline.runtime_token_cost} · learned {item.learned.runtime_token_cost} · dynamic {item.learned.dynamic_operator_uses}</span><small>{item.learned.steps.map(step => `${step.instruction.op}⟨${(step.instruction.operands || []).join(",")}⟩`).join(" → ")}</small></article>)}</div></section>

    <section className="content-grid operation-grid"><article className="surface comparison-card"><div className="section-heading"><div><p className="eyebrow">THREE INDEPENDENT LIBRARIES</p><h2>不是依赖单次偶然词表</h2></div><span className="status-chip good">ALL PASS</span></div><div className="evidence-list">{acceptance.runs.map(run => <div className="evidence-row" key={run.research_seed_commitment}><div><strong>LIBRARY {run.run_index + 1}</strong><span>{run.research_operator_count} operators · {run.verified_count}/{run.problem_count} verified · {run.dynamic_use_problem_count} dynamic</span></div><b>{(run.token_reduction * 100).toFixed(2)}% ↓</b></div>)}</div></article><article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">COST EVIDENCE</p><h2>自创工具确实提高解题效率</h2></div></div><div className="receipt-list"><div><dt>primitive-only tokens</dt><dd>{aggregate.baseline_tokens}</dd></div><div><dt>learned-library tokens</dt><dd>{aggregate.learned_tokens}</dd></div><div><dt>saved tokens</dt><dd>{aggregate.baseline_tokens - aggregate.learned_tokens}</dd></div><div><dt>reduction</dt><dd>{reduction}%</dd></div></div><div className="posthoc-note"><span>比较口径</span><strong>同一批题、同一状态边界、同一个一致代价规划器</strong><small>唯一差别是是否允许使用自主发现的运行时语义。</small></div></article></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">STRICT OBLIGATIONS</p><h2>十二项解题验收</h2></div></div><div className="operator-discovery-grid">{acceptance.proof_obligations.map(item => <article className="metric-card" key={item.obligation_id}><p><code>{item.obligation_id}</code></p><strong className="operator-name">{item.passed ? "通过" : "失败"}</strong><span>独立证据</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>已经能解状态目标题，尚不是自然语言数学模型</h2></div></div><ul>{acceptance.limitations.map(item => <li key={item}>{item}</li>)}</ul><div className="boundary-box"><p>准确成果</p><code>{report.claim.achieved}</code><span>未声称：{report.claim.not_claimed}</span></div><p className="digest-line">内容摘要 <code>{report.content_digest}</code></p></section>
  </main>;
}
