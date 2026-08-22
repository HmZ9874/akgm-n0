import data from "../../data/autonomous_intervention_v45_latest.json";

const report = data;
const acceptance = report.acceptance;
const design = acceptance.autonomous_experiment_design;
const growth = acceptance.language_growth;
const transfer = acceptance.sealed_counterfactual_audit;
const causal = acceptance.causal_effect_audit;
const translation = acceptance.posthoc_translation;
const gates = Object.entries(acceptance.discovery_gates);

export default function Page() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">AUTONOMOUS INTERVENTION V45</p><p className="brand-name">AKGM-N0 / Design → Execute → Falsify</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/science-v44">V44 worlds</a><a className="nav-link" href="/science-v39">V39 live loop</a><a className="nav-link" href="/">Overview</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">VERIFIED · COMPUTATIONAL INTERVENTION</span><span className="scope-label">PLAN → COMMIT → EXECUTE → UPDATE → FREEZE → TRANSFER</span></div><h1>The system now designs and executes its own bounded interventions</h1><p className="lede">V45 began with three anonymous control slots and no response observations. It selected a geometry-covering seed batch, then chose later actions by competing-program disagreement, leverage, novelty, and cost. After 14 live experiments it stopped at semantic saturation.</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{acceptance.passed ? "PASS" : "BOUND"}</strong><span>causal loop</span></div><p>Local computational apparatus · not nature</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>Autonomous experiments</p><strong>{design.experiment_count}</strong><span>host_selected=false</span></article>
      <article className="metric-card accent-violet"><p>Created mechanism</p><strong>{growth.selected_program.program_id}</strong><span>{growth.selected_program.features.length} retained features</span></article>
      <article className="metric-card accent-cyan"><p>Sealed transfer RMSE</p><strong>{transfer.rmse.toExponential(2)}</strong><span>{transfer.case_count} unseen interventions</span></article>
      <article className="metric-card accent-amber"><p>Stop condition</p><strong>3</strong><span>consecutive sterile rounds</span></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">AUTONOMOUS EXPERIMENT DESIGN</p><h2>Actions chosen before execution</h2></div></div><div className="timeline-list">{design.plans.map(plan => <div className="posthoc-note" key={plan.round_index}><strong>Round {plan.round_index}: {plan.kind.replaceAll("_", " ")}</strong><small>{plan.round_index === 0 ? `${plan.selected_actions?.length ?? 0} response-free coverage actions` : `utility ${plan.selected?.utility.toFixed(4)} · disagreement ${plan.selected?.normalized_disagreement.toFixed(4)}`}</small></div>)}</div><p className="concept-footnote">Every plan and batch records <code>host_selected=false</code>; unsafe actions are rejected by the external broker.</p></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">LANGUAGE GROWTH</p><h2>Mechanism built from structural mutations</h2></div></div><div className="timeline-list">{growth.selected_mutations.map((mutation, index) => <div className="posthoc-note" key={mutation}><strong>Mutation {index + 1}</strong><small>{mutation}</small></div>)}</div><div className="boundary-box"><p>Internal program</p><code>{growth.selected_program.opaque_program}</code><span>No target formula or named mechanism family was supplied.</span></div></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">SEALED COUNTERFACTUALS</p><h2>Frozen before a new process executed transfer actions</h2></div></div><div className="bar-chart"><div className="bar-row"><div className="bar-label"><span>RMSE</span><strong>{transfer.rmse.toExponential(5)}</strong></div><div className="bar-track"><div className="bar library" style={{width: "1%"}} /></div></div><div className="bar-row"><div className="bar-label"><span>Maximum absolute error</span><strong>{transfer.maximum_absolute_error.toExponential(5)}</strong></div><div className="bar-track"><div className="bar library" style={{width: "1%"}} /></div></div></div></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">CAUSAL EFFECT AUDIT</p><h2>Every assigned control changes the response</h2></div></div><div className="timeline-list">{causal.essential_controls.map(item => <div className="posthoc-note" key={item.control_slot}><strong>{item.control_slot}: {item.essential_effect_observed ? "ESSENTIAL" : "UNRESOLVED"}</strong><small>{item.nonzero_effect_count}/{item.matched_pair_count} matched pairs produced a nonzero effect</small></div>)}</div></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">POST-HOC TRANSLATION</p><h2>Human-readable counterpart</h2></div></div><div className="boundary-box"><p>{translation.human_equivalent}</p><code>{translation.internal_formula}</code><span>Q0, Q1, and Q2 were executable loop bounds; the response was executed operation count. Labels were revealed after discovery.</span></div></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">MISTAKE ROOM</p><h2>Rejected mechanisms remain replayable</h2></div></div><div className="boundary-box"><p>Rejected structural trials</p><code>{acceptance.mistake_room.rejected_structural_features.length}</code><span>They may be reconsidered only when new intervention evidence changes cross-validated score.</span></div></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROOF GATES</p><h2>Execution, safety, transfer, and overclaim control</h2></div></div><div className="operator-discovery-grid">{gates.map(([name, passed]) => <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{passed ? "PASS" : "FAIL"}</strong><span>{passed ? "evidence recorded" : "counterexample recorded"}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>Autonomous intervention is achieved only inside the bounded apparatus</h2></div></div><div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>This proves autonomous experimental control software. It does not prove intervention on an unknown natural system, independent-laboratory replication, or a fully autonomous scientist.</span></div></section>
  </main>;
}
