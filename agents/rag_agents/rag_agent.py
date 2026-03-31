import os
from agents.rag_agents.loader import load_documents
from agents.rag_agents.chunking import chunk_documents
from agents.rag_agents.embeddings import get_embedding_model
from agents.rag_agents.vector_store import create_vector_store
from agents.rag_agents.rag_chain import build_rag_chain



class RAGAgent:
    """
    Retrieval-Augmented Generation (RAG) agent for document-based question answering.
    
    This agent loads documents, creates embeddings, builds a vector store, and provides
    a retriever for finding relevant document chunks to answer user queries.
    
    Attributes:
        retriever: Vector store retriever for finding relevant document chunks
        rag_chain: RAG chain for generating responses based on retrieved documents
    """
    
    def __init__(self, data_path: str):
        """
        Initialize the RAG agent by loading documents and building the retrieval system.
        
        Args:
            data_path (str): Base path containing the 'docs' directory with documents
            
        Process:
            1. Loads documents from {data_path}/docs directory
            2. Chunks documents into smaller pieces
            3. Creates embeddings and vector store
            4. Sets up retriever and RAG chain
            5. Handles cases with no documents gracefully
        """
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
            return

        chunks = chunk_documents(documents)
        print(f"Created {len(chunks)} chunks")

        if not chunks:
            print("No chunks created from documents. Skipping vector store creation.")
            self.retriever = None
            self.rag_chain = None
            return

        embeddings = get_embedding_model()
        vectordb = create_vector_store(chunks, embeddings)

        self.retriever = vectordb.as_retriever(search_kwargs={"k": 6})
        self.rag_chain = build_rag_chain(self.retriever)

    def run(self, query: str):
        """
        Process a user query using the RAG system to generate a response.
        
        Args:
            query (str): User question or query to be answered based on uploaded documents
            
        Returns:
            str: Generated response based on retrieved document chunks, or error message
                 if no documents are available for retrieval
        """
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