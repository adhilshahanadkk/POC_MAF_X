import { useState, useRef, useEffect, useCallback } from 'react';
import { sendChat, uploadFiles, injectFromDrive, clearChat, downloadReport, deleteDoc, clearAllDocs } from '../api';

const SESSION_ID = 'user-' + Math.random().toString(36).slice(2, 10);

// ── Small helper SVGs ────────────────────────────────────────────────────────
const IconChat = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);
const IconClose = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
    strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconSend = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5"
    strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>
);
const IconAttach = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
    <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
  </svg>
);
const IconDrive = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
    <polyline points="16 16 12 12 8 16"/>
    <path d="M12 12v9"/>
    <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
    <polyline points="16 16 12 12 8 16"/>
  </svg>
);
const IconTrash = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
    strokeLinecap="round" strokeLinejoin="round" width="16" height="16">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
    <path d="M10 11v6"/><path d="M14 11v6"/>
  </svg>
);
const IconArrowDown = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
    strokeLinecap="round" strokeLinejoin="round" width="18" height="18">
    <polyline points="6 9 12 15 18 9"/>
  </svg>
);

// ── Markdown-lite renderer (bold, code, newlines, **tables**) ────────────────
function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, j) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={j}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={j} style={{ background: 'rgba(59,130,246,0.15)', padding: '1px 5px', borderRadius: 4, fontSize: '0.8em' }}>{part.slice(1, -1)}</code>;
    return part;
  });
}

function isTableRow(line) {
  const t = line.trim();
  return t.startsWith('|') && t.endsWith('|') && t.includes('|');
}
function isSeparator(line) {
  return /^\|[\s:?-]+(\|[\s:?-]+)+\|$/.test(line.trim());
}
function parseCells(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
}

// ── Metadata footer detector ─────────────────────────────────────────────────
const META_PATTERNS = [
  { key: 'database', regex: /^Database:\s*(.+)/i, icon: '🗄️', label: 'Database' },
  { key: 'table',    regex: /^Table:\s*(.+)/i,    icon: '📋', label: 'Table' },
  { key: 'timestamp',regex: /^Timestamp:\s*(.+)/i,icon: '🕐', label: 'Timestamp' },
];

function extractMetaFooter(lines) {
  const meta = {};
  let cutIndex = lines.length;

  // Scan from the end to find metadata lines
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 6); i--) {
    const trimmed = lines[i].trim();
    if (!trimmed) continue;
    let matched = false;
    for (const pat of META_PATTERNS) {
      const m = trimmed.match(pat.regex);
      if (m) {
        meta[pat.key] = { value: m[1].trim(), icon: pat.icon, label: pat.label };
        cutIndex = Math.min(cutIndex, i);
        matched = true;
        break;
      }
    }
    if (!matched && Object.keys(meta).length > 0) break;
  }

  if (Object.keys(meta).length === 0) return { bodyLines: lines, meta: null };

  // Remove trailing empty lines before the metadata block
  let end = cutIndex;
  while (end > 0 && !lines[end - 1].trim()) end--;

  return { bodyLines: lines.slice(0, end), meta };
}

