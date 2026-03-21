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
