import Link from "next/link";
import report from "../../data/breakthrough_research_v51_latest.json";


const acceptance = report.acceptance;
const axes = acceptance.ten_gate_standard.axes;
const mechanism = acceptance.mechanism_tournament;
const representation = acceptance.representation_forge;

const axisNames: Record<string, string> = {
  autonomous_representation_creation: "自主创造表示",
  causal_mechanism_reasoning: "机制推理",
  human_unknown_scientific_law: "人类未知科学规律",
};

const gateNames: Record<string, string> = {
  independent_natural_domain_transfer: "独立自然领域迁移",
  natural_system_external_intervention: "真实自然系统外部干预",
  independent_source_replication: "独立数据源复现",
  causal_mechanism_evidence: "因果机制证据",
  prospective_novel_prediction: "前瞻新预测",
  preclaim_open_literature_audit: "声明前开放文献审计",
  broad_prior_art_coverage: "广覆盖先验技术审计",
  independent_expert_novelty_review: "独立专家新颖性复核",
  independent_laboratory_replication: "独立实验室复现",
};


export default function ScienceV51Page() {
  return <main className="report-shell">
    <nav className="report-nav"><Link href="/science-v50">← V50 bounded rediscovery</Link><span>AKGM-N0 · V51</span></nav>

    <section className="hero-panel"><div className="hero-copy">
      <div className="verdict-row"><span className="verdict-badge">ARCHITECTURE UPGRADED</span><span className="scope-label">BREAKTHROUGH CLAIM BLOCKED</span></div>
      <h1>把“10分”变成十道不能跳过的证据门</h1>
      <p className="lede">V51 增加了行为等价审计、407 个竞争机制、主动辨别干预、关键机制消融和可执行表示压缩。分数由证据自动计算；没有独立自然数据与外部复现时，系统不能把自己评为 10。</p>
      <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
    </div></section>

    <section className="metric-grid meta-score-grid" aria-label="三项能力证据分">
      {axes.map((axis) => <article className="metric-card accent-cyan" key={axis.axis_id}>
        <p>{axisNames[axis.axis_id] ?? axis.axis_id}</p>
        <strong>{axis.score}/10</strong>
        <span>{axis.reached_ten ? "十门全部通过" : `${axis.blocking_gates.length} 门仍被证据锁住`}</span>
      </article>)}
      <article className="metric-card accent-amber"><p>突破性发现</p><strong className="status-word">未建立</strong><span>禁止把架构进步冒充科学突破</span></article>
    </section>

    <section className="content-grid">
      <article className="surface comparison-card">
        <div className="section-heading"><div><p className="eyebrow">MECHANISM TOURNAMENT</p><h2>不是只拟合一个公式，而是让机制互相竞争</h2></div><span className="evidence-chip">sealed RMSE {mechanism.sealed_audit.rmse.toExponential(2)}</span></div>
        <div className="receipt-list">
          <div><dt>生成候选机制</dt><dd>{mechanism.programs_generated}</dd></div>
          <div><dt>行为类别</dt><dd>{mechanism.behavior_classes}</dd></div>
          <div><dt>反事实探针</dt><dd>{mechanism.probe_count}</dd></div>
          <div><dt>胜者 / 次名分差</dt><dd>{mechanism.selected_score_gap.toFixed(6)}</dd></div>
          <div><dt>主动选择的下一干预</dt><dd>[{mechanism.next_discriminating_intervention.action.join(", ")}]</dd></div>
        </div>
        <div className="posthoc-note"><span>SELECTED ANONYMOUS MECHANISM</span><strong>{mechanism.selected.mechanism_id}</strong><small>{mechanism.selected.features.join(" + ")}</small></div>
      </article>

      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">REPRESENTATION FORGE</p><h2>{representation.representation_id}</h2></div><span className="status-pill">SANDBOXED</span></div>
        <dl className="concept-facts">
          <div><dt>原展开代价</dt><dd>{representation.primitive_token_cost}</dd></div>
          <div><dt>新表示代价</dt><dd>{representation.macro_token_cost}</dd></div>
          <div><dt>验证探针</dt><dd>{representation.probe_count}</dd></div>
        </dl>
        <pre className="code-block"><code>{JSON.stringify(representation.expansion, null, 2)}</code></pre>
        <p className="concept-footnote">这是程序从胜出机制压缩出的可执行复合表示，不是不可约的新数学原语；密封误差为 {representation.sealed_macro_rmse.toExponential(2)}。</p>
      </article>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">TEN-GATE CONTRACT</p><h2>还没通过的门</h2></div><p className="section-note">任何一门失败，对应的 10/10 声明自动失效</p></div>
      <div className="gate-grid">
        {axes.flatMap((axis) => axis.blocking_gates.map((gate) => <div className="gate-item" key={`${axis.axis_id}-${gate}`}>
          <span className="gate-light failed" />
          <div><strong>{gateNames[gate] ?? gate}</strong><span>{axisNames[axis.axis_id]}</span></div>
        </div>))}
      </div>
    </section>

    <section className="content-grid lower-grid">
      <article className="surface task-table-card">
        <div className="section-heading"><div><p className="eyebrow">AUTONOMOUS NEXT WORK</p><h2>按缺口而不是按版本号推进</h2></div></div>
        <div className="task-table">
          {acceptance.ten_gate_standard.next_tasks.map((task) => <div className="task-row" key={task.task_id}>
            <code>{task.task_id}</code><span>P{task.priority}</span><span>{task.closes.length} gates</span><span>{task.status.replaceAll("_", " ")}</span>
          </div>)}
        </div>
      </article>
      <article className="surface limitations-card">
        <div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>目前不能说什么</h2></div></div>
        <ol className="limitations-list">{acceptance.limitations.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol>
      </article>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="boundary-box"><p>Current label</p><code>{acceptance.claim_state.current_label}</code><span>独立验证器已通过，但它验证的是架构和证据锁，不是“已经发现未知规律”。</span></div>
    </section>
  </main>;
}
