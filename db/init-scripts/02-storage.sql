-- Create storage schema for file storage
CREATE SCHEMA IF NOT EXISTS storage;

-- Create storage tables
CREATE TABLE IF NOT EXISTS storage.buckets (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  public BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS storage.objects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bucket_id TEXT NOT NULL REFERENCES storage.buckets(id),
  name TEXT NOT NULL,
  owner UUID,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  metadata JSONB,
  path TEXT,
  UNIQUE(bucket_id, name)
);

-- Create a helper function to extract folder name from path
CREATE OR REPLACE FUNCTION storage.foldername(name TEXT)
RETURNS TEXT[] AS $$
BEGIN
  RETURN string_to_array(name, '/');
END;
$$ LANGUAGE plpgsql;

-- Create storage bucket for documents
INSERT INTO storage.buckets (id, name, public) 
VALUES ('documents', 'documents', FALSE)
ON CONFLICT (id) DO NOTHING;

-- Create a directory to store uploaded files
DO $$ 
BEGIN
  EXECUTE format('CREATE DIRECTORY IF NOT EXISTS %L', '/var/lib/postgresql/data/storage');
  EXECUTE format('CREATE DIRECTORY IF NOT EXISTS %L', '/var/lib/postgresql/data/storage/documents');
EXCEPTION WHEN OTHERS THEN
  -- Directory commands may not work in all Postgres versions
  -- Just log the error and continue
  RAISE NOTICE 'Could not create directories: %', SQLERRM;
END $$;