"""LLM service for RAG-powered chat responses."""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI

from app.config import settings


class LLMService:
    """LLM integration for chat with document context."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

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
        if not settings.OPENAI_API_KEY:
            return {
                "answer": "OpenAI API key not configured. Please set OPENAI_API_KEY.",
                "sources": [],
                "model": "none",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0}
            }

        # Build context from chunks
        context_text = "\n\n---\n\n".join([
            f"[Document: {c['filename']}]\n{c['content'][:1000]}"
            for c in context_chunks[:5]  # Limit context size
        ])

        # System prompt for RAG
        system_prompt = """You are a helpful assistant that answers questions based on the provided document context.

Rules:
- Only use information from the provided context to answer questions
- If the answer is not in the context, say "I couldn't find that information in the documents"
- Be concise but thorough
- Cite sources when possible using the document names
- Format your response clearly with bullet points if needed"""

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided (last 4 messages)
        if conversation_history:
            messages.extend(conversation_history[-4:])

        # Add current query with context
        messages.append({
            "role": "user",
            "content": f"Context from documents:\n{context_text}\n\nQuestion: {query}"
        })

        # Generate response
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )

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
            "answer": response.choices[0].message.content,
            "sources": sources,
            "model": self.model,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }


# Singleton instance
llm_service = LLMService()
