import data from "../../data/autonomous_science_os_v46_latest.json";

const report = data;
const acceptance = report.acceptance;
const network = acceptance.network_reality;
const language = acceptance.open_language_creation;
const causal = acceptance.causal_and_mechanism_reasoning;
const instrument = acceptance.instrument_architecture;
const campaign = acceptance.long_horizon_research.campaign;
const literature = acceptance.literature_and_human_knowledge_audit;
const capabilities = Object.entries(acceptance.capability_status);
const gates = Object.entries(acceptance.discovery_gates);

export default function Page() {
  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">AUTONOMOUS SCIENCE OS V46</p><p className="brand-name">AKGM-N0 / Network → Language → Cause → Instrument → Literature</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/science-v45">V45 intervention</a><a className="nav-link" href="/science-v44">V44 worlds</a><a className="nav-link" href="/">Overview</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy"><div className="verdict-row"><span className="verdict-badge">VERIFIED · UNIFIED BOUNDED OS</span><span className="scope-label">SEVEN CAPABILITIES · ONE EVIDENCE CHAIN</span></div><h1>The research kernel can now collect, extend, reason, design, remember, and audit</h1><p className="lede">V46 unifies allowlisted network reality collection, sandboxed language creation, intervention-based mechanism reasoning, instrument architecture, persistent research budgeting, and Crossref knowledge auditing. Every partial capability keeps its own execution boundary.</p><div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div></div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{acceptance.passed ? "PASS" : "BOUND"}</strong><span>science OS</span></div><p>Fabrication and natural intervention remain external</p></div>
    </section>

    <section className="metric-grid">
      <article className="metric-card accent-cyan"><p>Network records collected</p><strong>{network.collection.record_count}</strong><span>{network.agenda.selected.source_id} · host_selected=false</span></article>
      <article className="metric-card accent-violet"><p>Invented opcode</p><strong>{language.invented_semantic.semantic_id}</strong><span>{language.invented_semantic.token_savings_per_use} tokens saved per use</span></article>
      <article className="metric-card accent-cyan"><p>Instrument blueprint</p><strong>{instrument.blueprint.blueprint_id}</strong><span>{instrument.verification.present_interlock_count} safety interlocks verified</span></article>
      <article className="metric-card accent-amber"><p>Campaign cycle</p><strong>{campaign.cycle_index}</strong><span>next: {campaign.next_selected_task}</span></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CAPABILITY MATRIX</p><h2>Executed evidence is separated from design-only progress</h2></div></div><div className="operator-discovery-grid">{capabilities.map(([name, status]) => { const open = status.includes("not executed") || status.includes("pending") || status.includes("no new"); return <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{open ? "PARTIAL" : "DONE"}</strong><span>{status.replaceAll("_", " ")}</span></article>; })}</div></section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">NETWORK REALITY</p><h2>Gap-selected official acquisition</h2></div></div><div className="boundary-box"><p>Anonymous source commitment</p><code>{network.preregistration.source_commitment}</code><span>commit {network.preregistration.commit_event_index} → collect {network.preregistration.collection_event_index} → metadata {network.preregistration.metadata_reveal_event_index}</span></div><div className="boundary-box"><p>Receipt SHA-256</p><code>{network.collection.receipt.sha256}</code><span>{network.collection.receipt.bytes} bytes · HTTP {network.collection.receipt.status} · arbitrary URLs disabled</span></div><div className="boundary-box"><p>Post-hoc domain</p><code>{network.posthoc_source_metadata.domain}</code><span>{network.posthoc_source_metadata.institution}</span></div></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">OPEN LANGUAGE GROWTH</p><h2>A discovered program became a new opcode</h2></div></div><div className="boundary-box"><p>{language.invented_semantic.semantic_id}</p><code>{language.invented_semantic.expansion_features.join(" + ")}</code><span>primitive cost {language.invented_semantic.primitive_token_cost} → macro cost {language.invented_semantic.macro_token_cost}</span></div><div className="boundary-box"><p>Independent expansion replay</p><code>{language.independent_expansion_verification.maximum_expansion_error.toExponential(2)}</code><span>{language.independent_expansion_verification.case_count} sealed cases · native code remains blocked</span></div></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">CAUSAL MECHANISM REASONING</p><h2>Ablation makes both structures necessary</h2></div></div><div className="timeline-list">{causal.mechanism_ablation.map(item => <div className="posthoc-note" key={item.removed_feature}><strong>Remove {item.removed_feature}</strong><small>sealed RMSE {item.sealed_rmse.toFixed(4)} · {item.mechanistically_essential ? "ESSENTIAL" : "REDUNDANT"}</small></div>)}</div><p className="concept-footnote">{causal.confounding_assessment}. A unique universal graph is not claimed.</p></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">INSTRUMENT ARCHITECTURE</p><h2>Design verified; fabrication not executed</h2></div></div><div className="boundary-box"><p>Status</p><code>{instrument.blueprint.current_status}</code><span>fabrication_executed={String(instrument.blueprint.fabrication_executed)}</span></div><div className="timeline-list">{instrument.blueprint.mandatory_interlocks.map(item => <div className="posthoc-note" key={item}><strong>{item.replaceAll("_", " ")}</strong><small>mandatory external safety control</small></div>)}</div></article>
    </section>

    <section className="content-grid operation-grid">
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">LONG-HORIZON MANAGEMENT</p><h2>Persistent budgets and resumable agenda</h2></div></div><div className="metric-grid"><article className="metric-card"><p>Compute remaining</p><strong>{campaign.budgets.compute_units_remaining}</strong></article><article className="metric-card"><p>Network requests</p><strong>{campaign.budgets.network_requests_remaining}</strong></article></div><div className="timeline-list">{campaign.tasks.map(task => <div className="posthoc-note" key={task.task_id}><strong>{task.task_id.replaceAll("_", " ")}</strong><small>{task.status.replaceAll("_", " ")} · gain {task.information_gain} · cost {task.cost} · risk {task.risk}</small></div>)}</div></article>
      <article className="surface concept-card"><div className="section-heading"><div><p className="eyebrow">HUMAN KNOWLEDGE AUDIT</p><h2>{literature.audit_status.replaceAll("_", " ")}</h2></div></div><div className="boundary-box"><p>{literature.provider}</p><code>{literature.record_count} metadata records</code><span>full_text_reviewed={String(literature.full_text_reviewed)} · human_unknown_claim_allowed={String(literature.human_unknown_claim_allowed)}</span></div><div className="timeline-list">{literature.top_records.slice(0, 5).map(item => <div className="posthoc-note" key={item.doi ?? item.title}><strong>{item.title ?? "Untitled metadata record"}</strong><small>{item.doi ?? "no DOI"} · overlap {item.query_token_overlap.toFixed(3)}</small></div>)}</div></article>
    </section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">PROOF GATES</p><h2>Unified replay and claim control</h2></div></div><div className="operator-discovery-grid">{gates.map(([name, passed]) => <article className="metric-card" key={name}><p>{name.replaceAll("_", " ")}</p><strong className="operator-name">{passed ? "PASS" : "FAIL"}</strong><span>{passed ? "evidence recorded" : "counterexample recorded"}</span></article>)}</div></section>

    <section className="evidence-panel limitations-panel"><div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>Unified autonomy is not unrestricted autonomy</h2></div></div><div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>No physical instrument was fabricated, no new unknown natural system was manipulated, and no exhaustive literature or independent-laboratory review was completed.</span></div></section>
  </main>;
}
