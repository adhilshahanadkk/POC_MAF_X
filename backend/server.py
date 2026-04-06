"""
server.py
──────────
Single-file FastAPI backend for Transgraph.
Imports the existing agent workflow directly — no intermediate packages.

Run with:
    uvicorn backend.server:app --reload --port 8000
"""

import os
import io
import re
import sys
import json
import shutil
import base64
import tempfile

from io import BytesIO
from typing import List

import gdown
from google import genai
from google.genai import types

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from fastapi import Request
from ag_ui.core import RunAgentInput

# ── Ensure project root is on sys.path ────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)  # so relative paths (data/, chroma_db/) resolve correctly

from graph.workflow import build_graph
from agents.rag_agents.rag_agent import RAGAgent
from agents.agui_runner import run_agui_stream
from config.settings import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_API_KEY,
    PRIMARY_MODEL,
    VM_BASE_URL
)
from backend.report_generator import generate_pdf, generate_docx


# ═══════════════════════════════════════════════════════════════════════════════
# App & CORS
# ═══════════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="Transgraph Commodity Risk API",
    description="Multi-agent LangGraph backend for commodity risk management.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════════════════════
# Shared State  (singletons — replaces the old backend/rag_state.py)
# ═══════════════════════════════════════════════════════════════════════════════
_graph = None
_rag_agent: RAGAgent | None = None
_uploaded_doc_names: list[str] = []
_sessions: dict[str, dict] = {}        # session_id → memory dict

SAVE_DIR   = "data/docs"
CHROMA_DIR = "chroma_db"


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def get_rag():
    return _rag_agent


def rebuild_rag():
    global _rag_agent
    _rag_agent = RAGAgent(data_path="data")
    return _rag_agent


def get_session(sid: str) -> dict:
    if sid not in _sessions:
        _sessions[sid] = {"chat_history": [], "last_agent": None}
    return _sessions[sid]


def _clear_docs_and_chroma():
    global _uploaded_doc_names
    if os.path.exists(SAVE_DIR):
        for f in os.listdir(SAVE_DIR):
            os.remove(os.path.join(SAVE_DIR, f))
    if os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)
    os.makedirs(SAVE_DIR, exist_ok=True)
    _uploaded_doc_names.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# Startup
# ═══════════════════════════════════════════════════════════════════════════════
@app.on_event("startup")
async def startup():
    # Google GenAI client is auto-configured via GOOGLE_API_KEY and GOOGLE_GENAI_USE_VERTEXAI env vars
    print(f"[server] Google GenAI configured (project={GOOGLE_CLOUD_PROJECT}, location={GOOGLE_CLOUD_LOCATION})")

    print("[server] Compiling LangGraph workflow...")
    get_graph()
    print("[server] ✅ LangGraph ready.")

    try:
        from services.wordpress_fetcher import test_connection
        from services.scheduler import start_scheduler
        from agents.rag_agents.embeddings import get_embedding_model
        from langchain_community.vectorstores import Chroma

        if test_connection():
            rag = get_rag()
            if rag is None:
                rag = rebuild_rag()
            vs = getattr(rag, "vectorstore", None)
            if vs is None:
                vs = Chroma(
                    persist_directory=CHROMA_DIR,
                    embedding_function=get_embedding_model(),
                )
            start_scheduler(vs)
            print("[server] ✅ WordPress scheduler started.")
        else:
            print("[server] WordPress not reachable — skipping scheduler.")
    except Exception as e:
        print(f"[server] WordPress scheduler error: {e}")

    # ── VM (Permanent Vector Store) health check ──
    try:
        import requests as _req
        vm_resp = _req.get(f"{VM_BASE_URL}/", timeout=5)
        if vm_resp.status_code == 200:
            print(f"[server] ✅ VM permanent knowledge base connected at {VM_BASE_URL}")
        else:
            print(f"[server] ⚠️ VM responded with status {vm_resp.status_code}")
    except Exception as e:
        print(f"[server] ⚠️ VM not reachable at {VM_BASE_URL}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Transgraph API is running."}


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════════════════════════════════════════
class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    route: str
    chart_b64: str | None = None
    report_text: str | None = None  


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(req: ChatRequest):
    graph   = get_graph()
    rag     = get_rag()
    session = get_session(req.session_id)

    state_input = {
        **session,
        "query":             req.query,
        "rag_agent":         rag,
        "has_uploaded_docs":  len(_uploaded_doc_names) > 0,
        "uploaded_doc_names": list(_uploaded_doc_names),
    }

    result = graph.invoke(state_input)

    # Update session
    session["chat_history"].append(req.query)
    session["last_agent"] = result.get("route")
    session.update({k: v for k, v in result.items()
                    if k not in ("chart_buffer", "rag_agent")})

    # Chart → base64
    chart_b64 = None
    chart_buf: BytesIO | None = result.get("chart_buffer")
    if chart_buf:
        chart_buf.seek(0)
        chart_b64 = base64.b64encode(chart_buf.read()).decode()

    # final_output → string
    raw = result.get("final_output", "")
    if isinstance(raw, list):
        raw = "\n".join(str(x) for x in raw)
    elif not isinstance(raw, str):
        raw = str(raw) if raw else ""

    route = result.get("route", "unknown")

    # If report_agent, include report_text so frontend can request downloads
    report_text = None
    if route == "report_agent":
        report_text = result.get("report_text", "")
        if isinstance(report_text, dict):
            report_text = report_text.get("text", str(report_text))
        elif isinstance(report_text, list):
            report_text = "\n".join(
                x.get("text", str(x)) if isinstance(x, dict) else str(x)
                for x in report_text
            )
        elif not isinstance(report_text, str):
            report_text = str(report_text) if report_text else ""

    return ChatResponse(
        answer=raw or "No response generated.",
        route=route,
        chart_b64=chart_b64,
        report_text=report_text,
    )


