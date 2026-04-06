import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE_URL });

/** Send a chat message and receive AI response */
export async function sendChat(query, sessionId = 'default') {
  const { data } = await api.post('/api/chat', { query, session_id: sessionId });
  return data; // { answer, route, chart_b64, report_text }
}

/** Upload one or more files into the RAG vector store */
export async function uploadFiles(files) {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  const { data } = await api.post('/api/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data; // { injected, failed, total_docs }
}

/** Inject files from a Google Drive folder URL */
export async function injectFromDrive(url) {
  const { data } = await api.post('/api/drive', { url });
  return data; // { injected, total_docs }
}

/** Clear the current chat session */
export async function clearChat(sessionId = 'default') {
  await api.delete(`/api/chat/${sessionId}`);
}

/** Get WordPress sync status */
export async function getStatus() {
  const { data } = await api.get('/api/status');
  return data; // { wordpress_connected, last_sync }
}

/** Get list of uploaded documents */
export async function getUploadedDocs() {
  const { data } = await api.get('/api/docs');
  return data.docs;
}

/** Delete a single document from the knowledge base */
export async function deleteDoc(filename) {
  const { data } = await api.delete(`/api/docs/${encodeURIComponent(filename)}`);
  return data; // { status, filename, remaining_docs }
}

/** Clear all uploaded documents from the knowledge base */
export async function clearAllDocs() {
  const { data } = await api.delete('/api/docs');
  return data; // { status: "cleared" }
}

/** Download a report as PDF or DOCX (triggers browser file save) */
export async function downloadReport(reportText, format = 'pdf', chartB64 = null) {
  const res = await api.post('/api/report', {
    report_text: reportText,
    format,
    chart_b64: chartB64,
  }, { responseType: 'blob' });

  const ext  = format === 'docx' ? 'docx' : 'pdf';
  const mime = format === 'docx'
    ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    : 'application/pdf';

  const blob = new Blob([res.data], { type: mime });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `transgraph_report.${ext}`;
  link.click();
  URL.revokeObjectURL(link.href);
}
// Add this to your existing api.js

/**
 * AG-UI protocol streaming chat.
 * Calls /api/agui and returns an async generator of parsed events.
 */
export async function* streamAgUI(query, sessionId = 'default') {
  const response = await fetch(
    `${BASE_URL}/api/agui`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        thread_id: sessionId,
        messages: [{ role: 'user', content: query }],
        // AG-UI RunAgentInput required fields
        run_id: crypto.randomUUID(),
        forwarded_props: {},
        context: [],
        tools: [],
        state: null,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(`AG-UI endpoint error: ${response.status}`);
  }

  const reader  = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer    = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep last incomplete line

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const raw = line.slice(6).trim();
      if (!raw || raw === '[DONE]') continue;
      try {
        yield JSON.parse(raw);
      } catch {
        // skip malformed lines
      }
    }
  }
}