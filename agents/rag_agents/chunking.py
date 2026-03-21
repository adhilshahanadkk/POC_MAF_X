import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime

def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(documents)
    ingest_time = datetime.utcnow().strftime("%d %b %Y, %I:%M %p UTC")


    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = idx
        chunk.metadata["ingest_time"] = ingest_time
        chunk.metadata["doc_name"] = os.path.basename(chunk.metadata.get("source", "unknown")
)

    return chunks
