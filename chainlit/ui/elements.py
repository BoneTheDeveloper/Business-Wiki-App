"""Custom Chainlit elements for RAG metadata display."""
import chainlit as cl

from api.models import ChunkResult, StepsDetail


def build_chunk_table(chunks: list[ChunkResult]) -> str:
    """Build markdown table of retrieved chunks with similarity scores."""
    if not chunks:
        return "No chunks retrieved."

    header = "| # | Source | Similarity | Preview |\n|---|--------|------------|----------|\n"
    rows = []
    for i, chunk in enumerate(chunks[:10], 1):
        preview = chunk.content[:80].replace("\n", " ").replace("|", "\\|")
        rows.append(f"| {i} | {chunk.filename} | {chunk.similarity:.4f} | {preview} |")

    return header + "\n".join(rows)


def build_latency_summary(steps: StepsDetail, total_ms: float) -> str:
    """Build markdown latency summary of pipeline steps."""
    if total_ms <= 0:
        return "No pipeline data."

    e_pct = steps.embedding.latency_ms / total_ms * 100 if total_ms else 0
    r_pct = steps.retrieval.latency_ms / total_ms * 100 if total_ms else 0
    g_pct = steps.generation.latency_ms / total_ms * 100 if total_ms else 0

    return (
        f"**Pipeline Latency: {total_ms:.0f}ms**\n\n"
        f"| Step | Time | % of Total |\n"
        f"|------|------|------------|\n"
        f"| Embedding | {steps.embedding.latency_ms:.1f}ms | {e_pct:.0f}% |\n"
        f"| Retrieval | {steps.retrieval.latency_ms:.1f}ms | {r_pct:.0f}% |\n"
        f"| Generation | {steps.generation.latency_ms:.1f}ms | {g_pct:.0f}% |"
    )


async def send_chunk_sidebar(chunks: list[ChunkResult]) -> None:
    """Push top chunks to the element sidebar for inspection."""
    elements = []
    for i, chunk in enumerate(chunks[:8]):
        elements.append(
            cl.Text(
                content=chunk.content[:2000],
                name=f"[{chunk.similarity:.3f}] {chunk.filename} #{i + 1}",
                display="side",
            )
        )
    await cl.ElementSidebar.set_elements(elements)
    await cl.ElementSidebar.set_title("Retrieved Chunks")
