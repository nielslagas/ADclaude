-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS pgvector;

-- Case table for storing client cases
CREATE TABLE "Case" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  user_id UUID NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE
);

-- Document table for storing uploaded documents
CREATE TABLE "Document" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  mimetype TEXT NOT NULL,
  size INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'processing',
  case_id UUID NOT NULL REFERENCES "Case"(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  error TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE
);

-- Document chunks for vector search
CREATE TABLE "DocumentChunk" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES "Document"(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  metadata JSONB,
  embedding vector(768),  -- Dimension for Gemini embeddings
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE
);

-- Report table for storing generated reports
CREATE TABLE "Report" (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  template_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'processing',
  case_id UUID NOT NULL REFERENCES "Case"(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  content JSONB,
  metadata JSONB,
  error TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
  updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for performance
CREATE INDEX idx_case_user_id ON "Case" (user_id);
CREATE INDEX idx_case_status ON "Case" (status);
CREATE INDEX idx_document_case_id ON "Document" (case_id);
CREATE INDEX idx_document_user_id ON "Document" (user_id);
CREATE INDEX idx_document_status ON "Document" (status);
CREATE INDEX idx_document_chunk_document_id ON "DocumentChunk" (document_id);
CREATE INDEX idx_report_case_id ON "Report" (case_id);
CREATE INDEX idx_report_user_id ON "Report" (user_id);
CREATE INDEX idx_report_status ON "Report" (status);

-- Create vector index for document chunks
CREATE INDEX idx_document_chunk_embedding ON "DocumentChunk" USING hnsw (embedding vector_l2_ops);

-- Set up Row Level Security (RLS) policies
-- Enable RLS on tables
ALTER TABLE "Case" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Document" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "DocumentChunk" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "Report" ENABLE ROW LEVEL SECURITY;

-- Create policies to restrict access to user's own data
CREATE POLICY case_user_access ON "Case" 
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY document_user_access ON "Document" 
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY document_chunk_user_access ON "DocumentChunk" 
  FOR ALL USING (
    document_id IN (
      SELECT id FROM "Document" WHERE user_id = auth.uid()
    )
  );

CREATE POLICY report_user_access ON "Report" 
  FOR ALL USING (user_id = auth.uid());

-- Helper function for vector search
CREATE OR REPLACE FUNCTION search_document_chunks_vector(
  query_embedding vector(768),
  case_id UUID,
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 10
) RETURNS TABLE (
  id UUID,
  document_id UUID,
  content TEXT,
  chunk_index INTEGER,
  metadata JSONB,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id,
    c.document_id,
    c.content,
    c.chunk_index,
    c.metadata,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM 
    "DocumentChunk" c
  JOIN 
    "Document" d ON c.document_id = d.id
  WHERE 
    d.case_id = search_document_chunks_vector.case_id
    AND (1 - (c.embedding <=> query_embedding)) > match_threshold
  ORDER BY 
    c.embedding <=> query_embedding
  LIMIT 
    match_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;