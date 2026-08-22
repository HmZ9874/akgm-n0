import Link from "next/link";
import report from "../../data/event_world_semantic_search_v49_latest.json";


const acceptance = report.acceptance;
const program = acceptance.autonomous_language_search;
const sealed = acceptance.sealed_transfer;
const gap = report.new_gap_semantic;
const campaign = acceptance.long_horizon_research.campaign;


export default function ScienceV49Page() {
  return <main className="report-shell">
    <nav className="report-nav"><Link href="/science-v48">← V48 scope semantics</Link><span>AKGM-N0 · V49</span></nav>

    <section className="hero-panel"><div className="hero-copy">
      <div className="verdict-row"><span className="verdict-badge">VERIFIED · NEGATIVE DISCOVERY</span><span className="scope-label">73 PROGRAMS · SEALED WORLD</span></div>
      <h1>The honest next discovery is that the current observables are insufficient</h1>
      <p className="lede">V49 searched the single event world that defeated the V48 transfer candidate. No physical labels were available during search. Every memory, input, delta, self-coupling, pair interaction, and guarded path failed to produce stable predictive gain, so the system rejected formula promotion and registered an evidence gap.</p>
      <div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div>
    </div></section>

    <section className="metrics-grid">
      <article className="metric-card"><span>PROGRAMS</span><strong>{program.candidate_programs_evaluated}</strong><small>evaluated autonomously</small></article>
      <article className="metric-card"><span>VALIDATION</span><strong>{(program.validation.rmse_ratio_to_zero_baseline * 100).toFixed(3)}%</strong><small>of zero baseline error</small></article>
      <article className="metric-card"><span>SEALED</span><strong>{(sealed.rmse_ratio_to_zero_baseline * 100).toFixed(3)}%</strong><small>of zero baseline error</small></article>
      <article className="metric-card"><span>FORMULAS ACCEPTED</span><strong>0</strong><small>no forced discovery</small></article>
    </section>

    <section className="concept-grid">
      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">BEST PROGRAM</p><h2>{program.program_id}</h2></div></div>
        <div className="boundary-box"><p>Selected structure</p><code>{program.opaque_program}</code><span>Only ONE remained. All 72 attempted resource additions made validation performance worse after complexity cost.</span></div>
        <div className="timeline-list">
          <div className="posthoc-note"><strong>Stop reason</strong><small>{program.stop_reason} · {program.rounds.length} sterile rounds</small></div>
          <div className="posthoc-note"><strong>Promotion</strong><small>local_formula_accepted={String(acceptance.local_formula_accepted)}</small></div>
        </div>
      </article>

      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">NEW KNOWLEDGE STATE</p><h2>{gap.semantic_id}</h2></div></div>
        <div className="boundary-box"><p>{gap.kind}</p><code>{gap.action}</code><span>{gap.meaning}</span></div>
        <div className="timeline-list">
          <div className="posthoc-note"><strong>Formula promotion blocked</strong><small>{String(gap.formula_promotion_blocked)}</small></div>
          <div className="posthoc-note"><strong>Sealed counterexamples</strong><small>{sealed.counterexamples.length} stored for mandatory replay</small></div>
        </div>
      </article>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">POST-HOC REALITY</p><h2>{acceptance.posthoc_translation.domain}</h2></div></div>
      <div className="boundary-box"><p>{acceptance.posthoc_translation.source}</p><code>{acceptance.task_selection.target_world_id}</code><span>The searched target was catalog magnitude. Available anonymous inputs corresponded afterward to elapsed event time, latitude, longitude, and depth.</span></div>
      <div className="boundary-box"><p>Scientific interpretation</p><code>no validated predictor in the current finite language</code><span>This does not mean earthquakes are inherently unpredictable; it means this dataset, adapter, and language did not support the claimed relation.</span></div>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">AUTONOMOUS CONTINUATION</p><h2>{campaign.next_selected_task.replaceAll("_", " ")}</h2></div></div>
      <div className="boundary-box"><p>Campaign cycle {campaign.cycle_index}</p><code>{campaign.checkpoint_digest}</code><span>The next cycle must invent additional event-world observables or representational resources before trying another formula.</span></div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>Absence of evidence here is not a universal impossibility theorem</h2></div></div>
      <div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>No predictive, causal, universal, or human-unknown earthquake law is claimed.</span></div>
    </section>
  </main>;
}
