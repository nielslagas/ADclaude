-- Create a function for vector similarity search across document chunks
-- This function is optimized for pgvector and uses the <=> operator for cosine distance

-- First make sure the document_embeddings table has an index for fast vector searches
CREATE INDEX IF NOT EXISTS document_embeddings_embedding_idx ON document_embeddings USING hnsw (embedding vector_cosine_ops) WITH (ef_construction=100, m=16);

-- Create function to search document chunks by vector similarity
CREATE OR REPLACE FUNCTION search_document_chunks_vector(
    query_embedding vector(768),
    case_id uuid,
    match_threshold float DEFAULT 0.6,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id text,
    document_id uuid,
    content text,
    metadata jsonb,
    similarity float
) AS $$
BEGIN
    -- Return empty results if missing required parameters
    IF query_embedding IS NULL OR case_id IS NULL THEN
        RETURN;
    END IF;

    -- Join with document table to filter by case_id
    RETURN QUERY
    SELECT 
        dc.chunk_id::text as id,
        dc.document_id,
        dc.content,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) as similarity
    FROM 
        document_embeddings dc
    JOIN 
        document d ON dc.document_id = d.id
    WHERE 
        d.case_id = search_document_chunks_vector.case_id
        AND 1 - (dc.embedding <=> query_embedding) >= match_threshold
    ORDER BY 
        dc.embedding <=> query_embedding
    LIMIT 
        match_count;
END;
$$ LANGUAGE plpgsql;