import ChatWidget from '../components/ChatWidget';

const AGENTS = [
  { icon: '🧠', name: 'Supervisor', desc: 'High-level intent classifier. Routes your query to the right specialist using Gemini LLM.', tag: 'Orchestrator', color: 'rgba(59,130,246,0.12)', tagColor: '#3b82f6' },
  { icon: '📊', name: 'MSSQL Analyst', desc: 'Queries commodity prices, financial trends, and historical market data from the MSSQL warehouse.', tag: 'Market Data', color: 'rgba(245,158,11,0.12)', tagColor: '#f59e0b' },
  { icon: '👤', name: 'MySQL Agent', desc: 'Handles user profiles, account details, and subscription status from the MySQL user database.', tag: 'User Data', color: 'rgba(16,185,129,0.12)', tagColor: '#10b981' },
  { icon: '📚', name: 'RAG Researcher', desc: 'Retrieves context from uploaded documents, PDFs, and WordPress content using ChromaDB vector search.', tag: 'Documents', color: 'rgba(139,92,246,0.12)', tagColor: '#8b5cf6' },
  { icon: '🗺️', name: 'Planner', desc: 'Decomposes complex cross-domain queries into a sequential execution plan for multiple agents.', tag: 'Multi-Agent', color: 'rgba(236,72,153,0.12)', tagColor: '#ec4899' },
  { icon: '📈', name: 'Chart Agent', desc: 'Automatically extracts numerical data from AI answers and renders professional visualizations.', tag: 'Visualization', color: 'rgba(6,182,212,0.12)', tagColor: '#06b6d4' },
];

const STEPS = [
  { num: '01', icon: '🎯', iconClass: 'blue', title: 'Ask Anything', desc: 'Type your query in plain English — prices, user data, policies, or cross-domain comparisons.' },
  { num: '02', icon: '⚡', iconClass: 'cyan', title: 'Agents Collaborate', desc: 'The Supervisor routes to specialists. For complex queries, the Planner orchestrates multiple agents in sequence.' },
  { num: '03', icon: '📊', iconClass: 'purple', title: 'Insight Delivered', desc: 'A synthesized, structured answer is returned — often with an auto-generated chart for numerical data.' },
];

export default function Landing() {
  return (
    <div>
      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-inner">
          <div>
            <div className="hero-badge">
              <span>⚡</span> Multi-Agent AI Platform
            </div>
            <h1 className="hero-title">
              Commodity Risk<br />
              <span className="gradient-text">Intelligence,</span><br />
              Reimagined.
            </h1>
            <p className="hero-sub">
              Transgraph is a next-generation multi-agent AI system that unifies structured databases,
              document knowledge bases, and real-time market data — answering complex business queries
              in seconds.
            </p>
            <div className="hero-actions">
              <button
                className="btn-primary"
                onClick={() => document.querySelector('.chat-trigger')?.click()}
              >
                Launch Chat →
              </button>
              <a className="btn-outline" href="/about">Explore Agents</a>
            </div>
          </div>

          {/* Right side — dashboard preview */}
          <div className="hero-visual">
            <div className="hero-dashboard">
              <div className="dashboard-header">
                <div className="dot dot-red" />
                <div className="dot dot-yellow" />
                <div className="dot dot-green" />
                <div className="dashboard-title-bar">transgraph.ai — Risk Intelligence</div>
              </div>

              <div className="chat-preview">
                <div className="chat-bubble">
                  <div className="bubble-avatar ai">🤖</div>
                  <div className="bubble-text ai">
                    Gold is up <strong>2.3%</strong> this week. 17 premium subscribers are actively tracking it.
                  </div>
                </div>
                <div className="chat-bubble user">
                  <div className="bubble-avatar user-av">👤</div>
                  <div className="bubble-text user-msg">
                    Compare wheat prices with user subscription tiers
                  </div>
                </div>
                <div className="chat-bubble">
                  <div className="bubble-avatar ai">🤖</div>
                  <div className="bubble-text ai">
                    Running multi-agent analysis across MSSQL + MySQL…
                  </div>
                </div>
                <div className="chat-bubble">
                  <div className="bubble-avatar ai">🤖</div>
                  <div className="typing-indicator">
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                  </div>
                </div>
              </div>

              <div className="stats-row">
                <div className="stat-item">
                  <div className="stat-value">7</div>
                  <div className="stat-label">AI Agents</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">3</div>
                  <div className="stat-label">Data Sources</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">&lt;2s</div>
                  <div className="stat-label">Response Time</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="section" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="container">
          <span className="section-label">How It Works</span>
          <h2 className="section-title">Three steps to <span className="gradient-text">deep insight</span></h2>
          <p className="section-sub">
            From natural language question to structured, visualised answer — powered by a coordinated
            workforce of specialist AI agents.
          </p>
          <div className="steps-grid">
            {STEPS.map(s => (
              <div key={s.num} className="step-card">
                <p className="step-number">STEP {s.num}</p>
                <div className={`step-icon ${s.iconClass}`}>{s.icon}</div>
                <h3 className="step-title">{s.title}</h3>
                <p className="step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Agent Workforce ── */}
      <section className="section" style={{ paddingTop: 40 }}>
        <div className="container">
          <span className="section-label">Agent Workforce</span>
          <h2 className="section-title">Meet your <span className="gradient-text">AI team</span></h2>
          <p className="section-sub">
            Each agent is a specialist. Together, they tackle queries no single model could answer alone.
          </p>
          <div className="agents-grid">
            {AGENTS.map(a => (
              <div key={a.name} className="agent-card">
                <div className="agent-icon" style={{ background: a.color }}>{a.icon}</div>
                <div className="agent-info">
                  <h3>{a.name}</h3>
                  <p>{a.desc}</p>
                  <span className="agent-tag" style={{ background: a.color, color: a.tagColor }}>
                    {a.tag}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section style={{ padding: '80px 0', position: 'relative', zIndex: 1 }}>
        <div className="container">
          <div style={{
            background: 'linear-gradient(135deg, rgba(59,130,246,0.15), rgba(139,92,246,0.1))',
            border: '1px solid rgba(59,130,246,0.2)',
            borderRadius: 'var(--radius-lg)',
            padding: '60px 48px',
            textAlign: 'center',
          }}>
            <h2 style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: 'clamp(1.6rem,3vw,2.4rem)', fontWeight: 800, marginBottom: 16 }}>
              Ready to query your data with <span className="gradient-text">AI intelligence?</span>
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 32, maxWidth: 480, margin: '0 auto 32px' }}>
              Open the chat assistant and ask anything — from commodity price trends to cross-database analysis.
            </p>
            <button
              className="btn-primary"
              style={{ fontSize: '1rem', padding: '12px 32px' }}
              onClick={() => document.querySelector('.chat-trigger')?.click()}
            >
              Start Chatting →
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer>
        <div className="footer">
          <p className="footer-text">© 2025 Transgraph · Multi-Agent Commodity Risk Platform</p>
          <div className="footer-links">
            <a href="/about">About</a>
          </div>
        </div>
      </footer>

      {/* Floating Chat Widget */}
      <ChatWidget />
    </div>
  );
}
