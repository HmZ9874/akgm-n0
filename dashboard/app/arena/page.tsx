import type { Metadata } from "next";
import reportData from "../../data/keyboard_arena_latest.json";

export const metadata: Metadata = {
  title: "键盘符号竞技场 · AKGM-N0",
  description: "全部键盘标点空槽与验证优先的程序约简奖励。",
};

type Ranking = {
  rank: number;
  candidate_id: string;
  verified: boolean;
  passed_case_count: number;
  case_count: number;
  original_node_count: number;
  reduced_node_count: number;
  reduction_gain: number;
  description_cost: number;
  reward: number;
};

type Report = {
  run_id: string;
  created_at: string;
  knowledge_status: string;
  architecture: string;
  symbol_arena: {
    glyph_count: number;
    glyphs: string[];
    all_initially_unbound: boolean;
    chosen_glyph: string;
    remaining_unbound_count: number;
    binding: { operation_id: string };
  };
  search: {
    programs_generated: number;
    programs_filtered_by_mistake_memory: number;
    verified_candidate_count: number;
    scored_candidate_count: number;
  };
  reward_ranking: Ranking[];
  winner: {
    source_candidate_id: string;
    chosen_glyph: string;
    operation_id: string;
    probe: { input: number[]; output: number };
    score: Ranking;
  };
  glyph_order_ablation: {
    normal_order_glyph: string;
    reversed_order_glyph: string;
    same_operation_id: boolean;
    same_output: boolean;
  };
  gates: Array<{ gate_id: string; passed: boolean | null }>;
};

const report = reportData as Report;

export default function ArenaPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const winner = report.winner;

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup"><span className="brand-mark">32</span><div><p className="eyebrow">KEYBOARD SEMANTIC ARENA</p><p className="brand-name">AKGM-N0 / 全符号竞技场</p></div></div>
        <div className="run-meta"><a className="nav-link" href="/indexed">有序关系</a><a className="nav-link" href="/semantic">空符号实验</a><a className="nav-link" href="/active">主动实验</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">{report.knowledge_status}</span></div>
          <h1>先验证，再让最短程序获得符号</h1>
          <p className="lede">32 个可打印键盘标点全部从空语义开始。错误程序没有资格参与压缩竞赛；在全部验证通过的候选中，描述更短、常量更少、执行更省者奖励更高。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal"><div className="signal-ring full-ring"><strong>{winner.chosen_glyph}</strong><span>本轮获胜空槽</span></div><p>{winner.operation_id}</p></div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>开放符号</p><strong>{report.symbol_arena.glyph_count}</strong><span>全部初始未绑定</span></article>
        <article className="metric-card accent-violet"><p>搜索程序</p><strong>{report.search.programs_generated.toLocaleString()}</strong><span>4 个旧错误被过滤</span></article>
        <article className="metric-card accent-amber"><p>奖励资格</p><strong>{report.search.verified_candidate_count}</strong><span>个全验证候选</span></article>
        <article className="metric-card accent-slate"><p>剩余空槽</p><strong>{report.symbol_arena.remaining_unbound_count}</strong><span>等待新语义</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">OPEN GLYPHS</p><h2>所有字形均无预设含义</h2></div><span className="evidence-chip">{report.symbol_arena.glyph_count} slots</span></div>
          <pre className="code-block"><code>{report.symbol_arena.glyphs.join("  ")}</code></pre>
          <dl className="receipt-list">
            <div><dt>获胜字形</dt><dd>{winner.chosen_glyph}</dd></div>
            <div><dt>候选程序</dt><dd>{winner.source_candidate_id}</dd></div>
            <div><dt>描述成本</dt><dd>{winner.score.description_cost.toFixed(6)}</dd></div>
            <div><dt>奖励</dt><dd>{winner.score.reward.toFixed(6)}</dd></div>
            <div><dt>探针</dt><dd>[{winner.probe.input.join(", ")}] → {winner.probe.output}</dd></div>
          </dl>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">MDL REWARD RANKING</p><h2>候选奖励榜</h2></div></div>
          <div className="blind-table">
            {report.reward_ranking.map((item) => <div className="blind-row" key={item.candidate_id}><strong>#{item.rank}</strong><code>{item.candidate_id}</code><span>{item.reduced_node_count} 节点 / {item.reward.toFixed(2)}</span><span className={item.verified ? "zero-value" : "status-word"}>{item.verified ? "有资格" : "无资格"}</span></div>)}
          </div>
        </article>
      </section>

      <section className="content-grid lower-grid">
        <article className="surface limitations-card">
          <div className="section-heading"><div><p className="eyebrow">GLYPH ORDER ABLATION</p><h2>符号顺序不改变程序</h2></div></div>
          <dl className="receipt-list">
            <div><dt>正常顺序选择</dt><dd>{report.glyph_order_ablation.normal_order_glyph}</dd></div>
            <div><dt>反向顺序选择</dt><dd>{report.glyph_order_ablation.reversed_order_glyph}</dd></div>
            <div><dt>操作编号一致</dt><dd>{report.glyph_order_ablation.same_operation_id ? "是" : "否"}</dd></div>
            <div><dt>执行结果一致</dt><dd>{report.glyph_order_ablation.same_output ? "是" : "否"}</dd></div>
          </dl>
        </article>

        <article className="surface gates-section">
          <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>竞技场验证门</h2></div></div>
          <div className="gate-grid">{report.gates.map((gate) => <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${gate.passed === null ? "pending" : gate.passed ? "passed" : "failed"}`} /><div><strong>{gate.gate_id}</strong><span>{gate.passed === null ? "待多操作增长" : gate.passed ? "通过" : "未通过"}</span></div></div>)}</div>
        </article>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>32 空槽 · 正确性硬门 · 程序约简奖励</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
