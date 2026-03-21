# from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
# import os

# def load_documents(data_path: str):
#     documents = []

#     for file in os.listdir(data_path):
#         file_path = os.path.join(data_path, file)

#         if file.endswith(".pdf"):
#             loader = PyPDFLoader(file_path)
#             documents.extend(loader.load())

#         elif file.endswith(".docx"):
#             loader = Docx2txtLoader(file_path)
#             documents.extend(loader.load())

#     return documents
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_core.documents import Document

import pandas as pd
import os


def load_documents(data_path: str):
    documents = []

    if not os.path.exists(data_path):
        return documents

    for file in os.listdir(data_path):
        file_path = os.path.join(data_path, file)

        # PDF
        if file.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())

        # DOCX
        elif file.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
            documents.extend(loader.load())

        # Text / Markdown (used for extracted image chart text)
        elif file.endswith(".txt") or file.endswith(".md"):
            loader = TextLoader(file_path, encoding="utf-8")
            docs = loader.load()
            for d in docs:
                d.metadata = {**(d.metadata or {}), "source": file}
            documents.extend(docs)

        # CSV
        elif file.endswith(".csv"):
            df = pd.read_csv(file_path)
            text = df.to_string(index=False)
            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": file}
                )
            )

        # Excel
        elif file.endswith(".xlsx"):
            df = pd.read_excel(file_path)
            text = df.to_string(index=False)
            documents.append(
                Document(
                    page_content=text,
                    metadata={"source": file}
                )
            )
        
        # Files without extension - treat as text
        elif "." not in file or file.split(".")[-1] not in ["pdf", "docx", "txt", "md", "csv", "xlsx"]:
            try:
                print(f"Attempting to read file: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"Successfully read {len(content)} characters from {file}")
                documents.append(
                    Document(
                        page_content=content,
                        metadata={"source": file}
                    )
                )
            except Exception as e:
                print(f"Could not read file {file}: {e}")
                # Try different encodings
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    print(f"Successfully read {len(content)} characters from {file} with latin-1")
                    documents.append(
                        Document(
                            page_content=content,
                            metadata={"source": file}
                        )
                    )
                except Exception as e2:
                    print(f"Could not read file {file} with latin-1 either: {e2}")

    return documents
