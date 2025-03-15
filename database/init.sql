-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL,
    keywords TEXT[] NOT NULL,
    source TEXT,
    date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create spatial index
CREATE INDEX IF NOT EXISTS idx_memories_location ON memories USING GIST (location);

-- Create text search index
CREATE INDEX IF NOT EXISTS idx_memories_text ON memories USING GIN (to_tsvector('czech', text)); 