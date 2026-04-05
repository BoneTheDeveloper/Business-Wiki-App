"""Integration tests for pgvector features (requires Docker + PostgreSQL).

These tests verify vector operations against a real PostgreSQL + pgvector database.
Run with: TEST_USE_DOCKER=true uv run pytest tests/ -v -m pgvector
"""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_pgvector_extension_installed(db_engine):
    """Verify pgvector extension is available and installed."""
    async with db_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        row = result.fetchone()
        assert row is not None, "pgvector extension not installed"
        assert row[0] == "vector"


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_vector_insert_and_query(db_session: AsyncSession):
    """Test inserting and querying vector embeddings via pgvector."""
    # Create a test document first (satisfies FK constraint)
    await db_session.execute(text("""
        INSERT INTO users (id, email, role, is_active)
        VALUES ('11111111-1111-1111-1111-111111111111', 'pgv@test.com', 'user', true)
    """))
    await db_session.execute(text("""
        INSERT INTO documents (id, user_id, filename, file_path, format, status, visibility)
        VALUES (
            '22222222-2222-2222-2222-222222222222',
            '11111111-1111-1111-1111-111111111111',
            'test.pdf', '/tmp/test.pdf', 'pdf', 'completed', 'private'
        )
    """))

    # Insert a chunk with a 1536-dim unit vector (non-zero to avoid NaN in cosine distance)
    embedding = "[1.0" + ", " + ", ".join(["0.0"] * 1535) + "]"
    await db_session.execute(text("""
        INSERT INTO document_chunks (id, document_id, content, chunk_index, embedding)
        VALUES (
            '33333333-3333-3333-3333-333333333333',
            '22222222-2222-2222-2222-222222222222',
            'test content for vector search', 0, CAST(:emb AS vector)
        )
    """), {"emb": embedding})

    # Query using cosine distance operator
    result = await db_session.execute(text("""
        SELECT content, 1 - (embedding <=> CAST(:emb AS vector)) AS similarity
        FROM document_chunks
        WHERE document_id = '22222222-2222-2222-2222-222222222222'
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT 5
    """), {"emb": embedding})
    rows = result.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "test content for vector search"
    assert abs(rows[0][1] - 1.0) < 0.001  # cosine similarity ~1.0 for identical vectors


@pytest.mark.pgvector
@pytest.mark.asyncio
async def test_vector_cosine_distance(db_session: AsyncSession):
    """Test cosine distance operator returns correct ordering."""
    # Setup: user + document
    await db_session.execute(text("""
        INSERT INTO users (id, email, role, is_active)
        VALUES ('44444444-4444-4444-4444-444444444444', 'cosine@test.com', 'user', true)
    """))
    await db_session.execute(text("""
        INSERT INTO documents (id, user_id, filename, file_path, format, status, visibility)
        VALUES (
            '55555555-5555-5555-5555-555555555555',
            '44444444-4444-4444-4444-444444444444',
            'cosine.pdf', '/tmp/cosine.pdf', 'pdf', 'completed', 'private'
        )
    """))

    # Insert chunks with different embeddings
    # Chunk A: unit vector [1, 0, 0, ...] (1536 dims)
    vec_a = "[1.0" + ", " + ", ".join(["0.0"] * 1535) + "]"
    # Chunk B: half vector [0.5, 0.5, 0.707, 0, ...] — different direction
    vec_b = "[0.5, 0.5, 0.707" + ", " + ", ".join(["0.0"] * 1533) + "]"

    await db_session.execute(text("""
        INSERT INTO document_chunks (id, document_id, content, chunk_index, embedding)
        VALUES (
            '66666666-6666-6666-6666-666666666666',
            '55555555-5555-5555-5555-555555555555',
            'chunk A', 0, CAST(:emb AS vector)
        )
    """), {"emb": vec_a})

    await db_session.execute(text("""
        INSERT INTO document_chunks (id, document_id, content, chunk_index, embedding)
        VALUES (
            '77777777-7777-7777-7777-777777777777',
            '55555555-5555-5555-5555-555555555555',
            'chunk B', 1, CAST(:emb AS vector)
        )
    """), {"emb": vec_b})

    # Query with vec_a — chunk A should rank first (identical → distance = 0)
    result = await db_session.execute(text("""
        SELECT content, 1 - (embedding <=> CAST(:query AS vector)) AS similarity
        FROM document_chunks
        WHERE document_id = '55555555-5555-5555-5555-555555555555'
        ORDER BY embedding <=> CAST(:query AS vector)
    """), {"query": vec_a})
    rows = result.fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "chunk A"  # identical vector first
    assert rows[0][1] > rows[1][1]  # higher similarity for closer match
