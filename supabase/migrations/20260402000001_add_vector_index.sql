-- Add IVFFlat vector similarity index for document_chunks
-- Requires rows to exist for IVFFlat training; use IF NOT EXISTS guard
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE indexname = 'idx_chunks_embedding_ivf'
    ) THEN
        CREATE INDEX idx_chunks_embedding_ivf
        ON document_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100);
    END IF;
END
$$;
