-- Create core tables for the AD-Rapport Generator

-- Case table
CREATE TABLE IF NOT EXISTS case_table (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document table
CREATE TABLE IF NOT EXISTS document (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES case_table(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    mimetype VARCHAR(255) NOT NULL,
    size INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'processing',
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document chunk table
CREATE TABLE IF NOT EXISTS document_chunk (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES document(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report table
CREATE TABLE IF NOT EXISTS report (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES case_table(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    template_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'processing',
    content JSONB DEFAULT '{}',
    metadata JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS case_user_id_idx ON case_table(user_id);
CREATE INDEX IF NOT EXISTS case_status_idx ON case_table(status);
CREATE INDEX IF NOT EXISTS document_case_id_idx ON document(case_id);
CREATE INDEX IF NOT EXISTS document_user_id_idx ON document(user_id);
CREATE INDEX IF NOT EXISTS document_status_idx ON document(status);
CREATE INDEX IF NOT EXISTS document_chunk_document_id_idx ON document_chunk(document_id);
CREATE INDEX IF NOT EXISTS report_case_id_idx ON report(case_id);
CREATE INDEX IF NOT EXISTS report_user_id_idx ON report(user_id);
CREATE INDEX IF NOT EXISTS report_status_idx ON report(status);