@app.delete("/api/chat/{session_id}", tags=["Chat"])
async def clear_chat(session_id: str):
    _sessions.pop(session_id, None)
    return {"status": "cleared"}


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT DOWNLOAD  (PDF / DOCX)
# ═══════════════════════════════════════════════════════════════════════════════
class ReportRequest(BaseModel):
    report_text: str
    format: str = "pdf"       # "pdf" or "docx"
    chart_b64: str | None = None


@app.post("/api/report", tags=["Report"])
async def download_report(req: ReportRequest):
    chart_bytes = None
    if req.chart_b64:
        chart_bytes = BytesIO(base64.b64decode(req.chart_b64))

    if req.format == "docx":
        buf = generate_docx(req.report_text, chart_bytes)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=transgraph_report.docx"},
        )
    else:
        buf = generate_pdf(req.report_text, chart_bytes)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=transgraph_report.pdf"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════
@app.post("/api/upload", tags=["Upload"])
async def upload_files(files: List[UploadFile] = File(...)):
    os.makedirs(SAVE_DIR, exist_ok=True)
    injected, failed = [], []

    for file in files:
        try:
            content = await file.read()
            is_image = file.content_type and file.content_type.startswith("image")

            if is_image:
                extracted = _extract_image_text(content, file.filename)
                base = os.path.splitext(file.filename)[0].replace(" ", "_")
                out_name = f"__image_extract__{base}.md"
                with open(os.path.join(SAVE_DIR, out_name), "w", encoding="utf-8") as f:
                    f.write(f"Source image: {file.filename}\n\n{extracted}\n")
                if out_name not in _uploaded_doc_names:
                    _uploaded_doc_names.append(out_name)
                injected.append(out_name)
            else:
                with open(os.path.join(SAVE_DIR, file.filename), "wb") as f:
                    f.write(content)
                if file.filename not in _uploaded_doc_names:
                    _uploaded_doc_names.append(file.filename)
                injected.append(file.filename)
        except Exception as e:
            failed.append({"file": file.filename, "error": str(e)})

    if injected:
        rebuild_rag()

    return JSONResponse({
        "injected": injected,
        "failed": failed,
        "total_docs": list(_uploaded_doc_names),
    })


def _extract_image_text(img_bytes: bytes, filename: str) -> str:
    from PIL import Image as PILImage
    client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # Create image part from bytes
    image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/png")
    
    prompt = (
        "You are analyzing a chart/graph image for retrieval-based Q&A.\n"
        "Extract: 1) Chart type/title 2) Axes labels 3) Key values (table if possible) "
        "4) Trends, peaks, outliers 5) Visible text/labels. Be precise."
    )
    resp = client.models.generate_content(
        model=PRIMARY_MODEL,
        contents=[prompt, image_part]
    )
    return resp.text or str(resp)


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE
# ═══════════════════════════════════════════════════════════════════════════════
class DriveRequest(BaseModel):
    url: str


