import os
import logging
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Fallback basic text searcher class in case FAISS/Embeddings fail to initialize
class BasicTextSearcher:
    """
    A pure Python fallback semantic-ish searcher based on overlap/keyword matching
    if FAISS or remote embeddings are offline or fail to compile on Python 3.14.
    """
    def __init__(self):
        self.chunks = []
        self.metadatas = []

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        self.chunks.extend(texts)
        self.metadatas.extend(metadatas)

    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        # Simple query term overlap ranking
        query_words = set(query.lower().split())
        results = []
        
        for idx, chunk in enumerate(self.chunks):
            chunk_words = set(chunk.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            # Calculate a pseudo score
            score = overlap / (len(query_words) + 1)
            results.append((score, chunk, self.metadatas[idx]))
            
        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Return top k as standard dicts
        top_k = results[:k]
        return [
            {
                "page_content": content,
                "metadata": meta,
                "score": float(score)
            }
            for score, content, meta in top_k
        ]


class VectorStoreService:
    def __init__(self):
        self.index_dir = settings.FAISS_INDEX_PATH
        self.db = None
        self.fallback_db = BasicTextSearcher()
        self._init_embeddings_and_faiss()

    def _init_embeddings_and_faiss(self):
        try:
            # We use Google Generative AI Embeddings as primary choice
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning("GEMINI_API_KEY is not configured. Falling back to local SentenceTransformers or BasicTextSearcher.")
                raise ValueError("No Gemini API key")
                
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=api_key
            )
            logger.info("GoogleGenerativeAIEmbeddings initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not load Google Generative AI Embeddings: {e}. Trying SentenceTransformers...")
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
                self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                logger.info("Local HuggingFace all-MiniLM-L6-v2 Embeddings initialized successfully.")
            except Exception as hf_err:
                logger.error(f"Could not load local HuggingFace embeddings: {hf_err}. Using BasicTextSearcher fallback.")
                self.embeddings = None
                return

        # Attempt to load existing FAISS index
        try:
            from langchain_community.vectorstores import FAISS
            if os.path.exists(os.path.join(self.index_dir, "index.faiss")):
                # FAISS requires allow_dangerous_deserialization=True for local files loading
                self.db = FAISS.load_local(
                    self.index_dir, 
                    self.embeddings, 
                    allow_dangerous_deserialization=True
                )
                logger.info("Existing FAISS index loaded successfully.")
            else:
                logger.info("No existing FAISS index found. Ready for creation.")
        except Exception as faiss_err:
            logger.error(f"Could not load/initialize FAISS: {faiss_err}. Using BasicTextSearcher.")
            self.db = None

    def add_chunks(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        Adds text chunks with metadata to the active index and persists it to disk.
        """
        # Always feed the fallback
        self.fallback_db.add_texts(texts, metadatas)
        
        if self.embeddings is None:
            logger.warning("Embeddings not initialized. Chunks saved only to fallback text index.")
            return

        try:
            from langchain_community.vectorstores import FAISS
            if self.db is None:
                self.db = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
            else:
                self.db.add_texts(texts, metadatas=metadatas)
            
            # Save the index locally
            self.db.save_local(self.index_dir)
            logger.info("FAISS index successfully updated and saved to disk.")
        except Exception as e:
            logger.error(f"Error adding chunks to FAISS index: {e}")
            # Do not raise, we have the fallback database

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the index for documents matching the query.
        Returns a list of dictionaries with 'page_content' and 'metadata'.
        """
        if self.db is None or self.embeddings is None:
            logger.info("Vector DB not active. Running keyword search on fallback.")
            return self.fallback_db.similarity_search(query, k=k)

        try:
            results = self.db.similarity_search_with_score(query, k=k)
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "page_content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            return formatted_results
        except Exception as e:
            logger.error(f"FAISS search failed: {e}. Executing fallback search...")
            return self.fallback_db.similarity_search(query, k=k)


# Singleton instance
vector_store = VectorStoreService()
