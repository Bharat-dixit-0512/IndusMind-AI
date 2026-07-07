import logging
from typing import Dict, Any, List
import google.generativeai as genai
import json
from app.services.gemini_service import gemini_service, format_chunks_as_context, extractive_answer, not_found_message

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
            return self._not_found_response(query)

        context_str = format_chunks_as_context(context_chunks)

        prompt = f"""
You are a senior knowledge specialist briefing someone who needs the complete answer in one
pass, not a follow-up round of questions. Answer using ONLY the context below — never
introduce facts not present in it — but be thorough: pull in every relevant detail, figure,
and reference the context actually contains, organized clearly (short paragraphs or bullets
for multi-part answers), the way a well-paid expert consultant would brief a client.

Context:
---
{context_str}
---

User Query: {query}

Please formulate an authoritative, complete answer citing details from the text.
If the context is only partially relevant, answer the part(s) it supports and explicitly say
which part(s) are not covered by the uploaded documents.
If the context does not contain the answer at all, respond exactly with:
"{not_found_message(query)}"
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
                logger.info("KnowledgeAgent: Gemini unavailable, building extractive summary response.")
                return self._extractive_response(query, context_chunks)

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text.strip())
        except Exception as e:
            logger.error(f"KnowledgeAgent query failed: {e}. Falling back to extractive summary.")
            return self._extractive_response(query, context_chunks)

    def _not_found_response(self, query: str) -> Dict[str, Any]:
        return {
            "response": not_found_message(query),
            "confidence_score": 0.0,
            "reasoning_steps": ["No matching content was retrieved from the uploaded documents."],
            "evidence_base": []
        }

    def _extractive_response(self, query: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Non-fabricated fallback used when Gemini is unavailable — builds a concise
        extractive summary from the retrieved chunks (never a raw excerpt dump,
        and never hardcoded/demo content).
        """
        summary, citations = extractive_answer(query, context_chunks)
        if not citations:
            return self._not_found_response(query)
        return {
            "response": summary,
            "confidence_score": 0.3,
            "reasoning_steps": [
                "Retrieved matching content from uploaded documents.",
                "Gemini reasoning unavailable — returning an extractive summary instead of a synthesized answer."
            ],
            "evidence_base": sorted({c["document_name"] for c in citations})
        }


knowledge_agent = KnowledgeAgent()
