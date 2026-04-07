"""
langfuse_handler.py
───────────────────
Provides a Langfuse CallbackHandler for LangChain / LangGraph tracing.
Compatible with langfuse SDK v4.x.

The SDK auto-reads these env vars (set in .env):
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

Usage:
    from utils.langfuse_handler import get_langfuse_handler

    handler = get_langfuse_handler(session_id="abc", user_id="user_1")
    # Then pass to graph:  graph.invoke(state, config={"callbacks": [handler]})
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Check if Langfuse keys are configured ─────────────────────────────────────
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

_langfuse_available = bool(LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY)

if _langfuse_available:
    # Ensure env vars are set for the SDK to auto-read
    os.environ.setdefault("LANGFUSE_SECRET_KEY", LANGFUSE_SECRET_KEY)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", LANGFUSE_PUBLIC_KEY)
    os.environ.setdefault("LANGFUSE_HOST", LANGFUSE_HOST)
    print(f"[langfuse] ✅ Langfuse tracing enabled → {LANGFUSE_HOST}")
else:
    print("[langfuse] ⚠️  Langfuse keys not set — tracing disabled.")


def get_langfuse_handler(
    session_id: str | None = None,
    user_id: str | None = None,
    trace_name: str | None = None,
    tags: list[str] | None = None,
):
    """
    Returns a fresh LangchainCallbackHandler bound to one logical request/trace.

    Parameters
    ----------
    session_id : str, optional
        Groups traces by chat session in the Langfuse dashboard.
    user_id : str, optional
        Associates traces with a specific end-user.
    trace_name : str, optional
        Human-readable label shown in the Langfuse timeline.
    tags : list[str], optional
        Arbitrary tags for filtering in the dashboard.

    Returns None if Langfuse is not configured.
    """
    if not _langfuse_available:
        return None

    try:
        from langfuse.langchain import CallbackHandler
        from langfuse.types import TraceContext

        # Build trace context with session/user metadata
        trace_ctx = TraceContext(
            name=trace_name or "transgraph-agent",
            session_id=session_id,
            user_id=user_id,
            tags=tags or [],
        )

        handler = CallbackHandler(trace_context=trace_ctx)
        return handler

    except Exception as e:
        print(f"[langfuse] ❌ Failed to create handler: {e}")
        return None


def flush_langfuse():
    """
    Flush pending Langfuse events. Call on shutdown or end of short-lived scripts.
    """
    if not _langfuse_available:
        return
    try:
        from langfuse import Langfuse
        client = Langfuse()
        client.flush()
    except Exception as e:
        print(f"[langfuse] Flush error: {e}")
