-- Runs once, the first time the database volume is created.
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector: embeddings and similarity search
CREATE EXTENSION IF NOT EXISTS unaccent;   -- accent-insensitive full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- typo-tolerant matching
