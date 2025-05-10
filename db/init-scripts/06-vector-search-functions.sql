-- Vector Search Functions
-- This script adds PostgreSQL functions for searching document chunks by vector similarity

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
    RETURN QUERY
    SELECT
        c.chunk_id as id,
        c.document_id,
        c.content,
        c.metadata,
        1 - (c.embedding <=> query_embedding) as similarity
    FROM
        document_embeddings c
    JOIN
        document d ON c.document_id = d.id
    WHERE
        d.case_id = search_document_chunks_vector.case_id
        AND (1 - (c.embedding <=> query_embedding)) >= match_threshold
    ORDER BY
        c.embedding <=> query_embedding
    LIMIT
        match_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to search document chunks by text (converts text to embedding first)
CREATE OR REPLACE FUNCTION search_document_chunks_text(
    query_text text,
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
DECLARE
    query_embedding vector(768);
BEGIN
    -- This is a placeholder. In a real implementation, this would call an external service
    -- to generate an embedding for the query_text.
    -- For demonstration purposes, we use a simple random embedding
    query_embedding := (SELECT array_agg(random()) FROM generate_series(1, 768))::vector(768);
    
    RETURN QUERY
    SELECT * FROM search_document_chunks_vector(
        query_embedding,
        case_id,
        match_threshold, 
        match_count
    );
END;
$$ LANGUAGE plpgsql;

-- Create a function to handle direct text search as fallback
CREATE OR REPLACE FUNCTION direct_text_search(
    query_text text,
    case_id uuid,
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
    RETURN QUERY
    SELECT
        dc.id as id,
        d.id as document_id,
        dc.content,
        dc.metadata,
        1.0 as similarity  -- Fixed similarity score for direct matches
    FROM
        document_chunk dc
    JOIN
        document d ON dc.document_id = d.id
    WHERE
        d.case_id = direct_text_search.case_id
        AND dc.content ILIKE '%' || query_text || '%'
    ORDER BY
        -- Simple ranking by length of content (shorter content might be more relevant)
        length(dc.content)
    LIMIT
        match_count;
END;
$$ LANGUAGE plpgsql;

-- Function to combine vector search and direct text search (hybrid approach)
CREATE OR REPLACE FUNCTION hybrid_document_search(
    query_text text,
    case_id uuid,
    vector_weight float DEFAULT 0.7,
    match_threshold float DEFAULT 0.5,
    match_count int DEFAULT 10
)
RETURNS TABLE (
    id text,
    document_id uuid,
    content text,
    metadata jsonb,
    similarity float,
    search_method text
) AS $$
DECLARE
    vector_results record;
    text_results record;
    vector_count int;
BEGIN
    -- First try vector search
    SELECT count(*) INTO vector_count
    FROM search_document_chunks_vector(
        (SELECT array_agg(random()) FROM generate_series(1, 768))::vector(768),
        case_id,
        match_threshold,
        1
    );
    
    -- If we have vector embeddings, use them
    IF vector_count > 0 THEN
        RETURN QUERY
        SELECT
            v.id,
            v.document_id,
            v.content,
            v.metadata,
            v.similarity * vector_weight as similarity,
            'vector'::text as search_method
        FROM search_document_chunks_text(
            query_text,
            case_id, 
            match_threshold,
            match_count
        ) v;
    ELSE
        -- Fallback to direct text search if no vectors available
        RETURN QUERY
        SELECT
            t.id,
            t.document_id,
            t.content,
            t.metadata,
            t.similarity * (1 - vector_weight) as similarity,
            'text'::text as search_method
        FROM direct_text_search(
            query_text,
            case_id,
            match_count
        ) t;
    END IF;
END;
$$ LANGUAGE plpgsql;