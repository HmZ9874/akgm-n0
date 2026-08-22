import Link from "next/link";
import report from "../../data/semantic_transfer_counterexample_v48_latest.json";


const acceptance = report.acceptance;
const frozen = acceptance.frozen_opx_transfer;
const search = acceptance.counterexample_driven_search;
const semantic = acceptance.new_semantic;
const campaign = acceptance.long_horizon_research.campaign;
const worlds = frozen.world_results.map(item => ({
  ...item,
  translation: report.posthoc_world_translation[item.world_id as keyof typeof report.posthoc_world_translation],
  replacement: search.sealed_transfer[item.world_id as keyof typeof search.sealed_transfer],
}));


export default function ScienceV48Page() {
  return <main className="report-shell">
    <nav className="report-nav"><Link href="/science-v47">← V47 literature audit</Link><span>AKGM-N0 · V48</span></nav>

    <section className="hero-panel"><div className="hero-copy">
      <div className="verdict-row"><span className="verdict-badge">VERIFIED · COUNTEREXAMPLE-DRIVEN GROWTH</span><span className="scope-label">3 WORLDS · SEALED TRANSFER</span></div>
      <h1>The next discovery is a boundary: matching arity does not mean matching mechanism</h1>
      <p className="lede">V48 executed the task chosen by V47. The frozen OPX semantic failed every unrelated anonymous world. A replacement temporal program succeeded on two worlds but failed the third, so it was not promoted as universal. The failure created a new executable scope-and-abstention semantic.</p>
      <div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div>
    </div></section>

    <section className="metrics-grid">
      <article className="metric-card"><span>OPX TRANSFER</span><strong>0 / 3</strong><small>worlds beat baseline</small></article>
      <article className="metric-card"><span>REPLACEMENT</span><strong>2 / 3</strong><small>bounded success only</small></article>
      <article className="metric-card"><span>MISTAKE ROOM</span><strong>15</strong><small>sealed counterexamples</small></article>
      <article className="metric-card"><span>NEW SEMANTIC</span><strong>1</strong><small>scope control verified</small></article>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">NEW VERIFIED SEMANTIC</p><h2>{semantic.semantic_id}</h2></div></div>
      <div className="boundary-box"><p>{semantic.operation}</p><code>execute when mechanism signature matches; otherwise abstain + search locally</code><span>{semantic.meaning}</span></div>
      <div className="timeline-list">
        <div className="posthoc-note"><strong>Registered intervention apparatus</strong><small>decision={semantic.source_decision} · frozen sealed RMSE {acceptance.source_domain_replay.sealed_rmse.toExponential(3)}</small></div>
        <div className="posthoc-note"><strong>Observational temporal worlds</strong><small>decision={semantic.cross_domain_decision} · false accepts={semantic.false_cross_domain_accept_count}</small></div>
      </div>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">BEST REPLACEMENT CANDIDATE</p><h2>{search.candidate_program_id}</h2></div></div>
      <div className="boundary-box"><p>Internal program</p><code>0.927335736393·PREV − 0.446960122953·DELTA</code><span>Post-hoc: z(t) ≈ 0.9273 z(t−1) − 0.4470 [z(t−1)−z(t−2)]</span></div>
      <div className="boundary-box"><p>Promotion verdict</p><code>universal_formula_accepted={String(search.universal_formula_accepted)}</code><span>It remains a bounded candidate because the event-sequence world failed its sealed baseline gate.</span></div>
    </section>

    <section className="concept-grid">
      {worlds.map(world => <article className="surface concept-card" key={world.world_id}>
        <div className="section-heading"><div><p className="eyebrow">{world.world_id}</p><h2>{world.translation.domain}</h2></div></div>
        <div className="timeline-list">
          <div className="posthoc-note"><strong>Frozen OPX</strong><small>{world.sealed_transfer.rmse_ratio_to_zero_baseline.toFixed(3)} × zero baseline · failed</small></div>
          <div className="posthoc-note"><strong>Replacement candidate</strong><small>{world.replacement.rmse_ratio_to_zero_baseline.toFixed(3)} × zero baseline · {world.replacement.rmse_ratio_to_zero_baseline < 1 ? "passed" : "failed"}</small></div>
          <div className="posthoc-note"><strong>Evidence</strong><small>{world.replacement.point_count.toLocaleString()} sealed points · {world.translation.source}</small></div>
        </div>
      </article>)}
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">AUTONOMOUS CONTINUATION</p><h2>{campaign.next_selected_task.replaceAll("_", " ")}</h2></div></div>
      <div className="boundary-box"><p>Campaign cycle {campaign.cycle_index}</p><code>{campaign.checkpoint_digest}</code><span>The system will now search for a local semantic in the failed event world instead of forcing the two-world temporal candidate onto it.</span></div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>No universal formula was discovered in V48</h2></div></div>
      <div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>The new result is a verified computation-control semantic, not a new mathematical law. Official archives remain observational rather than causal experiments.</span></div>
    </section>
  </main>;
}