function renderText(text) {
  if (!text) return null;
  const lines = text.split('\n');
  const { bodyLines, meta } = extractMetaFooter(lines);
  const elements = [];
  let i = 0;

  while (i < bodyLines.length) {
    // Detect a markdown table block
    if (isTableRow(bodyLines[i]) && i + 1 < bodyLines.length && isSeparator(bodyLines[i + 1])) {
      const headers = parseCells(bodyLines[i]);
      i += 2; // skip header + separator
      const rows = [];
      while (i < bodyLines.length && isTableRow(bodyLines[i]) && !isSeparator(bodyLines[i])) {
        rows.push(parseCells(bodyLines[i]));
        i++;
      }
      elements.push(
        <div key={`tbl-${i}`} className="msg-table-wrap">
          <table className="msg-table">
            <thead>
              <tr>{headers.map((h, hi) => <th key={hi}>{renderInline(h)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri}>{row.map((cell, ci) => <td key={ci}>{renderInline(cell)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    } else {
      elements.push(
        <span key={`ln-${i}`}>{renderInline(bodyLines[i])}{i < bodyLines.length - 1 && <br />}</span>
      );
      i++;
    }
  }

  // Render metadata footer with icons
  if (meta) {
    elements.push(
      <div key="meta-footer" className="msg-meta-footer">
        <div className="msg-meta-divider" />
        {META_PATTERNS.map(pat => meta[pat.key] ? (
          <div key={pat.key} className="msg-meta-row">
            <span className="msg-meta-icon">{meta[pat.key].icon}</span>
            <span className="msg-meta-label">{meta[pat.key].label}:</span>
            <span className="msg-meta-value">{meta[pat.key].value}</span>
          </div>
        ) : null)}
      </div>
    );
  }

  return elements;
}

// ── Route badge colour map ───────────────────────────────────────────────────
const routeColour = {
  mysql_agent:   ['#10b981', 'rgba(16,185,129,0.12)'],
  mssql_agent:   ['#f59e0b', 'rgba(245,158,11,0.12)'],
  rag_agent:     ['#8b5cf6', 'rgba(139,92,246,0.12)'],
  report_agent:  ['#06b6d4', 'rgba(6,182,212,0.12)'],
  multi_agent:   ['#ec4899', 'rgba(236,72,153,0.12)'],
  planner:       ['#ec4899', 'rgba(236,72,153,0.12)'],
};

export default function ChatWidget() {
  const [open, setOpen]           = useState(false);
  const [messages, setMessages]   = useState([
    { role: 'ai', text: "Hi! I'm **Transgraph AI**, your commodity risk intelligence assistant."}
  ]);
  const [input, setInput]         = useState('');
  const [pendingCount, setPendingCount] = useState(0);
  const [showDrive, setShowDrive] = useState(false);
  const [driveUrl, setDriveUrl]   = useState('');
  const [uploadedDocs, setUploadedDocs] = useState([]);
  const [uploadStatus, setUploadStatus] = useState('');
  const [zoomedChart, setZoomedChart]   = useState(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const fileInputRef  = useRef(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const textareaRef   = useRef(null);

  // Clear old docs on page load/reload — each session starts fresh
  useEffect(() => {
    clearAllDocs().catch(() => {});
  }, []);

  // Auto-scroll to bottom (only when user is already near bottom)
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150;
    if (isNearBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, pendingCount]);

  // Track scroll position to show/hide scroll-to-bottom button
  const handleMessagesScroll = useCallback(() => {
    const container = messagesContainerRef.current;
    if (!container) return;
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    setShowScrollBtn(distanceFromBottom > 100);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  // Auto-resize textarea
  const handleInputChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  // ── Send chat message ──────────────────────────────────────────────────────
  const handleSend = async () => {
    const q = input.trim();
    if (!q) return;
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setMessages(prev => [...prev, { role: 'user', text: q }]);
    setPendingCount(c => c + 1);
    try {
      const res = await sendChat(q, SESSION_ID);
      setMessages(prev => [...prev, {
        role: 'ai',
        text: res.answer,
        route: res.route,
        chart: res.chart_b64 ? `data:image/png;base64,${res.chart_b64}` : null,
        reportText: res.report_text || null,
        chartB64: res.chart_b64 || null,
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `⚠️ Error: ${err?.response?.data?.detail || err.message || 'Could not reach the server.'}`,
      }]);
    } finally {
      setPendingCount(c => c - 1);
    }
  };

  // ── Keyboard shortcut: Enter to send, Shift+Enter for newline ─────────────
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  // ── File upload ────────────────────────────────────────────────────────────
  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploadStatus(`Uploading ${files.length} file(s)...`);
    try {
      const res = await uploadFiles(files);
      setUploadedDocs(res.total_docs || []);
      setUploadStatus(`✓ Injected: ${res.injected.join(', ')}`);
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `📄 Successfully injected **${res.injected.length}** document(s) into the knowledge base:\n${res.injected.map(d => `• ${d}`).join('\n')}`,
      }]);
    } catch (err) {
      setUploadStatus('Upload failed. Please try again.');
    }
    e.target.value = '';
  };

  // ── Google Drive inject ────────────────────────────────────────────────────
  const handleDriveInject = async () => {
    if (!driveUrl.trim()) {
      setUploadStatus('⚠️ Please paste a Google Drive folder URL first.');
      setTimeout(() => setUploadStatus(''), 3000);
      return;
    }
    setUploadStatus('Fetching from Google Drive...');
    try {
      const res = await injectFromDrive(driveUrl.trim());
      setUploadedDocs(res.total_docs || []);
      setUploadStatus(`✓ Drive: ${res.injected.join(', ')}`);
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `☁️ Successfully loaded **${res.injected.length}** file(s) from Google Drive:\n${res.injected.map(d => `• ${d}`).join('\n')}`,
      }]);
      setDriveUrl('');
      setShowDrive(false);
    } catch (err) {
      setUploadStatus(`Drive failed: ${err?.response?.data?.detail || err.message}`);
    }
  };

  // ── Clear chat ─────────────────────────────────────────────────────────────
  const handleClear = async () => {
    await clearChat(SESSION_ID).catch(() => {});
    setMessages([{
      role: 'ai',
      text: "Chat cleared. How can I help you today? 😊",
    }]);
    setUploadStatus('');
    setUploadedDocs([]);
  };

  // ── Delete a single document ───────────────────────────────────────────────
  const handleDeleteDoc = async (filename) => {
    try {
      const res = await deleteDoc(filename);
      setUploadedDocs(res.remaining_docs || []);
      setUploadStatus(`🗑️ Removed: ${filename}`);
      setMessages(prev => [...prev, {
        role: 'ai',
        text: `🗑️ Document **${filename}** has been removed from the knowledge base.`,
      }]);
      setTimeout(() => setUploadStatus(''), 3000);
    } catch (err) {
      setUploadStatus(`⚠️ Failed to delete: ${err?.response?.data?.detail || err.message}`);
      setTimeout(() => setUploadStatus(''), 4000);
    }
  };

  // ── Clear all documents ────────────────────────────────────────────────────
  const handleClearAllDocs = async () => {
    try {
      await clearAllDocs();
      setUploadedDocs([]);
      setUploadStatus('🗑️ All documents removed.');
      setMessages(prev => [...prev, {
        role: 'ai',
        text: '🗑️ All documents have been removed from the knowledge base.',
      }]);
      setTimeout(() => setUploadStatus(''), 3000);
    } catch (err) {
      setUploadStatus(`⚠️ Failed to clear: ${err?.response?.data?.detail || err.message}`);
      setTimeout(() => setUploadStatus(''), 4000);
    }
  };

  return (
    <>
      {/* ── Floating trigger button ── */}
      <button
        className="chat-trigger"
        onClick={() => setOpen(v => !v)}
        aria-label="Open chat assistant"
        title="Chat with Transgraph AI"
      >
        {open
          ? <IconClose />
          : (
            <svg viewBox="0 0 24 24" fill="white" width="24" height="24">
              <path d="M20 2H4C2.9 2 2 2.9 2 4v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z"/>
            </svg>
          )
        }
      </button>

      {/* ── Chat window ── */}
      {open && (
        <div className="chat-window">
          {/* Header */}
          <div className="chat-header">
            <div className="chat-header-avatar">
              🤖
              <div className="online-dot" />
            </div>
            <div className="chat-header-info">
              <h3>Transgraph AI</h3>
              <p>Multi-Agent Risk Intelligence • Online</p>
            </div>
            <button className="input-action chat-header-close" onClick={handleClear} title="Clear chat">
              <IconTrash />
            </button>
            <button className="input-action chat-header-close" onClick={() => setOpen(false)} title="Close">
              <IconClose />
            </button>
          </div>

          {/* Messages */}
          <div className="chat-messages" ref={messagesContainerRef} onScroll={handleMessagesScroll}>
            {messages.map((msg, i) => (
              <div key={i} className={`msg-row ${msg.role === 'user' ? 'user-row' : ''}`}>
                <div className={`msg-avatar ${msg.role === 'ai' ? 'ai-av' : 'user-av'}`}>
                  {msg.role === 'ai' ? '🤖' : '👤'}
                </div>
                <div>
                  <div className={`msg-bubble ${msg.role === 'ai' ? 'ai-bubble' : 'user-bubble'}`}>
                    {renderText(msg.text)}
                    {msg.chart && (
                      <div className="msg-chart" onClick={() => setZoomedChart(msg.chart)}>
                        <img src={msg.chart} alt="Data visualization" />
                      </div>
                    )}
                    {msg.route && routeColour[msg.route] && (
                      <div className="route-badge" style={{
                        color: routeColour[msg.route][0],
                        background: routeColour[msg.route][1],
                        borderColor: routeColour[msg.route][0] + '40',
                      }}>
                        {msg.route.replace('_', ' ')}
                      </div>
                    )}
                    {msg.reportText && (
                      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                        <button
                          className="drive-inject-btn"
                          onClick={() => downloadReport(msg.reportText, 'pdf', msg.chartB64)}
                        >
                          ⬇ PDF Report
                        </button>
                        <button
                          className="drive-inject-btn"
                          onClick={() => downloadReport(msg.reportText, 'docx', msg.chartB64)}
                        >
                          ⬇ DOCX Report
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {pendingCount > 0 && (
              <div className="msg-row">
                <div className="msg-avatar ai-av">🤖</div>
                <div className="typing-bubble">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
            {showScrollBtn && (
              <button
                className="scroll-to-bottom-btn"
                onClick={scrollToBottom}
                aria-label="Scroll to bottom"
                title="Scroll to bottom"
              >
                <IconArrowDown />
              </button>
            )}
          </div>

          {/* Input area */}
          <div className="chat-input-area">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.csv,.xlsx,.txt,.md,.png,.jpg,.jpeg"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />

            {/* Drive URL row */}
            {showDrive && (
              <div className="drive-input-row">
                <input
                  type="url"
                  placeholder="Paste Google Drive folder URL..."
                  value={driveUrl}
                  onChange={e => setDriveUrl(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleDriveInject()}
                />
                <button className="drive-inject-btn" onClick={handleDriveInject}>
                  Inject
                </button>
                <button
                  className="input-action"
                  onClick={() => { setShowDrive(false); setDriveUrl(''); }}
                  title="Close"
                  style={{ padding: 4 }}
                >
                  <IconClose />
                </button>
              </div>
            )}

            {/* Main input row */}
            <div className="input-row">
              <textarea
                ref={textareaRef}
                rows={1}
                placeholder="Ask anything..."
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
              />

              {/* Attach files */}
              <button
                className="input-action"
                onClick={() => fileInputRef.current?.click()}
                title="Upload document (PDF, DOCX, CSV, XLSX, image)"
              >
                <IconAttach />
              </button>

              {/* Google Drive */}
              <button
                className="input-action"
                onClick={() => setShowDrive(v => !v)}
                title="Inject from Google Drive folder"
                style={{ color: showDrive ? 'var(--accent-blue)' : undefined }}
              >
                <IconDrive />
              </button>

              {/* Send */}
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!input.trim()}
                title="Send message"
              >
                <IconSend />
              </button>
            </div>

            {uploadStatus && (
              <p className="upload-status" style={uploadStatus.startsWith('⚠') ? { color: '#ef4444', fontWeight: 600 } : undefined}>{uploadStatus}</p>
            )}
            {uploadedDocs.length > 0 && (
              <div className="active-docs-list">
                <div className="active-docs-header">
                  <span className="active-docs-label">📚 Active docs:</span>
                  {uploadedDocs.length >= 2 && (
                    <button className="clear-all-btn" onClick={handleClearAllDocs} title="Remove all documents">
                      Clear All
                    </button>
                  )}
                </div>
                <div className="active-docs-chips">
                  {uploadedDocs.map((doc) => (
                    <span key={doc} className="doc-chip">
                      <span className="doc-chip-name">{doc}</span>
                      <button
                        className="doc-chip-delete"
                        onClick={() => handleDeleteDoc(doc)}
                        title={`Remove ${doc}`}
                        aria-label={`Remove ${doc}`}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Fullscreen chart overlay */}
      {zoomedChart && (
        <div className="chart-overlay active" onClick={() => setZoomedChart(null)}>
          <img src={zoomedChart} alt="Zoomed chart" />
        </div>
      )}
    </>
  );
}
