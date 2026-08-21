import type { Metadata } from "next";
import reportData from "../../data/active_experiment_latest.json";

export const metadata: Metadata = {
  title: "主动实验研究 · AKGM-N0",
  description: "用一次数字实验区分竞争程序。",
};

type Report = {
  run_id: string;
  created_at: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  hypotheses_before_experiment: Array<{
    candidate_id: string;
    post_hoc_readable: string;
  }>;
  experiment_plan: {
    selected: {
      action: number;
      information_gain_bits: number;
      utility: number;
      prediction_groups: Array<{
        predicted_value: number;
        candidate_ids: string[];
      }>;
    };
  };
  numeric_feedback_update: {
    observed_value: number;
    retained_candidate_ids: string[];
    rejected_candidate_ids: string[];
    predictions: Array<{
      candidate_id: string;
      predicted_value: number;
      absolute_error: number;
    }>;
  };
  passive_action_baseline: {
    average_remaining_hypotheses: number;
    selected_action_remaining_hypotheses: number;
  };
  gates: Array<{ gate_id: string; passed: boolean | null }>;
  limitations: string[];
};

const report = reportData as Report;

export default function ActiveResearchPage() {
  const selected = report.experiment_plan.selected;
  const feedback = report.numeric_feedback_update;
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark">A2</span><div><p className="eyebrow">ACTIVE SCIENTIST</p><p className="brand-name">AKGM-N0 / 主动实验研究</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/semantic">空符号语义</a><a className="nav-link" href="/reasoning">关系思考</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">知识状态 {report.knowledge_status}</span></div>
          <h1>一次实验，排除四个错误程序</h1>
          <p className="lede">模型没有读取隐藏公式。它比较五个可执行程序在候选数字上的分歧，主动选择信息量最大的输入，只接收一个数字反馈。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{feedback.rejected_candidate_ids.length}/4</strong><span>错误候选排除</span></div><p>信息增益 {selected.information_gain_bits.toFixed(3)} bits</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>竞争假设</p><strong>{report.hypotheses_before_experiment.length}</strong><span>个可执行程序</span></article>
        <article className="metric-card accent-violet"><p>主动选择</p><strong>x = {selected.action}</strong><span>最大预测分歧</span></article>
        <article className="metric-card accent-amber"><p>数字反馈</p><strong>{feedback.observed_value}</strong><span>隐藏环境唯一返回值</span></article>
        <article className="metric-card accent-slate"><p>剩余假设</p><strong>{feedback.retained_candidate_ids.length}</strong><span>进入限定知识状态</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">HYPOTHESIS COMMITTEE</p><h2>实验前五个候选</h2></div></div>
          <div className="blind-table">
            {report.hypotheses_before_experiment.map((item) => {
              const prediction = feedback.predictions.find((entry) => entry.candidate_id === item.candidate_id);
              const retained = feedback.retained_candidate_ids.includes(item.candidate_id);
              return <div className="blind-row" key={item.candidate_id}><code>{item.post_hoc_readable}</code><span>预测 {prediction?.predicted_value}</span><span>误差 {prediction?.absolute_error}</span><span className={retained ? "zero-value" : "status-word"}>{retained ? "保留" : "拒绝"}</span></div>;
            })}
          </div>
        </article>

        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">RESEARCH RESULT</p><h2>这次新增的思考能力</h2></div></div>
          <dl className="receipt-list">
            <div><dt>实验选择</dt><dd>按预测分组熵，而非随机</dd></div>
            <div><dt>最大信息量</dt><dd>{selected.information_gain_bits.toFixed(6)} bits</dd></div>
            <div><dt>平均被动实验剩余</dt><dd>{report.passive_action_baseline.average_remaining_hypotheses.toFixed(2)} 个</dd></div>
            <div><dt>主动实验剩余</dt><dd>{report.passive_action_baseline.selected_action_remaining_hypotheses} 个</dd></div>
          </dl>
          <p className="concept-footnote">四个失败程序及数字反例已写入跨运行错题库；它们不会在相同条件下被等价重提。</p>
        </article>
      </section>

      <section className="surface gates-section">
        <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>验证门</h2></div></div>
        <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed === null ? "pending" : gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed === null ? "待迁移验证" : gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>竞争假设 · 信息增益 · 数字反馈 · 独立账本</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
