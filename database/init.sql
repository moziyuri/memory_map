-- Povolení PostGIS rozšíření
CREATE EXTENSION IF NOT EXISTS postgis;

-- Vytvoření tabulky pro vzpomínky
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    coordinates GEOMETRY(Point, 4326) NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    source VARCHAR(255),
    date VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Vytvoření prostorového indexu pro rychlejší vyhledávání
CREATE INDEX IF NOT EXISTS memories_coordinates_idx ON memories USING GIST (coordinates);

-- Vytvoření textového indexu pro fulltextové vyhledávání
CREATE INDEX IF NOT EXISTS memories_text_idx ON memories USING GIN (to_tsvector('simple', text)); 