
import os
from agents.rag_agents.loader import load_documents
from agents.rag_agents.chunking import chunk_documents
from agents.rag_agents.embeddings import get_embedding_model
from agents.rag_agents.vector_store import create_vector_store
from agents.rag_agents.rag_chain import build_rag_chain



class RAGAgent:
    def __init__(self, data_path: str):
        documents = []
        docs_path = f"{data_path}/docs"
        print(f"Looking for documents in: {docs_path}")
        print(f"Path exists: {os.path.exists(docs_path)}")
        if os.path.exists(docs_path):
            files_in_docs = os.listdir(docs_path)
            print(f"Files found: {files_in_docs}")
        
        documents.extend(load_documents(f"{data_path}/docs"))

        print(f"Loaded {len(documents)} documents")

        if not documents:
            print("No documents found for RAG. Skipping vector store creation.")
            self.retriever = None
            self.rag_chain = None
            self.vectorstore = None
            return

        chunks = chunk_documents(documents)
        print(f"Created {len(chunks)} chunks")

        if not chunks:
            print("No chunks created from documents. Skipping vector store creation.")
            self.retriever = None
            self.rag_chain = None
            self.vectorstore = None
            return

        embeddings = get_embedding_model()
        vectordb = create_vector_store(chunks, embeddings)

        self.vectorstore = vectordb
        self.retriever = vectordb.as_retriever(search_kwargs={"k": 6})
        self.rag_chain = build_rag_chain(self.retriever)

    def run(self, query: str):
        if not self.rag_chain:
            return "I don't have any uploaded documents or chart analyses to answer from yet. Please upload a document or chart image and try again."
        return self.rag_chain(query)


if __name__ == "__main__":
    agent = RAGAgent(data_path="data")

    print("\n🤖 Agentic RAG Assistant (type 'exit' to quit)\n")

    while True:
        q = input("Ask ➜ ")
        if q.lower() == "exit":
            break
        print("\nAI:\n", agent.run(q))
