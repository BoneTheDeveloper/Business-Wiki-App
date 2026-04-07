"""Chainlit RAG Playground — interactive chat with full RAG pipeline observability."""
import chainlit as cl

from api.client import chat, search, list_documents
from api.models import ChatResponse
from ui.steps import show_embedding_step, show_retrieval_step, show_generation_step
from ui.elements import build_chunk_table, build_latency_summary, send_chunk_sidebar


@cl.on_chat_start
async def start():
    """Initialize chat session and load available documents."""
    doc_names: list[str] = []
    doc_count = 0

    try:
        docs_resp = await list_documents()
        doc_names = [d.filename for d in docs_resp.documents]
        doc_count = docs_resp.total
    except Exception:
        doc_names = []
        doc_count = 0

    cl.user_session.set("document_names", doc_names)
    cl.user_session.set("doc_count", doc_count)
    cl.user_session.set("conversation_history", [])

    if doc_count > 0:
        doc_list = ", ".join(doc_names[:5])
        if len(doc_names) > 5:
            doc_list += f" (+ {len(doc_names) - 5} more...)"
        content = (
            "## RAG Playground\n\n"
            "Ask questions about your uploaded documents. "
            "I'll search through them and show retrieved chunks with similarity scores. "
            "Each step of the RAG pipeline is visualized with latency metrics.\n\n"
            f"**{doc_count} documents indexed:** {doc_list}"
        )
    else:
        content = "RAG Playground ready. Ask a question about your documents."

    await cl.Message(content=content).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle user message with full RAG pipeline observability."""
    query = message.content.strip()
    if not query or len(query) < 3:
        await cl.Message(content="Query must be at least 3 characters.").send()
        return

    conversation_history: list[dict] = cl.user_session.get("conversation_history") or []

    conversation_history.append({"role": "user", "content": query})
    cl.user_session.set("conversation_history", conversation_history)

    try:
        # Call backend chat endpoint with full observability
        data: ChatResponse = await chat(
            query=query,
            top_k=5,
            conversation_history=conversation_history,
        )

        if not data or not data.response:
            await cl.Message(
                content="No response from backend. Check if PLAYGROUND_ENABLED=true on your backend."
            ).send()
            return

        # Update conversation history with assistant response
        conversation_history.append({"role": "assistant", "content": data.response})
        cl.user_session.set("conversation_history", conversation_history)

        # Show pipeline steps with metrics
        await show_embedding_step(data.steps)
        await show_retrieval_step(data.steps, data.chunks)
        await show_generation_step(data.steps, data.model)

        # Display retrieved chunks table
        chunk_table_md = build_chunk_table(data.chunks)
        await cl.Message(content=f"### Retrieved Chunks\n\n{chunk_table_md}").send()

        # Show latency summary
        latency_md = build_latency_summary(data.steps, data.total_latency_ms)
        await cl.Message(content=latency_md).send()

        # Push chunks to sidebar for inspection
        await send_chunk_sidebar(data.chunks)

        # Send final answer
        await cl.Message(content=data.response).send()

    except Exception as e:
        # Sanitize error — never expose raw exception details
        await cl.Message(content="**Error:** Request failed. Check backend logs for details.").send()
