from graph.workflow import build_graph

app = build_graph()

state_memory = {
    "chat_history": [],
    "last_agent": None
}

while True:
    query = input("Ask Query: ")

    # MEMORY QUESTION HANDLER
    if "previous question" in query.lower():
        history = state_memory.get("chat_history", [])
        if history:
            print("\nSQL Output:")
            print(history[-1])
        else:
            print("\nSQL Output:")
            print("No previous question found.")
        continue

    state_input = {**state_memory, "query": query}

    result = app.invoke(state_input)

    # -------- MEMORY UPDATE --------
    state_memory["chat_history"].append(query)
    state_memory["last_agent"] = result.get("route")

    state_memory.update(result)

    print("\nSQL Output:")
    print(result.get("final_output"))
