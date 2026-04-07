# agui_runner.py
import uuid
import base64
import asyncio
from typing import AsyncGenerator

from ag_ui.core import (
    RunAgentInput, EventType,
    RunStartedEvent, RunFinishedEvent, RunErrorEvent,
    StepStartedEvent, StepFinishedEvent,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    StateSnapshotEvent,
)
from ag_ui.encoder import EventEncoder
from utils.langfuse_handler import get_langfuse_handler


# Map LangGraph node names → human-readable step labels shown in the UI
STEP_LABELS = {
    "supervisor":   "Supervisor: routing query",
    "planner":      "Planner: building execution plan",
    "executor":     "Executor: running sub-agents",
    "combiner":     "Combiner: synthesising results",
    "mysql_agent":  "MySQL Agent: querying user data",
    "mssql_agent":  "MSSQL Agent: querying market data",
    "rag_agent":    "RAG Agent: searching documents",
    "vm_agent":     "VM Agent: searching knowledge base",
    "graph_agent":  "Chart Agent: building visualisation",
    "report_agent": "Report Agent: formatting report",
}


async def run_agui_stream(
    input_data: RunAgentInput,
    graph,                          # ← accept pre-compiled graph from server
    rag_agent,
    uploaded_doc_names: list[str],
    session_memory: dict,
) -> AsyncGenerator[str, None]:
    """
    Async generator that:
      1. Invokes the LangGraph workflow via astream_events
      2. Translates LangGraph node lifecycle events → AG-UI events
      3. Yields SSE-encoded strings for FastAPI StreamingResponse

    The caller (server.py) is responsible for updating session_memory
    after the stream completes.  We store result state in
    session_memory["_agui_final_state"] so the server can read it.
    """
    encoder = EventEncoder()
    run_id  = str(uuid.uuid4())
    thread_id = input_data.thread_id or str(uuid.uuid4())

    # Extract the user's query from the AG-UI message list
    query = ""
    for msg in reversed(input_data.messages):
        if hasattr(msg, "role") and msg.role == "user":
            content = msg.content
            query = content if isinstance(content, str) else str(content)
            break

    # ── RUN_STARTED ──────────────────────────────────────────────────────────
    yield encoder.encode(RunStartedEvent(
        type=EventType.RUN_STARTED,
        thread_id=thread_id,
        run_id=run_id,
    ))

    query_lower = query.lower().strip()

    # ── CHECK: Is this a simple greeting? ────────────────────────────────
    # If so, respond immediately without invoking the graph
    greeting_patterns = {
        "hi", "hello", "hey", "hii", "hiii", "yo", "sup",
        "good morning", "good afternoon", "good evening",
        "howdy", "hola", "namaste", "greetings",
    }
    if query_lower in greeting_patterns or query_lower.rstrip("!.,") in greeting_patterns:
        greeting_answer = "Hello! How can I help you today?"
        message_id = str(uuid.uuid4())
        yield encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant",
        ))
        yield encoder.encode(TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id=message_id,
            delta=greeting_answer,
        ))
        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id,
        ))

        session_memory["_agui_final_state"] = {
            "query": query,
            "route": "greeting",
            "answer": greeting_answer,
        }

        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id,
        ))
        return  # ← skip graph entirely

    # ── CHECK: Is this a conversational/meta question? ────────────────────
    # If so, answer directly from chat_history without invoking the graph
    conversational_keywords = [
        "previous question", "last question", "what did i ask",
        "what did you say", "what was my", "repeat", "our conversation",
        "chat history", "last answer", "earlier question",
    ]
    chat_history = session_memory.get("chat_history", [])
    is_conversational = any(kw in query_lower for kw in conversational_keywords)

    if is_conversational:
        if not chat_history:
            answer = "No previous conversation found. This is a new session — please ask a question first!"
        else:
            # Build a targeted answer based on what the user is asking
            user_questions = [h.replace("User: ", "") for h in chat_history if h.startswith("User: ")]
            ai_answers = [h for h in chat_history if h.startswith("AI (")]

            if "previous question" in query_lower or "last question" in query_lower or "what did i ask" in query_lower:
                if user_questions:
                    answer = f"Your previous question was:\n\n\"{user_questions[-1]}\""
                else:
                    answer = "You haven't asked any questions yet in this session."
            elif "last answer" in query_lower or "what did you say" in query_lower:
                if ai_answers:
                    last_answer = ai_answers[-1].split("): ", 1)[-1] if "): " in ai_answers[-1] else ai_answers[-1]
                    answer = f"My previous answer was:\n\n{last_answer}"
                else:
                    answer = "I haven't provided any answers yet in this session."
            else:
                # General conversation history request
                history_text = "\n".join(chat_history[-20:])
                answer = f"Here is your conversation history:\n\n{history_text}"

        message_id = str(uuid.uuid4())
        yield encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id=message_id,
            role="assistant",
        ))
        yield encoder.encode(TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            message_id=message_id,
            delta=answer,
        ))
        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id=message_id,
        ))

        # Update session memory
        session_memory["_agui_final_state"] = {
            "query": query,
            "route": "chat_history",
            "answer": answer,
        }

        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id,
        ))
        return  # ← skip graph entirely

    state_input = {
        **session_memory,
        "query":              query,
        "rag_agent":          rag_agent,
        "has_uploaded_docs":  len(uploaded_doc_names) > 0,
        "uploaded_doc_names": list(uploaded_doc_names),
    }

    final_state = {}

    # ── Langfuse tracing ──────────────────────────────────────────────────
    langfuse_handler = get_langfuse_handler(
        session_id=thread_id,
        trace_name="agui_chat",
        tags=["agui", "streaming"],
    )
    run_config = {"callbacks": [langfuse_handler]} if langfuse_handler else {}

    try:
        # astream_events streams node-level lifecycle events from LangGraph
        async for event in graph.astream_events(state_input, version="v2", config=run_config):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Debug: log all chain events to see what names come through
            if kind in ("on_chain_start", "on_chain_end"):
                print(f"[agui_runner] {kind} | name={name!r} | in_STEP_LABELS={name in STEP_LABELS}")

            # ── Node started → STEP_STARTED ──────────────────────────────
            if kind == "on_chain_start" and name in STEP_LABELS:
                print(f"[agui_runner] >>> Emitting STEP_STARTED: {STEP_LABELS[name]}")
                yield encoder.encode(StepStartedEvent(
                    type=EventType.STEP_STARTED,
                    step_name=STEP_LABELS[name],
                ))

            # ── Node finished → STEP_FINISHED + capture state ─────────────
            elif kind == "on_chain_end" and name in STEP_LABELS:
                yield encoder.encode(StepFinishedEvent(
                    type=EventType.STEP_FINISHED,
                    step_name=STEP_LABELS[name],
                ))
                # Accumulate state from each node's output
                node_output = event.get("data", {}).get("output", {})
                print(f"[agui_runner] on_chain_end output for {name!r}: type={type(node_output).__name__}, keys={list(node_output.keys()) if isinstance(node_output, dict) else 'N/A'}")
                if isinstance(node_output, dict):
                    final_state.update(node_output)

        # ── Stream final answer as TEXT_MESSAGE events ────────────────────
        answer = final_state.get("final_output", "")
        print(f"[agui_runner] final_state keys: {list(final_state.keys())}")    
        print(f"[agui_runner] final_output type={type(answer).__name__}, len={len(str(answer))}, preview={str(answer)[:100]!r}")
        if isinstance(answer, list):
            answer = "\n".join(str(x) for x in answer)
        elif not isinstance(answer, str):
            answer = str(answer) if answer else ""

        message_id = str(uuid.uuid4())
        if answer.strip():
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=message_id,
                role="assistant",
            ))
            # Stream in chunks for smooth word-by-word appearance
            chunk_size = 8
            words = answer.split(" ")
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=message_id,
                    delta=chunk,
                ))
                await asyncio.sleep(0)  # yield to event loop
            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=message_id,
            ))

        # ── Emit shared state snapshot (chart, route, report) ─────────────
        chart_buf = final_state.get("chart_buffer")
        chart_b64 = None
        if chart_buf:
            chart_buf.seek(0)
            chart_b64 = base64.b64encode(chart_buf.read()).decode()

        route = final_state.get("route", "unknown")

        # Build report_text (same normalisation as /api/chat)
        report_text = None
        if route == "report_agent":
            rt = final_state.get("report_text", "")
            if isinstance(rt, dict):
                report_text = rt.get("text", str(rt))
            elif isinstance(rt, list):
                report_text = "\n".join(
                    x.get("text", str(x)) if isinstance(x, dict) else str(x)
                    for x in rt
                )
            elif isinstance(rt, str):
                report_text = rt
            else:
                report_text = str(rt) if rt else None

        shared_state = {
            "route":       route,
            "chart_b64":   chart_b64,
            "report_text": report_text,
            "answer":      answer,
        }
        yield encoder.encode(StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot=shared_state,
        ))

        # ── Store final_state so server.py can update session memory ──────
        session_memory["_agui_final_state"] = {
            "query":  query,
            "route":  route,
            "answer": answer,
        }

        # ── RUN_FINISHED ──────────────────────────────────────────────────
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id,
        ))

    except Exception as exc:
        yield encoder.encode(RunErrorEvent(
            type=EventType.RUN_ERROR,
            message=str(exc),
            code="GRAPH_ERROR",
        ))