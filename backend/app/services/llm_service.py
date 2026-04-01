"""LLM service for RAG-powered chat responses using Google Gemini."""
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

from app.config import settings


class LLMService:
    """LLM integration for chat with document context."""

    def __init__(self):
        self._client: Optional[genai.Client] = None
        self.model = "gemini-2.0-flash"

    @property
    def client(self) -> genai.Client:
        """Lazy-init client to avoid crash when GOOGLE_API_KEY is empty."""
        if self._client is None:
            self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        return self._client

    async def chat(
        self,
        query: str,
        context_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate chat response with RAG context.

        Args:
            query: User's question
            context_chunks: Retrieved document chunks for context
            conversation_history: Previous messages for multi-turn chat

        Returns:
            Dict with answer, sources, model, and usage info
        """
        if not settings.GOOGLE_API_KEY:
            return {
                "answer": "Google API key not configured. Please set GOOGLE_API_KEY.",
                "sources": [],
                "model": "none",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0}
            }

        # Build context from chunks
        context_text = "\n\n---\n\n".join([
            f"[Document: {c['filename']}]\n{c['content'][:1000]}"
            for c in context_chunks[:5]
        ])

        # System prompt for RAG
        system_prompt = """You are a helpful assistant that answers questions based on the provided document context.

Rules:
- Only use information from the provided context to answer questions
- If the answer is not in the context, say "I couldn't find that information in the documents"
- Be concise but thorough
- Cite sources when possible using the document names
- Format your response clearly with bullet points if needed"""

        # Build Gemini contents from conversation history
        gemini_contents = []
        if conversation_history:
            for msg in conversation_history[-4:]:
                role = "model" if msg.get("role") == "assistant" else "user"
                gemini_contents.append({
                    "role": role,
                    "parts": [{"text": msg.get("content", "")}]
                })

        # Add current query with context
        gemini_contents.append({
            "role": "user",
            "parts": [{"text": f"Context from documents:\n{context_text}\n\nQuestion: {query}"}]
        })

        # Generate response
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=gemini_contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=1000,
                    temperature=0.7
                )
            )
        except Exception as e:
            return {
                "answer": f"Error generating response: {str(e)[:200]}",
                "sources": [],
                "model": self.model,
                "usage": {"prompt_tokens": 0, "completion_tokens": 0}
            }

        # Safely extract response text (raises ValueError on safety blocks)
        try:
            answer = response.text
        except (ValueError, AttributeError):
            answer = "I couldn't generate a response due to safety filters."

        # Safely extract usage metadata
        usage_meta = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

        # Build sources list
        sources = [
            {
                "document_id": c.get("document_id", ""),
                "filename": c.get("filename", ""),
                "chunk_id": c.get("chunk_id", ""),
                "similarity": c.get("similarity", 0),
                "page": c.get("metadata", {}).get("page")
            }
            for c in context_chunks[:5]
        ]

        return {
            "answer": answer or "I couldn't generate a response.",
            "sources": sources,
            "model": self.model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens
            }
        }


# Singleton instance
llm_service = LLMService()
