import os
import json
import logging
from typing import List, Dict, Any, Optional, Set
from app.core.config import settings

logger = logging.getLogger(__name__)

FALLBACK_INDEX_FILENAME = "fallback_index.json"


def _reciprocal_rank_fusion(result_lists: List[List[Dict[str, Any]]], k_constant: int = 60) -> List[Dict[str, Any]]:
    """
    Reranks results from multiple retrievers (e.g. vector similarity + keyword
    overlap) using Reciprocal Rank Fusion — the standard technique production
    hybrid-search systems (Elasticsearch, Weaviate, etc.) use to combine
    rankings from retrievers whose raw scores aren't on comparable scales
    (FAISS L2 distance vs. a 0..1 keyword-overlap ratio). Each item's fused
    score is the sum, across every list it appears in, of 1/(k_constant + rank);
    items ranked highly by multiple retrievers naturally float to the top.
    """
    scores: Dict[tuple, float] = {}
    items: Dict[tuple, Dict[str, Any]] = {}
    for results in result_lists:
        for rank, r in enumerate(results):
            meta = r.get("metadata", {})
            key = (meta.get("document_id"), meta.get("chunk_index"))
            scores[key] = scores.get(key, 0.0) + 1.0 / (k_constant + rank + 1)
            if key not in items:
                items[key] = r

    ranked_keys = sorted(scores.keys(), key=lambda key: scores[key], reverse=True)
    return [{**items[key], "rerank_score": scores[key]} for key in ranked_keys]