@app.post("/api/drive", tags=["Upload"])
async def inject_from_drive(req: DriveRequest):
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", req.url)
    if not match:
        raise HTTPException(400, "Invalid Google Drive folder URL")
    folder_id = match.group(1)

    with tempfile.TemporaryDirectory() as tmp:
        try:
            downloaded = gdown.download_folder(
                id=folder_id, output=tmp, quiet=True,
                use_cookies=False, remaining_ok=True,
            )
        except Exception as e:
            raise HTTPException(500, f"Drive download failed: {e}")

        if not downloaded:
            raise HTTPException(404, "No files found in folder")

        _clear_docs_and_chroma()
        injected = []

        paths = []
        for item in (downloaded if isinstance(downloaded, list) else [downloaded]):
            if os.path.isdir(item):
                for fname in os.listdir(item):
                    paths.append(os.path.join(item, fname))
            elif os.path.isfile(item):
                paths.append(item)

        for src in paths:
            fname = os.path.basename(src)
            shutil.copy2(src, os.path.join(SAVE_DIR, fname))
            _uploaded_doc_names.append(fname)
            injected.append(fname)

    if injected:
        rebuild_rag()

    return JSONResponse({"injected": injected, "total_docs": list(_uploaded_doc_names)})


# ═══════════════════════════════════════════════════════════════════════════════
# DOCS
# ═══════════════════════════════════════════════════════════════════════════════
@app.get("/api/docs", tags=["Upload"])
async def list_docs():
    return {"docs": list(_uploaded_doc_names)}


@app.delete("/api/docs", tags=["Upload"])
async def clear_docs():
    _clear_docs_and_chroma()
    return {"status": "cleared"}


@app.delete("/api/docs/{filename}", tags=["Upload"])
async def delete_single_doc(filename: str):
    """Remove a single document from the knowledge base."""
    global _uploaded_doc_names
    filepath = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, f"Document '{filename}' not found.")
    os.remove(filepath)
    _uploaded_doc_names = [d for d in _uploaded_doc_names if d != filename]
    # Rebuild RAG with remaining docs, or clear chroma if none left
    if _uploaded_doc_names:
        rebuild_rag()
    else:
        if os.path.exists(CHROMA_DIR):
            shutil.rmtree(CHROMA_DIR, ignore_errors=True)
        global _rag_agent
        _rag_agent = None
    return {"status": "deleted", "filename": filename, "remaining_docs": list(_uploaded_doc_names)}


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════
LAST_SYNC_FILE = os.path.join("data", "last_sync.json")


@app.get("/api/status", tags=["Status"])
async def status():
    wp_connected = False
    last_sync = None
    vm_connected = False
    if os.path.exists(LAST_SYNC_FILE):
        try:
            with open(LAST_SYNC_FILE) as f:
                last_sync = json.load(f).get("last_sync")
        except Exception:
            pass
    try:
        from services.wordpress_fetcher import test_connection
        wp_connected = test_connection()
    except Exception:
        pass
    try:
        import requests as _req
        vm_resp = _req.get(f"{VM_BASE_URL}/", timeout=5)
        vm_connected = vm_resp.status_code == 200
    except Exception:
        pass
    return JSONResponse({
        "wordpress_connected": wp_connected,
        "last_sync": last_sync,
        "vm_connected": vm_connected,
        "vm_url": VM_BASE_URL,
    })

@app.post("/api/agui", tags=["AG-UI"])
async def agui_chat(input_data: RunAgentInput, request: Request):
    """
    AG-UI compatible SSE endpoint.
    Replaces /api/chat for the new streaming ChatWidget.
    The old /api/chat remains for backward compatibility.
    """
    # Reuse the existing session memory system
    session_id = input_data.thread_id or "default"
    session    = get_session(session_id)
    rag        = get_rag()
    graph      = get_graph()          # ← shared singleton, no duplicate compilation

    async def event_stream():
        async for chunk in run_agui_stream(
            input_data=input_data,
            graph=graph,
            rag_agent=rag,
            uploaded_doc_names=list(_uploaded_doc_names),
            session_memory=session,
        ):
            yield chunk

        # ── Update session memory for multi-turn context ──
        final = session.pop("_agui_final_state", None)
        if final:
            session["chat_history"].append(final["query"])
            session["last_agent"] = final["route"]

    return StreamingResponse(event_stream(), media_type="text/event-stream")

