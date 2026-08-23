import Link from "next/link";
import report from "../../data/calce_v522_latest.json";


const scoreNames: Record<string, string> = {
  autonomous_representation_creation: "自主创造表示",
  causal_mechanism_reasoning: "机制推理",
  human_unknown_scientific_law: "人类未知科学规律",
};


export default function ScienceV52Page() {
  const prediction = report.sealed_prediction;
  return <main className="report-shell">
    <nav className="report-nav"><Link href="/science-v51">← V51 evidence gates</Link><span>AKGM-N0 · V52.2</span></nav>

    <section className="hero-panel"><div className="hero-copy">
      <div className="verdict-row"><span className="verdict-badge">REAL DATA EXPERIMENT COMPLETE</span><span className="scope-label">SEALED TEST FAILED</span></div>
      <h1>第一次真实数据实验：发现了关系，也证明了程序还不会迁移</h1>
      <p className="lede">系统在不知道电池、SOC 和倍率名称时搜索了 6,675 个程序，并在提交程序后才打开 CALCE 保留组。容量双通道审计通过，但程序没有胜过“记住上一次观测”的基线，因此不能宣布新规律。</p>
      <div className="run-id"><span>VERDICT</span><code>{report.verdict}</code></div>
    </div></section>

    <section className="metric-grid meta-score-grid" aria-label="V52能力证据分">
      {Object.entries(report.capability_scores).map(([key, score]) => <article className="metric-card accent-cyan" key={key}>
        <p>{scoreNames[key] ?? key}</p><strong>{score}/10</strong><span>真实保留测试后重新审计</span>
      </article>)}
      <article className="metric-card accent-amber"><p>突破性发现</p><strong className="status-word">未建立</strong><span>文献审计确认关系已知</span></article>
    </section>

    <section className="content-grid">
      <article className="surface comparison-card">
        <div className="section-heading"><div><p className="eyebrow">SEALED PREDICTION</p><h2>冻结程序没有通过</h2></div><span className="status-pill">{report.sealed_status}</span></div>
        <div className="receipt-list">
          <div><dt>程序 RMSE</dt><dd>{prediction.forged_rmse.toFixed(6)}</dd></div>
          <div><dt>最佳基线</dt><dd>{prediction.best_baseline}</dd></div>
          <div><dt>基线 RMSE</dt><dd>{prediction.best_baseline_rmse.toFixed(6)}</dd></div>
          <div><dt>误差比 / 门槛</dt><dd>{prediction.error_ratio.toFixed(3)} / {prediction.threshold.toFixed(2)}</dd></div>
          <div><dt>容量列交叉检查</dt><dd>{prediction.logger_crosscheck_ratio.toFixed(3)}</dd></div>
        </div>
        <pre className="code-block"><code>{report.development_search.selected_expression}</code></pre>
        <p className="concept-footnote">双容量通道给出相同失败结论：{String(prediction.crosscheck_preserved_conclusion)}。失败来自迁移能力，不再归因于解析器。</p>
      </article>

      <article className="surface concept-card">
        <div className="section-heading"><div><p className="eyebrow">MATCHED RATE EFFECT</p><h2>三个窗口方向一致</h2></div><span className="evidence-chip">2 cells / condition</span></div>
        <div className="operator-discovery-grid">
          {report.matched_rate_effects.map((effect) => <div className="metric-card" key={effect.soc_window}>
            <p>SOC 窗口 {Math.round(effect.soc_window * 100)}%</p>
            <strong>{effect.high_minus_low_response.toFixed(4)}</strong>
            <span>2C − C/2 容量保持</span>
          </div>)}
        </div>
        <p className="concept-footnote">窗口越宽，高倍率组的容量保持劣势越大；这是该实验内的有界关系，不是跨化学体系定律。</p>
      </article>
    </section>

    <section className="surface gates-section">
      <div className="section-heading"><div><p className="eyebrow">FAILURE LEDGER</p><h2>每次失败都保留，不回写成功</h2></div></div>
      <div className="task-table">
        {report.experiment_timeline.map((item) => <div className="task-row" key={item.version}>
          <code>{item.version}</code><span>{item.status.replaceAll("_", " ")}</span><span>{item.reason}</span>
        </div>)}
      </div>
    </section>

    <section className="content-grid lower-grid">
      <article className="surface comparison-card">
        <div className="section-heading"><div><p className="eyebrow">PRIOR ART AUDIT</p><h2>独立恢复，但不是首次发现</h2></div></div>
        <p>{report.prior_art_audit.finding}</p>
        <a href={report.prior_art_audit.official_experiment_article}>CALCE 2016 official experiment article</a>
      </article>
      <article className="surface limitations-card">
        <div className="section-heading"><div><p className="eyebrow">HONEST BOUNDARY</p><h2>目前不能说什么</h2></div></div>
        <ol className="limitations-list">{report.honest_boundary.map((item, index) => <li key={item}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol>
      </article>
    </section>
  </main>;
}
