from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_text_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Splits text content into semantic chunks using LangChain's RecursiveCharacterTextSplitter.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n--- Page Break ---\n\n", "\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)
