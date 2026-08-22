import data from "../../data/counterexample_transfer_v42_latest.json";

const report = data;
const acceptance = report.acceptance;
const discovery = acceptance.discovery;
const transfer = acceptance.transfer_audit;
const feedback = acceptance.counterexample_feedback;
const stages = [
  ["Early", transfer.by_life_stage.early.rmse],
  ["Middle", transfer.by_life_stage.middle.rmse],
  ["Late", transfer.by_life_stage.late.rmse],
] as const;
const candidates = [
  ["STATE_FOLD", discovery.candidate_validation.state_fold.validation_rmse],
  ["CONTEXT_FOLD", discovery.candidate_validation.context_fold.validation_rmse],
  ["INTERACTION_FOLD", discovery.candidate_validation.interaction_fold.validation_rmse],
] as const;
const gates = Object.entries(acceptance.discovery_gates);

export default function Page() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">COUNTEREXAMPLE TRANSFER V42</p><p className="brand-name">AKGM-N0 / Frozen cross-object replication</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/science-v41-challenge">V41 challenge</a><a className="nav-link" href="/science-v41">V41 discovery</a><a className="nav-link" href="/">Overview</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">VERIFIED · BOUNDED CLAIM</span><span className="scope-label">COUNTEREXAMPLE → SEARCH → FREEZE → REVEAL → TRANSFER</span></div><h1>INTERACTION_FOLD transfers below the threshold on every reused-archive stage</h1><p className="lede">The learner consumed the V41 late-life failure, searched anonymous programs on object A, froze one program, and only then received object B. Domain, object, and life-stage labels were unavailable during selection.</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{acceptance.passed ? "PASS" : "BOUND"}</strong><span>programmatic transfer</span></div><p>Fresh external replication is still required</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>Selected program</p><strong>{discovery.selected.created_operator}</strong><span>{discovery.selected.program_id}</span></article>
      <article className="metric-card accent-violet"><p>RW5 validation RMSE</p><strong>{discovery.selected.validation_rmse.toFixed(4)}</strong><span>selected before transfer reveal</span></article>
      <article className="metric-card accent-cyan"><p>RW6 transfer RMSE</p><strong>{transfer.overall.rmse.toFixed(4)}</strong><span>60 frozen-transfer trajectories</span></article>
      <article className="metric-card accent-amber"><p>Late-stage RMSE</p><strong>{transfer.by_life_stage.late.rmse.toFixed(4)}</strong><span>registered ceiling {transfer.threshold_rmse.toFixed(2)}</span></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">SEMANTIC COMPETITION</p><h2>Validation selected the composed operator</h2></div></div><div className="bar-chart">{candidates.map(([name, value]) => <div className="bar-row" key={name}><div className="bar-label"><span>{name}</span><strong>{value.toFixed(5)}</strong></div><div className="bar-track"><div className={`bar ${name === "INTERACTION_FOLD" ? "library" : "baseline"}`} style={{width: `${Math.min(100, value / 0.11 * 100)}%`}} /></div></div>)}</div><p className="concept-footnote">Score = validation RMSE + 10⁻⁵ × program nodes. No transfer measurements participate in selection.</p></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">FROZEN TRANSFER</p><h2>All three stages remain below 0.10</h2></div></div><div className="bar-chart">{stages.map(([name, value]) => <div className="bar-row" key={name}><div className="bar-label"><span>{name}</span><strong>{value.toFixed(5)} · {value < transfer.threshold_rmse ? "PASS" : "FAIL"}</strong></div><div className="bar-track"><div className={`bar ${value < transfer.threshold_rmse ? "library" : "baseline"}`} style={{width: `${Math.min(100, value / transfer.threshold_rmse * 100)}%`}} /></div></div>)}</div></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">COUNTEREXAMPLE FEEDBACK</p><h2>The V41 failure changed the next search</h2></div></div><div className="posthoc-note"><strong>{feedback.consumed_failure_id}</strong><small>Previous late RMSE {feedback.previous_observed_rmse.toFixed(5)} → V42 transfer late RMSE {feedback.new_transfer_late_rmse.toFixed(5)}. The earlier universal claim remains revoked.</small></div><div className="boundary-box"><p>Created computation</p><code>{discovery.selected.opaque_program}</code><span>Internal composition only; this is not presented as a new electrochemical law.</span></div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROOF GATES</p><h2>Every engineering gate passes</h2></div></div><div className="operator-discovery-grid">{gates.map(([name, passed]) => <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{passed ? "PASS" : "FAIL"}</strong><span>{passed ? "evidence recorded" : "counterexample recorded"}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>What this run does not prove</h2></div></div><div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>Developers had prior access to this reused archive. A different campaign or laboratory must supply the next genuinely fresh sealed test.</span></div></section>
  </main>;
}
