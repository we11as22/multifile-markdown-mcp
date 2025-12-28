-- PostgreSQL + pgvector initialization script for Agent Memory MCP
-- This script runs on container first startup

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Database is already created by Docker environment variables
-- Tables will be created by Alembic migrations at runtime

-- Create RRF score function (Reciprocal Rank Fusion)
CREATE OR REPLACE FUNCTION rrf_score(rank BIGINT, k INTEGER DEFAULT 60)
RETURNS NUMERIC
LANGUAGE SQL IMMUTABLE PARALLEL SAFE
AS $$
    SELECT COALESCE(1.0 / ($1 + $2), 0.0);
$$;

-- Create tables
CREATE TABLE IF NOT EXISTS memory_files (
    id SERIAL PRIMARY KEY,
    file_path VARCHAR(512) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'other',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_hash VARCHAR(64) NOT NULL,
    word_count INTEGER DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT valid_category CHECK (category IN ('main', 'project', 'concept', 'conversation', 'preference', 'other'))
);

CREATE INDEX IF NOT EXISTS idx_memory_files_category ON memory_files(category);
CREATE INDEX IF NOT EXISTS idx_memory_files_updated ON memory_files(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_files_tags ON memory_files USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_memory_files_metadata ON memory_files USING gin(metadata);

CREATE TABLE IF NOT EXISTS memory_chunks (
    id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES memory_files(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(1536),
    header_path TEXT[] DEFAULT '{}',
    section_level INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_file_chunk UNIQUE(file_id, chunk_index)
);

-- Add generated column for fulltext search
ALTER TABLE memory_chunks ADD COLUMN IF NOT EXISTS content_tsvector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON memory_chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file_chunk ON memory_chunks(file_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunks_fulltext ON memory_chunks USING gin(content_tsvector);
CREATE INDEX IF NOT EXISTS idx_chunks_header ON memory_chunks USING gin(header_path);

-- Create vector index (IVFFlat for better performance with large datasets)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat ON memory_chunks
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS sync_status (
    id SERIAL PRIMARY KEY,
    file_id INTEGER UNIQUE NOT NULL REFERENCES memory_files(id) ON DELETE CASCADE,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    last_synced_hash VARCHAR(64),
    sync_status VARCHAR(20) DEFAULT 'pending',
    error_message TEXT,
    CONSTRAINT valid_sync_status CHECK (sync_status IN ('pending', 'syncing', 'completed', 'failed'))
);
