import Link from "next/link";
import report from "../../data/open_set_representation_v50_latest.json";


const acceptance = report.acceptance;
const discovery = acceptance.representation_discovery;
const selected = discovery.selected;
const sealed = acceptance.sealed_transfer;
const human = acceptance.posthoc_translation.human_equivalent;
const campaign = acceptance.long_horizon_research.campaign;


export default function ScienceV50Page() {
  return <main className="report-shell">
    <nav className="report-nav"><Link href="/science-v49">← V49 evidence gap</Link><span>AKGM-N0 · V50</span></nav>

    <section className="hero-panel"><div className="hero-copy">
      <div className="verdict-row"><span className="verdict-badge">VERIFIED · MEANINGFUL REDISCOVERY</span><span className="scope-label">OPEN SET REPRESENTATION · SEALED</span></div>
      <h1>The system stopped predicting the next event and discovered a distributional relation</h1>
      <p className="lede">Starting only from ordered anonymous event values, V50 created threshold sets, counted their members, synthesized non-trivial ASTs over adjacent levels, and froze the best relation before sealed groups were revealed. Human seismology names were introduced only after verification.</p>
      <div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div>
    </div></section>

    <section className="metrics-grid">
      <article className="metric-card"><span>NEW SEMANTIC</span><strong>1</strong><small>{discovery.semantic_id}</small></article>
      <article className="metric-card"><span>CONSTANT</span><strong>{selected.constant.toFixed(6)}</strong><small>no sealed refit</small></article>
      <article className="metric-card"><span>VALIDATION ERROR</span><strong>{(selected.validation.prediction_rmse_ratio * 100).toFixed(2)}%</strong><small>of identity baseline</small></article>
      <article className="metric-card"><span>SEALED ERROR</span><strong>{(sealed.prediction_rmse_ratio * 100).toFixed(2)}%</strong><small>of identity baseline</small></article>
    </section>

    <section className="concept-grid">
      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">INTERNAL DISCOVERY</p><h2>{discovery.semantic_id}</h2></div></div>
        <div className="boundary-box"><p>Synthesized AST</p><code>SAFE_DIV(B, A)</code><span>A and B are adjacent empirical survival counts. The AST depends on both inputs, changes under counterfactual edits, and is not an identity.</span></div>
        <div className="boundary-box"><p>Internal relation</p><code>B / A ≈ {selected.constant.toFixed(12)}</code><span>Threshold step Δ={acceptance.anonymous_set_world.grid.step.toFixed(3)} was inferred from training values.</span></div>
      </article>

      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">POST-HOC TRANSLATION</p><h2>{human.known_human_family}</h2></div></div>
        <div className="boundary-box"><p>Human-readable formula</p><code>N(M ≥ m + 0.1) / N(M ≥ m) ≈ {selected.constant.toFixed(6)}</code><span>Iteration gives N(M ≥ m+nΔ) ≈ N(M ≥ m)·Kⁿ.</span></div>
        <div className="boundary-box"><p>Equivalent log-linear slope</p><code>log₁₀N = a − {human.estimated_b.toFixed(6)}M</code><span>This is a rediscovery of a known relation, not a human-unknown law.</span></div>
      </article>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">SEALED EVIDENCE</p><h2>The relation transferred without fitting its constant again</h2></div></div>
      <div className="timeline-list">
        <div className="posthoc-note"><strong>Candidate ASTs evaluated</strong><small>{discovery.evaluated_candidate_count} non-trivial relations from generic arithmetic</small></div>
        <div className="posthoc-note"><strong>Sealed constant drift</strong><small>{(sealed.constant_relative_shift * 100).toFixed(3)}%</small></div>
        <div className="posthoc-note"><strong>Sealed pairs</strong><small>{sealed.pair_count} adjacent threshold comparisons across {acceptance.anonymous_set_world.sealed_group_count} groups</small></div>
        <div className="posthoc-note"><strong>Residual memory</strong><small>{sealed.counterexamples.length} largest deviations retained for mandatory replay</small></div>
      </div>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">AUTONOMOUS CONTINUATION</p><h2>{campaign.next_selected_task.replaceAll("_", " ")}</h2></div></div>
      <div className="boundary-box"><p>Campaign cycle {campaign.cycle_index}</p><code>{campaign.checkpoint_digest}</code><span>The next valid step is a genuinely independent event catalog, not more fitting on the same archive.</span></div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>Meaningful rediscovery is not human novelty or causation</h2></div></div>
      <div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>The substrate still supplies ordering, comparison, counting, arithmetic, and an AST budget. Independent-catalog replication remains required.</span></div>
    </section>
  </main>;
}
