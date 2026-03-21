from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL



class RAGState(TypedDict):
    query: str
    docs: List
    answer: str
    approved: bool

def get_llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        temperature=0.2,
        api_key=GOOGLE_API_KEY
    )

def extract_text_from_response(response):
    """Extract clean text from various LLM response formats"""
    if response is None:
        return ""
    
    # If it's already a string, return it
    if isinstance(response, str):
        return response.strip()
    
    # If it has a content attribute (AIMessage object)
    if hasattr(response, "content"):
        text = response.content
        if isinstance(text, str):
            return text.strip()
        # If content is a list, extract from it
        if isinstance(text, list) and text:
            return extract_text_from_response(text[0])
    
    # If it's a list
    if isinstance(response, list):
        if not response:
            return ""
        # Recursively extract from first item
        return extract_text_from_response(response[0])
    
    # If it's a dictionary
    if isinstance(response, dict):
        # Try common keys
        for key in ['text', 'content', 'message', 'answer']:
            if key in response:
                result = extract_text_from_response(response[key])
                if result:
                    return result
        # If no common keys, convert to string
        return str(response)
    
    # Fallback: convert to string
    return str(response).strip()

def retrieve_node(state: RAGState, retriever):
    docs = retriever.invoke(state["query"])
    return {"docs": docs}

def answer_node(state: RAGState):
    llm = get_llm()

    context_blocks = []
    for d in state["docs"]:
        m = d.metadata
        context_blocks.append(
            f"[Doc: {m.get('doc_name','NA')} | "
            f"Page: {m.get('page','NA')} | "
            f"Chunk: {m.get('chunk_id','NA')} | "
            f"Time: {m.get('ingest_time','NA')}]\n"
            f"{d.page_content}"
        )

    context = "\n\n".join(context_blocks)

    prompt = f"""
You are a document QA assistant.

Answer ONLY using the context below.
Do not use external knowledge.

If the answer is missing, say:
"I could not find this information in the documents."

Context:
{context}

Question:
{state['query']}

Answer:
"""


    response = llm.invoke(prompt)
    
    # Use helper function to extract clean text from any response format
    answer = extract_text_from_response(response)
    
    # Debug: Print full answer length and content
    if answer:
        print(f"LLM Answer (extracted): Length={len(answer)} chars")
        print("LLM Answer (extracted):", answer[:200] + "..." if len(answer) > 200 else answer)
        print("Full answer being returned:", answer)  # Debug full answer
    else:
        print("WARNING: Empty answer extracted from response")
        answer = "I could not find this information in the documents."
    
    # Build sources list safely
    try:
        sources = [
            f"{d.metadata.get('doc_name','NA')} | "
            f"Page {d.metadata.get('page','NA')} | "
            f"Chunk {d.metadata.get('chunk_id','NA')} | "
            f"Ingested {d.metadata.get('ingest_time','NA')}"
            for d in state.get("docs", [])
        ]
        sources_text = "\n".join(sources) if sources else "No sources available"
    except Exception as e:
        print(f"Error building sources: {e}")
        sources_text = "Sources unavailable"

    final_answer = (
        f"{answer}\n\n"
        f"---\n"
        f"**Sources:**\n{sources_text}"
    )

    print("Returning answer from answer_node")
    return {"answer": final_answer}

def evaluate_node(state: RAGState):
    llm = get_llm()

    response = llm.invoke(
        f"""
Question:
{state['query']}

Answer:
{state['answer']}

Is the answer:
- strictly grounded in the context?
- complete?
- free of hallucination?

Reply only YES or NO.
"""
    )
    
    # Handle different response types
    if hasattr(response, "content"):
        verdict = response.content
    elif isinstance(response, list):
        # Extract text from list of dictionaries like [{'type': 'text', 'text': '...'}]
        if response and isinstance(response[0], dict):
            verdict = response[0].get('text', str(response[0]))
        elif response and hasattr(response[0], "content"):
            verdict = response[0].content
        else:
            verdict = str(response[0]) if response else "NO"
    elif isinstance(response, dict):
        # Handle dictionary response
        verdict = response.get('text', response.get('content', str(response)))
    else:
        verdict = str(response)
    
    verdict = verdict.strip().upper() if isinstance(verdict, str) else str(verdict).strip().upper()

    return {"approved": verdict == "YES"}


def router(state: RAGState):
    return END if state["approved"] else "answer"


def build_rag_chain(retriever):
    builder = StateGraph(RAGState)

    builder.add_node("retrieve", lambda s: retrieve_node(s, retriever))
    builder.add_node("answer", answer_node)
    # Temporarily disabled evaluation to prevent infinite loops
    # builder.add_node("evaluate", evaluate_node)

    builder.set_entry_point("retrieve")
    builder.add_edge("retrieve", "answer")
    builder.add_edge("answer", END)  # Go directly to end, skip evaluation
    # builder.add_edge("answer", "evaluate")
    # builder.add_conditional_edges("evaluate", router)

    graph = builder.compile()

    def run(query: str):
        try:
            result = graph.invoke({"query": query})
            # Ensure we return the answer field, or fallback to empty string
            answer = result.get("answer", "")
            if not answer:
                print("WARNING: No answer found in result:", result.keys())
            return answer
        except Exception as e:
            print(f"Error in RAG chain: {e}")
            import traceback
            traceback.print_exc()
            return f"Error processing query: {str(e)}"

    return run
