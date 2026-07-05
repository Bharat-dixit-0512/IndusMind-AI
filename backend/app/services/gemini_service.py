import os
import re
import logging
from typing import List, Dict, Any, Tuple
import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)


def format_chunks_as_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved FAISS chunks into a `[Source: filename]\\nContent: ...` block,
    shared by every agent that builds a Gemini prompt from retrieved context.
    """
    context_str = ""
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        filename = meta.get("filename", "Unknown Document")
        context_str += f"[Source: {filename}]\nContent: {chunk.get('page_content', '')}\n\n"
    return context_str


class GeminiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.active = False
        self._init_client()

    def _init_client(self):
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.active = True
            logger.info("Gemini API client initialized successfully.")
        else:
            logger.warning("GEMINI_API_KEY is not set. Gemini queries will run in mock mode.")
            self.active = False

    def query_gemini_with_context(
        self,
        query: str,
        vector_chunks: List[Dict[str, Any]],
        graph_triples: List[Dict[str, Any]]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Sends the query, vector chunks, and graph context to Gemini 2.5 Flash.
        Instructs Gemini to answer using ONLY the provided contexts (i.e. the user's
        own uploaded documents) and to output inline citations.
        Returns the text response and a list of citation dictionaries.

        If Gemini is not configured, or the call fails, falls back to a grounded,
        non-fabricated answer built directly from the retrieved chunks (never demo data).
        """
        if not vector_chunks and not graph_triples:
            logger.info("No context retrieved from FAISS/graph for query: %r", query)
            return "No relevant information was found in the uploaded documents.", []

        if not self.active:
            logger.info("Gemini service offline (no API key). Building grounded fallback from retrieved chunks.")
            return self._build_grounded_fallback(vector_chunks)

        # Format Vector context
        context_str = format_chunks_as_context(vector_chunks)

        # Format Graph context
        graph_str = ""
        for edge in graph_triples:
            graph_str += f"Relation: ({edge.get('source')}) -[{edge.get('label')}]-> ({edge.get('target')})\n"

        system_prompt = f"""
You are an AI knowledge assistant. You answer questions using ONLY the context retrieved
from the user's own uploaded documents (and, if present, their knowledge graph). You have
no other source of information — never use outside or general knowledge to fill in gaps.

Context Datasets:
1. RETRIEVED DOCUMENT EXCERPTS:
{context_str if context_str else "(none retrieved)"}

2. KNOWLEDGE GRAPH RELATIONSHIPS:
{graph_str if graph_str else "(none retrieved)"}

CRITICAL RULES:
1. Answer the user's question clearly and directly using only the context above.
2. Every fact or specification you state MUST be cited directly from the RETRIEVED DOCUMENT EXCERPTS.
3. Use inline brackets for citations, referencing the exact Source ID (e.g., `[Resume.pdf, Page 1]` or `[Contract.docx, Sheet: Logs]`).
4. If the context does not contain the answer, say exactly: "I could not find this information in the uploaded documents." Do not make up facts, and never invent details not present in the context.
"""

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                contents=[
                    {"role": "user", "parts": [f"System instruction: {system_prompt}\n\nUser Question: {query}"]}
                ]
            )

            answer = response.text.strip()
            citations = self._parse_citations(answer, vector_chunks)
            logger.info("Gemini answered query using %d retrieved chunk(s), %d citation(s) parsed.", len(vector_chunks), len(citations))
            return answer, citations
        except Exception as e:
            logger.error(f"Gemini query failed: {e}. Falling back to grounded chunk-based answer.")
            return self._build_grounded_fallback(vector_chunks)

    def _parse_citations(self, text: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parses text to find inline citations (e.g. [Filename.pdf, Page X])
        and maps them to original chunk records.
        """
        citations = []
        # Find matches like [Filename.pdf, Page 12] or [Filename.pdf, Chunk X] or [Filename.pdf]
        matches = re.findall(r'\[([^\]]+)\]', text)
        
        seen_filenames = set()
        for match in matches:
            parts = match.split(",")
            doc_name = parts[0].strip()
            
            if doc_name in seen_filenames:
                continue
                
            # Find the chunk that matches this document name to extract snippet
            matching_chunk = next(
                (c for c in chunks if c.get("metadata", {}).get("filename", "").lower() == doc_name.lower()),
                None
            )
            
            if matching_chunk:
                seen_filenames.add(doc_name)
                page = None
                if len(parts) > 1:
                    try:
                        # Extract digits
                        digits = re.findall(r'\d+', parts[1])
                        if digits:
                            page = int(digits[0])
                    except ValueError:
                        pass
                
                citations.append({
                    "document_name": doc_name,
                    "page_number": page,
                    "text": matching_chunk["page_content"][:200] + "..."  # Short summary snippet
                })
        return citations

    def _build_grounded_fallback(self, vector_chunks: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Builds a non-fabricated answer directly from retrieved FAISS chunks when
        Gemini reasoning is unavailable (no API key configured, or the API call failed).
        Never references demo/sample data — only the actual retrieved document excerpts.
        """
        if not vector_chunks:
            return "No relevant information was found in the uploaded documents.", []

        lines = ["_AI reasoning is currently unavailable — showing the most relevant excerpts found in your uploaded documents:_"]
        citations = []
        seen_filenames = set()
        for chunk in vector_chunks[:3]:
            meta = chunk.get("metadata", {})
            filename = meta.get("filename", "Unknown Document")
            chunk_idx = meta.get("chunk_index")
            content = (chunk.get("page_content") or "").strip()
            if not content:
                continue
            lines.append(f"\n**[{filename}]**\n{content[:1500]}")
            if filename not in seen_filenames:
                seen_filenames.add(filename)
                citations.append({
                    "document_name": filename,
                    "page_number": chunk_idx,
                    "text": content[:200] + ("..." if len(content) > 200 else "")
                })
        return "\n".join(lines), citations


gemini_service = GeminiService()
