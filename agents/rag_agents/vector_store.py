from langchain_community.vectorstores import Chroma

PERSIST_DIR = "chroma_db"


def create_vector_store(chunks, embeddings):
    """
    Creates a Chroma vector store from document chunks and embeddings.
    
    Args:
        chunks (list): List of chunked Document objects to be stored in the vector database
        embeddings: Embedding model instance for generating vector representations
        
    Returns:
        Chroma: Configured Chroma vector store with documents embedded and persisted to disk
               at the PERSIST_DIR location for efficient similarity search and retrieval.
    """
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )