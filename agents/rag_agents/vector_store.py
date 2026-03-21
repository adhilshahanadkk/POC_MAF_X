from langchain_community.vectorstores import Chroma

PERSIST_DIR = "chroma_db"


def create_vector_store(chunks, embeddings):
    return Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
