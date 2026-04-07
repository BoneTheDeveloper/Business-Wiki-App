"""Chainlit step builders for RAG pipeline visualization."""
import chainlit as cl

from api.models import StepsDetail, ChunkResult


async def show_embedding_step(steps: StepsDetail) -> None:
    """Render embedding generation step with timing."""
    async with cl.Step(name="Embedding", type="tool") as step:
        step.input = "Generate query embedding"
        step.output = f"Vector created ({steps.embedding.dimensions}d)"
        step.metadata = {
            "model": "gemini-embedding-001",
            "dimensions": steps.embedding.dimensions,
            "latency_ms": round(steps.embedding.latency_ms, 1),
        }


async def show_retrieval_step(
    steps: StepsDetail,
    chunks: list[ChunkResult],
) -> None:
    """Render retrieval step with chunk details."""
    async with cl.Step(name="Retrieval", type="tool") as step:
        step.input = "Semantic search in vector store"
        step.output = f"Found {steps.retrieval.chunks_count} chunks"
        step.metadata = {
            "chunks_count": steps.retrieval.chunks_count,
            "latency_ms": round(steps.retrieval.latency_ms, 1),
        }

        # Show top chunks as side elements with similarity scores
        for i, chunk in enumerate(chunks[:8]):
            content_preview = chunk.content[:600]
            if len(chunk.content) > 600:
                content_preview += "..."

            element = cl.Text(
                content=content_preview,
                name=f"[{chunk.similarity:.3f}] {chunk.filename}",
                display="side",
            )
            step.elements.append(element)


async def show_generation_step(steps: StepsDetail, model: str) -> None:
    """Render LLM generation step with token usage."""
    async with cl.Step(name="Generation", type="llm") as step:
        step.input = "Generate response from context"
        step.output = f"Completed ({steps.generation.tokens_out} tokens)"
        step.metadata = {
            "model": model,
            "tokens_in": steps.generation.tokens_in,
            "tokens_out": steps.generation.tokens_out,
            "latency_ms": round(steps.generation.latency_ms, 1),
        }
