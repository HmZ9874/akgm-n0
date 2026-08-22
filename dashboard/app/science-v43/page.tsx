import data from "../../data/autonomous_scientist_v43_latest.json";

const report = data;
const acceptance = report.acceptance;
const discovery = acceptance.discovery;
const transfer = acceptance.transfer_audit;
const translation = acceptance.posthoc_translation;
const selectedRounds = discovery.rounds.filter(item => item.selected_mutation !== null);
const stages = [
  ["Early", transfer.by_life_stage.early.rmse],
  ["Middle", transfer.by_life_stage.middle.rmse],
  ["Late", transfer.by_life_stage.late.rmse],
] as const;
const gates = Object.entries(acceptance.discovery_gates);

export default function Page() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">AUTONOMOUS SCIENTIST KERNEL V43</p><p className="brand-name">AKGM-N0 / Research-language growth</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/science-v42">V42 transfer</a><a className="nav-link" href="/science-v41-challenge">V41 challenge</a><a className="nav-link" href="/">Overview</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">VERIFIED · BOUNDED AUTONOMY</span><span className="scope-label">MINIMAL GENOME → MUTATE → SCORE → FREEZE → TRANSFER</span></div><h1>The system changed its research language instead of choosing from named models</h1><p className="lede">V43 started with one visible input and no recurrent state. It evaluated 22 executable genomes, autonomously grew two state slots and another input channel, then stopped only after three sterile research rounds.</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{acceptance.passed ? "PASS" : "BOUND"}</strong><span>language growth</span></div><p>A fully autonomous scientist is not yet claimed</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>Created semantic</p><strong>{discovery.selected_program.program_id}</strong><span>{discovery.selected_program.node_count} executable nodes</span></article>
      <article className="metric-card accent-violet"><p>Programs evaluated</p><strong>{discovery.candidate_programs_evaluated}</strong><span>no named candidate menu</span></article>
      <article className="metric-card accent-cyan"><p>Transfer RMSE</p><strong>{transfer.overall.rmse.toFixed(4)}</strong><span>V42 was {transfer.v42_overall_rmse.toFixed(4)}</span></article>
      <article className="metric-card accent-amber"><p>Stop condition</p><strong>{discovery.sterile_rounds}</strong><span>consecutive sterile rounds</span></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">AUTONOMOUS AGENDA</p><h2>Selected structural mutations</h2></div></div><div className="timeline-list">{selectedRounds.map(item => <div className="posthoc-note" key={item.round_index}><strong>Round {item.round_index}: {item.selected_mutation}</strong><small>score {item.score_before.toFixed(5)} → {item.score_after.toFixed(5)} · information gain {item.information_gain.toFixed(5)}</small></div>)}</div><p className="concept-footnote">Every round records <code>host_selected=false</code>. Unsuccessful context, interaction, input, delta, and branch mutations remain in the research ledger.</p></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">GENOME CHANGE</p><h2>Memory was created as a research resource</h2></div></div><div className="boundary-box"><p>Initial</p><code>inputs={discovery.initial_genome.visible_inputs}; state_slots={discovery.initial_genome.state_slots}</code><span>constant plus one anonymous observation</span></div><div className="boundary-box"><p>Final</p><code>inputs={discovery.final_genome.visible_inputs}; state_slots={discovery.final_genome.state_slots}</code><span>two anonymous observations and two recurrent memory slots</span></div></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">FROZEN TRANSFER</p><h2>Every reused-archive stage stays below 0.10</h2></div></div><div className="bar-chart">{stages.map(([name, value]) => <div className="bar-row" key={name}><div className="bar-label"><span>{name}</span><strong>{value.toFixed(5)} · {value < transfer.threshold_rmse ? "PASS" : "FAIL"}</strong></div><div className="bar-track"><div className={`bar ${value < transfer.threshold_rmse ? "library" : "baseline"}`} style={{width: `${Math.min(100, value / transfer.threshold_rmse * 100)}%`}} /></div></div>)}</div></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">POST-HOC TRANSLATION</p><h2>Human-readable counterpart</h2></div></div><div className="boundary-box"><p>{translation.human_equivalent_family}</p><code>{translation.formula}</code><span>The learner never received this name, formula, or physical channel mapping.</span></div></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROOF GATES</p><h2>Independent replay and claim control</h2></div></div><div className="operator-discovery-grid">{gates.map(([name, passed]) => <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{passed ? "PASS" : "FAIL"}</strong><span>{passed ? "evidence recorded" : "counterexample recorded"}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>This is a kernel milestone, not the end goal</h2></div></div><div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>State width, mutation operators, arithmetic, and coefficient fitting are still supplied. The next test requires a fresh external world and autonomous data/experiment selection.</span></div></section>
  </main>;
}
