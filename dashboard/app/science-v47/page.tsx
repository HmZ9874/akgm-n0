import Link from "next/link";
import report from "../../data/full_text_literature_research_v47_latest.json";


const acceptance = report.acceptance;
const action = acceptance.autonomous_research_action;
const audit = acceptance.prior_art_audit;
const campaign = acceptance.long_horizon_research.campaign;
const documents = acceptance.open_full_text_evidence.documents;
const dimensions = [
  ["structure_search", "Structure search"],
  ["reusable_semantic", "Reusable semantics"],
  ["guarded_form", "Guarded / piecewise form"],
  ["interaction_product", "Interaction / product"],
  ["parsimony", "Parsimony / compression"],
  ["verification", "Verification / generalization"],
] as const;


export default function ScienceV47Page() {
  return <main className="report-shell">
    <nav className="report-nav">
      <Link href="/science-v46">← V46 operating system</Link>
      <span>AKGM-N0 · V47</span>
    </nav>

    <section className="hero-panel">
      <div className="hero-copy">
        <div className="verdict-row">
          <span className="verdict-badge">VERIFIED · AUTONOMOUS OPEN-FULL-TEXT AUDIT</span>
          <span className="scope-label">POST-DISCOVERY · NO BACKFLOW</span>
        </div>
        <h1>The system researched its own discovery—and found related human prior art</h1>
        <p className="lede">The V46 semantic was cryptographically frozen before literature access. V47 then selected four structural queries, screened {action.metadata_record_count} records, and inspected {action.full_text_document_count} openly licensed full texts. Literature classified the result but could not alter it.</p>
        <div className="run-id"><span>LATEST</span><code>{report.run_id}</code></div>
      </div>
    </section>

    <section className="metrics-grid">
      <article className="metric-card"><span>SEARCHES</span><strong>{action.search_count}</strong><small>allowlisted query families</small></article>
      <article className="metric-card"><span>METADATA</span><strong>{action.metadata_record_count}</strong><small>records screened</small></article>
      <article className="metric-card"><span>FULL TEXT</span><strong>{action.full_text_document_count}</strong><small>openly licensed documents</small></article>
      <article className="metric-card"><span>REQUEST BUDGET</span><strong>{campaign.budgets.network_requests_remaining}</strong><small>network requests remain</small></article>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">RESEARCH VERDICT</p><h2>{audit.audit_status.replaceAll("_", " ")}</h2></div></div>
      <div className="boundary-box">
        <p>What V47 established</p>
        <code>known method family + known components</code>
        <span>Symbolic/program structure search, reusable semantics, guarded forms, interaction terms, and complexity control all have related open prior art.</span>
      </div>
      <div className="boundary-box">
        <p>What V47 did not establish</p>
        <code>exact identity = false · human-unknown = false</code>
        <span>No paper was proved identical to the complete OPX composite, and absence from this corpus would not prove global novelty.</span>
      </div>
    </section>

    <section className="concept-grid">
      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">FROZEN OBJECT</p><h2>{acceptance.frozen_discovery.semantic_id}</h2></div></div>
        <div className="timeline-list">
          {acceptance.frozen_discovery.expansion_features.map((feature, index) => <div className="posthoc-note" key={feature}><strong>{feature}</strong><small>coefficient {acceptance.frozen_discovery.expansion_coefficients[index].toPrecision(6)}</small></div>)}
        </div>
        <div className="boundary-box"><p>Discovery commitment</p><code>{acceptance.frozen_discovery.commitment}</code><span>committed before the first search request</span></div>
      </article>

      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">CONCEPT COVERAGE</p><h2>Independent full-text fingerprints</h2></div></div>
        <div className="timeline-list">
          {dimensions.map(([key, label]) => {
            const item = audit.dimension_coverage[key];
            return <div className="posthoc-note" key={key}><strong>{label}</strong><small>{item.document_count} document(s) · detected={String(item.detected)}</small></div>;
          })}
        </div>
      </article>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">OPEN EVIDENCE SET</p><h2>Six documents selected without host-supplied paper IDs</h2></div></div>
      <div className="timeline-list">
        {documents.map(document => <div className="posthoc-note" key={document.pmcid}>
          <strong>{document.title}</strong>
          <small>{document.pmcid} · {document.body_word_count.toLocaleString()} body words · SHA-256 {document.receipt.sha256.slice(0, 16)}…</small>
          <a href={`https://europepmc.org/article/PMC/${document.pmcid}`} target="_blank" rel="noreferrer">Open source record ↗</a>
        </div>)}
      </div>
    </section>

    <section className="evidence-panel">
      <div className="section-heading"><div><p className="eyebrow">AUTONOMOUS CONTINUATION</p><h2>{campaign.next_selected_task.replaceAll("_", " ")}</h2></div></div>
      <div className="boundary-box"><p>Campaign cycle {campaign.cycle_index}</p><code>{campaign.checkpoint_digest}</code><span>The next cycle will challenge the learned composite on unrelated domains and send failures to the counterexample room.</span></div>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">CLAIM BOUNDARY</p><h2>Full-text audit is not exhaustive novelty proof</h2></div></div>
      <div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>Patents, books, closed publications, unpublished knowledge, expert identity review, physical experimentation, and independent-laboratory replication remain outside this run.</span></div>
    </section>
  </main>;
}
