import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service, format_chunks_as_context

logger = logging.getLogger(__name__)


class KnowledgeAgent:
    def __init__(self):
        self.active = gemini_service.active

    def retrieve_sop_or_manual(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Retrieves SOP/manual/reference content from the user's own uploaded documents
        and constructs an authoritative, cited answer. Never fabricates an answer —
        if no relevant content was retrieved, or Gemini is unavailable, falls back to
        a grounded, non-fabricated response built from the retrieved chunks only.
        """
        logger.info("KnowledgeAgent retrieving info for query: %r (%d context chunk(s))", query, len(context_chunks))

        if not context_chunks:
            logger.info("KnowledgeAgent: no context chunks retrieved, returning not-found response.")
            return self._not_found_response()

        context_str = format_chunks_as_context(context_chunks)

        prompt = f"""
You are a knowledge assistant. Your task is to answer queries relating to procedures, manuals,
and reference documentation using ONLY the context below — never introduce facts not present in it.

Context:
---
{context_str}
---

User Query: {query}

Please formulate an authoritative answer citing details from the text.
If the context does not contain the answer, respond exactly with:
"I could not find this information in the uploaded documents."
Include a confidence score (from 0.00 to 1.00), a list of step-by-step reasoning steps, and evidence items.

Return your response in EXACT JSON format with these keys:
- "response": (string, markdown allowed, answering the query clearly with citations in brackets like [filename.pdf])
- "confidence_score": (float, e.g. 0.94)
- "reasoning_steps": list of strings detailing the search & correlation logic
- "evidence_base": list of strings of specific sections, rules, or values extracted

Do not include any extra text outside the JSON.
"""

        try:
            if not self.active:
                logger.info("KnowledgeAgent: Gemini unavailable, building grounded fallback response.")
                return self._grounded_fallback_response(context_chunks)

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"KnowledgeAgent query failed: {e}. Falling back to grounded chunk-based response.")
            return self._grounded_fallback_response(context_chunks)

    def _not_found_response(self) -> Dict[str, Any]:
        return {
            "response": "I could not find this information in the uploaded documents.",
            "confidence_score": 0.0,
            "reasoning_steps": ["No matching content was retrieved from the uploaded documents."],
            "evidence_base": []
        }

    def _grounded_fallback_response(self, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Non-fabricated fallback used when Gemini is unavailable but relevant chunks
        were retrieved — surfaces the raw excerpts instead of a hardcoded demo answer.
        """
        filenames = sorted({c.get("metadata", {}).get("filename", "Unknown Document") for c in context_chunks})
        excerpt = "\n\n".join(
            f"**[{c.get('metadata', {}).get('filename', 'Unknown Document')}]**\n{(c.get('page_content') or '').strip()[:1500]}"
            for c in context_chunks[:3]
        )
        return {
            "response": f"_AI reasoning is currently unavailable — showing the most relevant excerpts found in your uploaded documents:_\n\n{excerpt}",
            "confidence_score": 0.3,
            "reasoning_steps": [
                "Retrieved matching content from uploaded documents.",
                "Gemini reasoning unavailable — returning raw excerpts instead of a synthesized answer."
            ],
            "evidence_base": filenames
        }


knowledge_agent = KnowledgeAgent()
