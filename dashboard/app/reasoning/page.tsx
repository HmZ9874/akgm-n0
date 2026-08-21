import type { Metadata } from "next";
import reportData from "../../data/relation_growth_latest.json";

export const metadata: Metadata = {
  title: "关系思考实验 · AKGM-N0",
  description: "证据工作记忆、程序合成、反投机门控与关系验证。",
};

type Gate = {
  gate_id: string;
  actual: unknown;
  threshold: unknown;
  passed: boolean | null;
};

type EvidenceConstant = {
  value: number;
  derivation_depth: number;
  provenance: { op: string; left?: number; right?: number };
};

type Report = {
  run_id: string;
  created_at: string;
  title: string;
  verdict: string;
  knowledge_status: string;
  architecture: string;
  search: {
    programs_generated: number;
    programs_filtered_by_mistake_memory: number;
    evidence_derived_working_memory: EvidenceConstant[];
    selected_candidate: {
      candidate_id: string;
      program: Record<string, unknown>;
      program_nodes: number;
    };
  };
  relation_graph: {
    observed_members_in_discovered_chain: number[];
    direct_edges: Array<{ source: number; target: number }>;
  };
  post_hoc_evaluator_interpretation: {
    readable_formula: string;
    human_relation_graph: string;
  };
  success_formula_room_record: { room_record_id: string } | null;
  gates: Gate[];
  limitations: string[];
};

const report = reportData as Report;

function gateState(gate: Gate) {
  if (gate.passed === null) return { text: "待验证", className: "pending" };
  return gate.passed
    ? { text: "通过", className: "passed" }
    : { text: "未通过", className: "failed" };
}

export default function ReasoningPage() {
  const generatedAt = new Date(report.created_at).toLocaleString("zh-CN", { hour12: false });
  const constants = report.search.evidence_derived_working_memory;
  const selected = report.search.selected_candidate;

  return (
    <main>
      <header className="masthead">
        <div className="brand-lockup">
          <span className="brand-mark">R2</span>
          <div><p className="eyebrow">EVIDENCE REASONING</p><p className="brand-name">AKGM-N0 / 思考能力证据台</p></div>
        </div>
        <div className="run-meta"><a className="nav-link" href="/active">主动实验</a><a className="nav-link" href="/operation">运算生长</a><a className="nav-link" href="/mistakes">错题库</a><span className="meta-dot" /><span>{generatedAt}</span></div>
      </header>

      <section className="hero panel-grid">
        <div className="hero-copy">
          <div className="verdict-row"><span className="verdict-badge">有条件通过</span><span className="scope-label">知识状态 {report.knowledge_status}</span></div>
          <h1>从数字证据构造工作记忆</h1>
          <p className="lede">未提供常量 1、目标公式、顺序含义或乘法。系统从数字差异中产生记忆原子，再组合和验证可执行关系。</p>
          <div className="run-id"><span>RUN</span><code>{report.run_id}</code></div>
        </div>
        <div className="hero-signal compact-signal">
          <div className="signal-ring full-ring"><strong>{report.relation_graph.direct_edges.length}/6</strong><span>关系边通过</span></div>
          <p>输入逆序后仍选择同一程序</p>
        </div>
      </section>

      <section className="metric-grid">
        <article className="metric-card accent-cyan"><p>搜索程序</p><strong>{report.search.programs_generated}</strong><span>语义去重后候选</span></article>
        <article className="metric-card accent-violet"><p>工作记忆</p><strong>{constants.length}</strong><span>个证据派生原子</span></article>
        <article className="metric-card accent-amber"><p>完整关系链</p><strong>{report.relation_graph.observed_members_in_discovered_chain.length}</strong><span>个输入成员</span></article>
        <article className="metric-card accent-slate"><p>成功房间</p><strong className="status-word">已记录</strong><span>{report.success_formula_room_record?.room_record_id ?? "—"}</span></article>
      </section>

      <section className="content-grid operation-grid">
        <article className="surface concept-card">
          <div className="section-heading"><div><p className="eyebrow">DISCOVERED PROGRAM</p><h2>{selected.candidate_id}</h2></div><span className="evidence-chip">{selected.program_nodes} 节点</span></div>
          <pre className="code-block operation-code"><code>{JSON.stringify(selected.program, null, 2)}</code></pre>
          <div className="posthoc-note"><span>验证后可读式</span><strong>{report.post_hoc_evaluator_interpretation.readable_formula}</strong><small>{report.post_hoc_evaluator_interpretation.human_relation_graph}</small></div>
        </article>

        <article className="surface task-table-card">
          <div className="section-heading"><div><p className="eyebrow">WORKING MEMORY TRACE</p><h2>关键常量如何产生</h2></div></div>
          <div className="blind-table">
            {constants.filter((item) => Math.abs(item.value) <= 4).map((item) => (
              <div className="blind-row" key={`${item.value}-${item.derivation_depth}`}>
                <strong>{item.value}</strong><span>深度 {item.derivation_depth}</span><code>{item.provenance.left} − {item.provenance.right}</code><span className="zero-value">证据派生</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="surface gates-section">
        <div className="section-heading"><div><p className="eyebrow">EVIDENCE GATES</p><h2>思考链验证</h2></div><p className="section-note">错题记忆过滤 {report.search.programs_filtered_by_mistake_memory} 个候选</p></div>
        <div className="gate-grid">
          {report.gates.map((gate) => {
            const state = gateState(gate);
            return <div className="gate-item" key={gate.gate_id}><span className={`gate-light ${state.className}`} /><div><strong>{gate.gate_id}</strong><span>{state.text}</span></div></div>;
          })}
        </div>
      </section>

      <footer><div><span className="footer-mark">AKGM-N0</span><span>证据工作记忆 · 程序合成 · 非 Transformer</span></div><code>{report.architecture}</code></footer>
    </main>
  );
}