# Fallback basic text searcher class in case FAISS/Embeddings fail to initialize
class BasicTextSearcher:
    """
    A pure Python fallback semantic-ish searcher based on overlap/keyword matching
    if FAISS or remote embeddings are offline or fail to compile on Python 3.14.

    Persists to disk (see save/load) so that documents already indexed here are
    not lost on process restart — otherwise, whenever FAISS/Gemini embeddings are
    unavailable, a restart would silently make every previously-uploaded document
    unsearchable even though it still shows as COMPLETED in the database.
    """
    def __init__(self):
        self.chunks: List[str] = []
        self.metadatas: List[Dict[str, Any]] = []

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        self.chunks.extend(texts)
        self.metadatas.extend(metadatas)

    def remove_by_document_id(self, document_id: str) -> int:
        keep = [i for i, m in enumerate(self.metadatas) if m.get("document_id") != document_id]
        removed = len(self.metadatas) - len(keep)
        self.chunks = [self.chunks[i] for i in keep]
        self.metadatas = [self.metadatas[i] for i in keep]
        return removed

    def reconcile(self, valid_document_ids: Set[str]) -> int:
        keep = [i for i, m in enumerate(self.metadatas) if m.get("document_id") in valid_document_ids]
        removed = len(self.metadatas) - len(keep)
        self.chunks = [self.chunks[i] for i in keep]
        self.metadatas = [self.metadatas[i] for i in keep]
        return removed

    def save(self, index_dir: str) -> None:
        path = os.path.join(index_dir, FALLBACK_INDEX_FILENAME)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"chunks": self.chunks, "metadatas": self.metadatas}, f)
            logger.info(f"Fallback text index persisted to disk at {path} ({len(self.chunks)} chunk(s)).")
        except Exception as e:
            logger.error(f"Failed to persist fallback text index: {e}")

    def load(self, index_dir: str) -> None:
        path = os.path.join(index_dir, FALLBACK_INDEX_FILENAME)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.chunks = data.get("chunks", [])
            self.metadatas = data.get("metadatas", [])
            logger.info(f"Fallback text index loaded from disk at {path} ({len(self.chunks)} chunk(s)).")
        except Exception as e:
            logger.error(f"Failed to load fallback text index from {path}: {e}")

    def similarity_search(self, query: str, k: int = 5, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # Simple query term overlap ranking, restricted to the requesting user's own documents
        query_words = set(query.lower().split())
        results = []

        for idx, chunk in enumerate(self.chunks):
            meta = self.metadatas[idx]
            if user_id is not None and meta.get("user_id") != user_id:
                continue
            chunk_words = set(chunk.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            # Calculate a pseudo score
            score = overlap / (len(query_words) + 1)
            results.append((score, chunk, meta))

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
        self.fallback_db.load(self.index_dir)
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
                model="models/gemini-embedding-001",
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
        # Always feed the fallback, and persist it immediately so it survives a restart
        self.fallback_db.add_texts(texts, metadatas)
        self.fallback_db.save(self.index_dir)
        logger.info(f"Indexing {len(texts)} chunk(s) into vector store (metadata sample: {metadatas[0] if metadatas else None})")

        if self.embeddings is None:
            logger.warning("Embeddings not initialized. Chunks saved only to fallback text index.")
            return

        try:
            # pyrefly: ignore [missing-import]
            from langchain_community.vectorstores import FAISS
            if self.db is None:
                self.db = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
            else:
                self.db.add_texts(texts, metadatas=metadatas)

            # Save the index locally
            self.db.save_local(self.index_dir)
            logger.info(f"FAISS index successfully updated and saved to disk at {self.index_dir}.")
        except Exception as e:
            logger.error(f"Error adding chunks to FAISS index: {e}")
            # Do not raise, we have the fallback database

    def search(self, query: str, k: int = 5, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: casts a wider net with both FAISS semantic vector
        similarity and keyword overlap search (BasicTextSearcher), then
        reranks the combined candidate pool with Reciprocal Rank Fusion (see
        `_reciprocal_rank_fusion`) rather than a naive vector-first
        concatenation. This catches cases embedding similarity alone can miss
        (exact codes, names, dates) while still benefiting from semantic
        matching, and a chunk ranked well by *both* retrievers is correctly
        prioritized over one only one retriever liked.
        Restricted to the given user's own uploaded documents (if user_id is provided).
        Returns a list of dictionaries with 'page_content' and 'metadata'.
        """
        fetch_k = max(k * 3, 15)  # wider candidate pool feeds the reranker

        vector_results: List[Dict[str, Any]] = []
        if self.db is not None and self.embeddings is not None:
            try:
                filter_ = {"user_id": user_id} if user_id is not None else None
                raw_results = self.db.similarity_search_with_score(query, k=fetch_k, filter=filter_)
                vector_results = [
                    {"page_content": doc.page_content, "metadata": doc.metadata, "score": float(score)}
                    for doc, score in raw_results
                ]
            except Exception as e:
                logger.error(f"FAISS search failed: {e}. Continuing with keyword search only.")

        keyword_results = self.fallback_db.similarity_search(query, k=fetch_k, user_id=user_id)

        results = _reciprocal_rank_fusion([vector_results, keyword_results])[:k]

        retrieved_docs = sorted({r.get("metadata", {}).get("filename", "Unknown Document") for r in results})
        logger.info(
            f"Hybrid retrieval for query {query!r} (user_id={user_id}): "
            f"{len(vector_results)} vector hit(s), {len(keyword_results)} keyword hit(s), "
            f"{len(results)} reranked result(s) from document(s): {retrieved_docs}"
        )
        return results

    def remove_document(self, document_id: str) -> None:
        """
        Removes all chunks belonging to `document_id` from both the FAISS index and
        the fallback text index, and persists the change. Must be called whenever a
        document is deleted, so it stops being a source of truth for retrieval —
        otherwise its chunks silently linger in the index forever.
        """
        removed_fallback = self.fallback_db.remove_by_document_id(document_id)
        if removed_fallback:
            self.fallback_db.save(self.index_dir)
            logger.info(f"Removed {removed_fallback} chunk(s) for document {document_id} from fallback text index.")

        if self.db is not None:
            try:
                matching_ids = [
                    fid for fid, doc in self.db.docstore._dict.items()
                    if doc.metadata.get("document_id") == document_id
                ]
                if matching_ids:
                    self.db.delete(ids=matching_ids)
                    self.db.save_local(self.index_dir)
                    logger.info(f"Removed {len(matching_ids)} chunk(s) for document {document_id} from FAISS index.")
            except Exception as e:
                logger.error(f"Could not remove document {document_id} chunks from FAISS index: {e}")

    def reconcile_with_documents(self, valid_document_ids: Set[str]) -> None:
        """
        Removes any indexed chunks whose document_id is not in `valid_document_ids`
        (e.g. leftover from documents that were deleted before this cleanup existed,
        or residual demo/test data). Called at startup so the index always reflects
        only documents that currently exist in the database — never bundled demo
        content or orphaned data from previous runs.
        """
        removed_fallback = self.fallback_db.reconcile(valid_document_ids)
        if removed_fallback:
            self.fallback_db.save(self.index_dir)
            logger.info(f"Reconciliation removed {removed_fallback} orphaned/stale chunk(s) from fallback text index.")

        if self.db is not None:
            try:
                stale_ids = [
                    fid for fid, doc in self.db.docstore._dict.items()
                    if doc.metadata.get("document_id") not in valid_document_ids
                ]
                if stale_ids:
                    self.db.delete(ids=stale_ids)
                    self.db.save_local(self.index_dir)
                    logger.info(f"Reconciliation removed {len(stale_ids)} orphaned/stale chunk(s) from FAISS index.")
            except Exception as e:
                logger.error(f"Could not reconcile FAISS index against current documents: {e}")


# Singleton instance
vector_store = VectorStoreService()
