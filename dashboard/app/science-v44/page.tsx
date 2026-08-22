import data from "../../data/autonomous_world_research_v44_latest.json";

const report = data;
const acceptance = report.acceptance;
const agenda = acceptance.autonomous_agenda;
const discovery = acceptance.discovery;
const transfer = acceptance.sealed_transfer_audit;
const translation = acceptance.posthoc_translation;
const ranking = agenda.ranking;
const progress = Object.entries(acceptance.capability_progress);
const gates = Object.entries(acceptance.discovery_gates);

export default function Page() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">AUTONOMOUS WORLD RESEARCH V44</p><p className="brand-name">AKGM-N0 / Official-world blind selection</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/science-v43">V43 language</a><a className="nav-link" href="/science-v42">V42 transfer</a><a className="nav-link" href="/">Overview</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">VERIFIED · BOUNDED AUTONOMY</span><span className="scope-label">SURVEY → RANK → COMMIT → REVEAL → REPLAY</span></div><h1>The system selected what to study before it knew the scientific domain</h1><p className="lede">V44 surveyed three anonymous official worlds from NASA, NOAA, and USGS. A first blind choice failed sealed transfer; that counterexample changed the development-only risk logic. The next preregistered run selected a different world and passed two unseen source groups.</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{acceptance.passed ? "PASS" : "BOUND"}</strong><span>world selection</span></div><p>Fully autonomous scientist remains blocked</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>Selected anonymous world</p><strong>{agenda.selected_world_id}</strong><span>host_selected=false</span></article>
      <article className="metric-card accent-violet"><p>Created program</p><strong>{discovery.selected_program.program_id}</strong><span>{discovery.candidate_programs_evaluated} programs in selected world</span></article>
      <article className="metric-card accent-cyan"><p>Sealed transfer NRMSE</p><strong>{transfer.normalized_rmse.toFixed(4)}</strong><span>pass threshold &lt; 1.0</span></article>
      <article className="metric-card accent-amber"><p>Queued worlds</p><strong>{agenda.next_research_queue.length}</strong><span>remain sealed for later research</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">AUTONOMOUS AGENDA</p><h2>World ranking before domain reveal</h2></div></div><div className="operator-discovery-grid">{ranking.map((item, index) => <article className="metric-card" key={item.world_id}><p>Rank {index + 1} · {item.world_id}</p><strong className="operator-name">{item.research_priority.toFixed(4)}</strong><span>gain {item.normalized_information_gain.toFixed(3)} · stability {item.cross_group_stability.toFixed(3)} · {index === 0 ? "SELECTED" : "SEALED QUEUE"}</span></article>)}</div></section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">SELF-GROWN LANGUAGE</p><h2>Resources selected by score</h2></div></div><div className="timeline-list">{discovery.selected_mutations.map((mutation, index) => <div className="posthoc-note" key={`${mutation}-${index}`}><strong>Step {index + 1}: {mutation}</strong><small>no named model or physical variable was supplied</small></div>)}</div><p className="concept-footnote">Stop reason: <code>{discovery.stop_reason}</code>.</p></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">SEALED TRANSFER</p><h2>Source groups never overlap</h2></div></div><div className="boundary-box"><p>Training</p><code>{transfer.training_groups.join(", ")}</code></div><div className="boundary-box"><p>Validation</p><code>{transfer.validation_groups.join(", ")}</code></div><div className="boundary-box"><p>Transfer</p><code>{transfer.transfer_groups.join(", ")}</code><span>program and agenda were committed first</span></div></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">POST-HOC MEANING</p><h2>{translation.domain}</h2></div></div><div className="boundary-box"><p>{translation.human_equivalent_task}</p><code>{translation.internal_formula}</code><span>{translation.institution} · labels were revealed only after transfer scoring.</span></div></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">MISTAKE ROOM</p><h2>Failure changes future selection</h2></div></div><div className="boundary-box"><p>First blind failure</p><code>{acceptance.mistake_room.mandatory_replay_history[0]?.event_id ?? "none"}</code><span>Cross-source-group stability is now mandatory; transfer measurements were not used for refitting.</span></div><div className="boundary-box"><p>Rejected language mutations</p><code>{acceptance.mistake_room.rejected_language_mutations.length}</code><span>retained for replay when evidence changes</span></div></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">AUTONOMY LEDGER</p><h2>What is complete and what still needs reality</h2></div></div><div className="operator-discovery-grid">{progress.map(([name, status]) => <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{status.includes("not_") ? "OPEN" : status.includes("not_available") ? "OPEN" : "DONE"}</strong><span>{status.replaceAll("_", " ")}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROOF GATES</p><h2>Independent replay and claim control</h2></div></div><div className="operator-discovery-grid">{gates.map(([name, passed]) => <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{passed ? "PASS" : "FAIL"}</strong><span>{passed ? "evidence recorded" : "counterexample recorded"}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>External archive autonomy is not complete science autonomy</h2></div></div><div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>Causal intervention, live apparatus, unrestricted language invention, literature novelty adjudication, and independent-laboratory replication remain open.</span></div></section>
  </main>;
}
