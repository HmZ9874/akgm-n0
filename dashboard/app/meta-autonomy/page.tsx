import baselineData from "../../data/meta_autonomy_v3_latest.json";
import researchData from "../../data/deep_meta_research_latest.json";
import operatorCatalogData from "../../data/operator_catalog_v5_latest.json";

const research = researchData;
const benchmark = research.benchmark;
const scoreLabels: Record<string, { name: string; note: string }> = {
  expanded_sealed_generalization: { name: "扩展封闭泛化", note: "11 个匿名世界的未见数据" },
  proof_portfolio_coverage: { name: "证明组合覆盖", note: "多项式、特征量、乘积归纳、C-finite" },
  structural_self_extension: { name: "结构自扩展", note: "7 类资源基因均由缺口触发" },
  autonomous_curriculum: { name: "自主课程", note: "世界顺序由学习器评分选择" },
  library_transfer_efficiency: { name: "程序库迁移", note: "学习宏对原始枚举的候选削减" },
};

export default function MetaAutonomyPage() {
  const scores = benchmark.dimension_scores as Record<string, number>;
  const sealedPassed = benchmark.sealed_results.filter((item) => item.passed).length;
  const proofPassed = benchmark.proof_results.filter((item) => item.passed).length;
  const mutations = Array.from(new Set(benchmark.autonomous_selections.flatMap((item) => item.mutations)));
  const library = benchmark.library_learning;
  const operatorCatalog = operatorCatalogData.catalog;
  const operators = operatorCatalog.operators;
  const foundationalOperators = operators.filter((item) => item.classification !== "derived_executable_operator");

  return <main>
    <header className="masthead">
      <div className="brand-lockup"><span className="brand-mark gen1-mark">●</span><div><p className="eyebrow">META-AUTONOMY V5</p><p className="brand-name">AKGM-N0 / 50 运算符自主探索</p></div></div>
      <div className="run-meta"><a className="nav-link" href="/foundation-v8">新基础17–20</a><a className="nav-link" href="/operator-500">500运算研究</a><a className="nav-link" href="/high-school">高中门槛</a><a className="nav-link" href="/foundation">数学发展谱系</a><a className="nav-link" href="/mistakes">错题库</a><a className="nav-link" href="/">总览</a></div>
    </header>

    <section className="hero panel-grid operation-hero">
      <div className="hero-copy">
        <div className="verdict-row"><span className="verdict-badge">深度基准通过</span><span className="scope-label">EXPANDED SYMBOLIC RESEARCH</span></div>
        <h1>最弱维度从 {baselineData.benchmark.overall_score.toFixed(1)} 提升到 {benchmark.overall_score.toFixed(2)} / 10</h1>
        <p className="lede">非 Transformer、无目标公式输入。框架新增计数—状态交互、系数空间扩展、仿射特征量证明、C-finite 递推证明，以及从多个独立解中压缩程序宏的能力。</p>
        <div className="run-id"><span>LATEST</span><code>{research.run_id}</code><code>{research.verdict}</code></div>
      </div>
      <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{benchmark.overall_score.toFixed(2)}</strong><span>五项最低分</span></div><p>限定的符号程序创造基准</p></div>
    </section>

    <section className="metric-grid meta-score-grid">
      {Object.entries(scores).map(([key, value]) => <article className="metric-card accent-cyan" key={key}>
        <p>{scoreLabels[key]?.name ?? key}</p><strong>{value.toFixed(2)}</strong><span>{scoreLabels[key]?.note}</span>
        <div className="capability-meter"><i style={{ width: `${value * 10}%` }} /></div>
      </article>)}
    </section>

    <section className="panel-grid two-column">
      <article className="evidence-panel">
        <div className="section-heading"><div><p className="eyebrow">SEALED WORLDS</p><h2>封闭泛化 {sealedPassed}/{benchmark.sealed_results.length}</h2></div><span className="status-chip good">全部通过</span></div>
        <div className="evidence-list">
          {benchmark.sealed_results.map((item) => <div className="evidence-row" key={item.world_id}>
            <div><code>{item.world_id}</code><strong>{item.evaluator_interpretation}</strong><span>解释与封闭值均未提供给学习器</span></div><b>{item.sealed_passed}/{item.sealed_total}</b>
          </div>)}
        </div>
      </article>

      <article className="evidence-panel">
        <div className="section-heading"><div><p className="eyebrow">PROGRAM GENOME</p><h2>自主触发 {mutations.length}/7 类变异</h2></div><span className="status-chip good">SELF-GROWN</span></div>
        <div className="chip-cloud">{mutations.map((item) => <code key={item}>{item}</code>)}</div>
        <div className="boundary-box"><p>初始基因组</p><code>{JSON.stringify(benchmark.initial_genome)}</code><p>最终基因组</p><code>{JSON.stringify(benchmark.final_genome)}</code></div>
        <div className="section-heading research-subheading"><div><p className="eyebrow">KEY FINDINGS</p><h2>本轮结构发现</h2></div></div>
        <ul>{benchmark.research_findings.map((item) => <li key={item}>{item}</li>)}</ul>
      </article>
    </section>

    <section className="panel-grid two-column">
      <article className="evidence-panel">
        <div className="section-heading"><div><p className="eyebrow">PROOF PORTFOLIO</p><h2>循环证明 {proofPassed}/{benchmark.proof_results.length}</h2></div><span className="status-chip good">100%</span></div>
        <div className="evidence-list">
          {benchmark.proof_results.map((item) => <div className="evidence-row" key={item.program_id}>
            <div><code>{item.program_id}</code><strong>{item.proof_domains.join(" + ")}</strong><span>证书由固定内核重新计算并复验</span></div><b>{item.passed ? "PASS" : "FAIL"}</b>
          </div>)}
        </div>
      </article>

      <article className="evidence-panel">
        <div className="section-heading"><div><p className="eyebrow">LIBRARY LEARNING</p><h2>多解压缩 → 新世界迁移</h2></div><span className="status-chip good">−{(library.candidate_reduction_fraction * 100).toFixed(2)}%</span></div>
        <div className="metric-grid room-metrics">
          <div className="metric-card"><p>原始枚举</p><strong>{library.primitive_baseline_candidates}</strong><span>执行候选</span></div>
          <div className="metric-card"><p>宏引导搜索</p><strong>{library.macro_candidates}</strong><span>执行候选</span></div>
        </div>
        <div className="chip-cloud">{library.macros.map((macro) => <code key={macro.macro_id}>{macro.macro_id} · 节省 {macro.token_savings_per_use} token</code>)}</div>
        <div className="boundary-box"><p>完全保留的迁移世界</p><code>{library.transfer_sealed.world_id}</code><span>封闭复验 {library.transfer_sealed.sealed_passed}/{library.transfer_sealed.sealed_total}</span></div>
        <div className="metric-grid room-metrics">
          <div className="metric-card"><p>成功房间</p><strong>{research.rooms.success_count}</strong><span>哈希链与证明重放</span></div>
          <div className="metric-card"><p>研究错题</p><strong>{research.rooms.mistake_count}</strong><span>架构反模式已记录</span></div>
        </div>
      </article>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">OPERATOR CATALOG V5</p><h2>已验证运算语义 {operatorCatalog.promoted_operator_count}/50</h2></div><span className="status-chip good">50 个程序与行为签名均不重复</span></div>
      <div className="metric-grid room-metrics">
        <div className="metric-card"><p>独立程序</p><strong>{operatorCatalog.unique_program_count}</strong><span>程序结构去重</span></div>
        <div className="metric-card"><p>独立行为</p><strong>{operatorCatalog.unique_behavior_signature_count}</strong><span>声明域行为去重</span></div>
        <div className="metric-card"><p>基础结构突破</p><strong>{foundationalOperators.length}</strong><span>其余是可执行派生语义</span></div>
      </div>
      <div className="boundary-box"><p>本轮真正的结构新增</p><span>{operatorCatalog.foundational_novelty.new_structural_capability}；由此得到运行时参数化的 {operatorCatalog.foundational_novelty.enabled_generic_operator}。</span></div>
      <div className="operator-discovery-grid">
        {operators.map((item) => <article className="metric-card" key={item.operator_id}>
          <p><code>{item.operator_id}</code></p><strong className="operator-name">{item.posthoc_name}</strong>
          <span>{item.domain_contract}</span><small>{item.classification}</small>
        </article>)}
      </div>
      <div className="boundary-box"><p>尚未晋级</p><span>通用除法、通用余数、整数根、对数与有理数字段：缺少必要结构依赖，未用有限拟合冒充发现。</span></div>
      <p className="digest-line">V5 内容摘要 <code>{operatorCatalog.content_digest}</code></p>
    </section>

    <section className="evidence-panel limitations-panel">
      <div className="section-heading"><div><p className="eyebrow">HONEST SCOPE</p><h2>9.99 是扩展符号基准分，不是通用智能分</h2></div></div>
      <ul>{benchmark.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      <p className="digest-line">内容摘要 <code>{benchmark.content_digest}</code></p>
    </section>
  </main>;
}
