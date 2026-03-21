import ChatWidget from '../components/ChatWidget';

const AGENTS = [
  {
    icon: '🧠', name: 'Supervisor Agent', role: 'Orchestrator',
    color: 'rgba(59,130,246,0.12)', tagColor: '#3b82f6',
    desc: 'The entry point of every query. Uses Gemini LLM to classify intent and route to the single most appropriate specialist or the multi-agent planner.',
    tags: ['LLM Routing', 'Intent Classification', 'Gemini'],
    tagStyle: { background: 'rgba(59,130,246,0.1)', color: '#60a5fa' },
  },
  {
    icon: '📊', name: 'MSSQL Analyst', role: 'Market Data',
    color: 'rgba(245,158,11,0.12)', tagColor: '#f59e0b',
    desc: 'Queries the MSSQL CommodityPrices database. Handles financial trends, commodity pricing, historical fluctuations, volatility analysis, and spread calculations.',
    tags: ['MSSQL', 'Commodity Prices', 'SQL Agent'],
    tagStyle: { background: 'rgba(245,158,11,0.1)', color: '#fbbf24' },
  },
  {
    icon: '👤', name: 'MySQL Agent', role: 'User Intelligence',
    color: 'rgba(16,185,129,0.12)', tagColor: '#10b981',
    desc: 'Queries the MySQL user_db database. Handles user profiles, account details, subscription tiers, and engagement metrics.',
    tags: ['MySQL', 'User Profiles', 'Subscriptions'],
    tagStyle: { background: 'rgba(16,185,129,0.1)', color: '#34d399' },
  },
  {
    icon: '📚', name: 'RAG Researcher', role: 'Document Intelligence',
    color: 'rgba(139,92,246,0.12)', tagColor: '#8b5cf6',
    desc: 'Performs semantic search against ChromaDB to answer questions from uploaded PDFs, DOCX files, CSVs, and WordPress content. Great for policy, manual, and knowledge-base questions.',
    tags: ['ChromaDB', 'Vector Search', 'LangChain'],
    tagStyle: { background: 'rgba(139,92,246,0.1)', color: '#a78bfa' },
  },
  {
    icon: '🗺️', name: 'Planner Agent', role: 'Multi-Agent Coordinator',
    color: 'rgba(236,72,153,0.12)', tagColor: '#ec4899',
    desc: 'Receives complex cross-domain queries and decomposes them into a sequential JSON execution plan. Manages dependency injection between agents using {prev_result} placeholders.',
    tags: ['Multi-Agent', 'Planning', 'JSON Plans'],
    tagStyle: { background: 'rgba(236,72,153,0.1)', color: '#f472b6' },
  },
  {
    icon: '⚙️', name: 'Executor & Combiner', role: 'Orchestration',
    color: 'rgba(6,182,212,0.12)', tagColor: '#06b6d4',
    desc: 'The Executor runs each planned step in sequence, passing outputs as context. The Combiner synthesises all results into one coherent, structured answer.',
    tags: ['Execution', 'Synthesis', 'LangGraph'],
    tagStyle: { background: 'rgba(6,182,212,0.1)', color: '#22d3ee' },
  },
  {
    icon: '📈', name: 'Chart Agent', role: 'Visualization',
    color: 'rgba(249,115,22,0.12)', tagColor: '#f97316',
    desc: 'Analyses the final text answer and determines whether data is chartable. If so, it builds a professional matplotlib bar, line, or pie chart and returns a PNG buffer.',
    tags: ['Matplotlib', 'Auto-Viz', 'Data Export'],
    tagStyle: { background: 'rgba(249,115,22,0.1)', color: '#fb923c' },
  },
  {
    icon: '📄', name: 'Report Agent', role: 'Document Generation',
    color: 'rgba(168,85,247,0.12)', tagColor: '#a855f7',
    desc: 'Formats previous AI answers into downloadable structured reports available as PDF (ReportLab) or DOCX (python-docx). Triggered by keywords like "generate a report."',
    tags: ['PDF', 'DOCX', 'ReportLab'],
    tagStyle: { background: 'rgba(168,85,247,0.1)', color: '#c084fc' },
  },
];

const TECH = [
  { icon: '🦜', name: 'LangGraph', desc: 'Agent orchestration & routing graph' },
  { icon: '🤖', name: 'Gemini', desc: 'Google LLM for reasoning & planning' },
  { icon: '🗄️', name: 'ChromaDB', desc: 'Vector store for document retrieval' },
  { icon: '🔗', name: 'LangChain', desc: 'Chains, prompts & SQL toolkit' },
  { icon: '⚡', name: 'FastAPI', desc: 'Async REST API backend' },
  { icon: '⚛️', name: 'React + Vite', desc: 'Frontend SPA with instant HMR' },
  { icon: '🐬', name: 'MySQL', desc: 'User profile & subscription store' },
  { icon: '🏢', name: 'MSSQL', desc: 'Commodity pricing data warehouse' },
];

const FLOW = [
  { icon: '💬', label: 'User Query', sub: 'Natural language' },
  { arrow: true },
  { icon: '🧠', label: 'Supervisor', sub: 'Intent routing' },
  { arrow: true },
  { icon: '🗺️', label: 'Planner', sub: 'Multi-agent' },
  { arrow: true },
  { icon: '⚙️', label: 'Executor', sub: 'Runs agents' },
  { arrow: true },
  { icon: '📊', label: 'Combiner', sub: 'Synthesises' },
  { arrow: true },
  { icon: '📈', label: 'Chart Agent', sub: 'Visualise' },
  { arrow: true },
  { icon: '✅', label: 'Response', sub: 'Answer + chart' },
];

const nodeColors = {
  '💬': 'rgba(59,130,246,0.15)',
  '🧠': 'rgba(139,92,246,0.15)',
  '🗺️': 'rgba(236,72,153,0.15)',
  '⚙️': 'rgba(6,182,212,0.15)',
  '📊': 'rgba(245,158,11,0.15)',
  '📈': 'rgba(249,115,22,0.15)',
  '✅': 'rgba(16,185,129,0.15)',
};

export default function About() {
  return (
    <div>
      {/* ── About Hero ── */}
      <section className="about-hero">
        <div className="container">
          <span className="section-label">Agent Workforce</span>
          <h1 className="section-title" style={{ textAlign: 'center' }}>
            Meet the <span className="gradient-text">Intelligence Layer</span>
          </h1>
          <p className="section-sub" style={{ textAlign: 'center', margin: '0 auto' }}>
            Transgraph is not a single AI — it's a coordinated workforce of specialist agents, each
            owning a specific domain, working together to answer your most complex business questions.
          </p>
        </div>
      </section>

      {/* ── Architecture Flow ── */}
      <section className="arch-section">
        <div className="container">
          <span className="section-label">System Architecture</span>
          <h2 className="section-title">How agents <span className="gradient-text">flow together</span></h2>
          <div className="arch-flow">
            {FLOW.map((node, i) =>
              node.arrow ? (
                <div key={i} className="arch-arrow">→</div>
              ) : (
                <div key={i} className="arch-node" style={{ background: nodeColors[node.icon] || 'transparent', borderRadius: 12 }}>
                  <div className="arch-node-icon">{node.icon}</div>
                  <div className="arch-node-label">{node.label}</div>
                  <div className="arch-node-sub">{node.sub}</div>
                </div>
              )
            )}
          </div>
        </div>
      </section>

      {/* ── Agent Cards ── */}
      <section className="about-agents-section">
        <div className="container">
          <span className="section-label">Specialist Agents</span>
          <h2 className="section-title">Every agent, <span className="gradient-text">explained</span></h2>
          <div className="about-agents-grid">
            {AGENTS.map(a => (
              <div key={a.name} className="about-agent-card">
                <div className="about-agent-icon" style={{ background: a.color }}>{a.icon}</div>
                <h3>{a.name}</h3>
                <span className="agent-tag" style={{ ...a.tagStyle, marginBottom: 12, display: 'inline-block' }}>{a.role}</span>
                <p>{a.desc}</p>
                <div className="tags">
                  {a.tags.map(t => (
                    <span key={t} className="tag" style={a.tagStyle}>{t}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Tech Stack ── */}
      <section className="tech-stack-section">
        <div className="container">
          <span className="section-label">Technology Stack</span>
          <h2 className="section-title">Built on <span className="gradient-text">proven foundations</span></h2>
          <div className="tech-grid">
            {TECH.map(t => (
              <div key={t.name} className="tech-card">
                <div className="tech-icon">{t.icon}</div>
                <div className="tech-name">{t.name}</div>
                <div className="tech-desc">{t.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer>
        <div className="footer">
          <p className="footer-text">© 2025 Transgraph · Multi-Agent Commodity Risk Platform</p>
          <div className="footer-links">
            <a href="/">Home</a>
          </div>
        </div>
      </footer>

      <ChatWidget />
    </div>
  );
}
