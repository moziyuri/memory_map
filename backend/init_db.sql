-- Drop database if exists
DROP DATABASE IF EXISTS memorymap;

-- Create database
CREATE DATABASE memorymap;

-- Connect to the database
\c memorymap

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS hstore;

-- Create memories table
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    keywords TEXT[],
    source TEXT,
    date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    year_of_event INTEGER,
    year_of_record INTEGER,
    person_name TEXT,
    birth_year INTEGER
);

-- Create place_names table for historical place names
CREATE TABLE IF NOT EXISTS place_names (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    alt_name TEXT,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    historical_period TEXT,
    description TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for place_names
CREATE INDEX IF NOT EXISTS place_names_name_idx ON place_names (name);
CREATE INDEX IF NOT EXISTS place_names_alt_name_idx ON place_names (alt_name);
CREATE INDEX IF NOT EXISTS place_names_historical_period_idx ON place_names (historical_period);
CREATE INDEX IF NOT EXISTS place_names_location_idx ON place_names USING GIST (location);

-- Create osm_data table for additional geographical data
CREATE TABLE IF NOT EXISTS osm_data (
    id BIGINT PRIMARY KEY,
    name TEXT,
    tags HSTORE,
    way GEOMETRY(GEOMETRY, 4326),
    osm_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for osm_data
CREATE INDEX IF NOT EXISTS osm_data_name_idx ON osm_data (name);
CREATE INDEX IF NOT EXISTS osm_data_tags_idx ON osm_data USING GIN (tags);
CREATE INDEX IF NOT EXISTS osm_data_way_idx ON osm_data USING GIST (way);

-- Insert some sample data into place_names
INSERT INTO place_names (name, alt_name, location, historical_period, description, source)
VALUES
    ('Praha', 'Praga', ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326), '1850-2023', 'Hlavní město České republiky', 'Oficiální záznam'),
    ('Brno', 'Brünn', ST_SetSRID(ST_MakePoint(16.6068, 49.1951), 4326), '1850-2023', 'Druhé největší město České republiky', 'Oficiální záznam'),
    ('Lidice', NULL, ST_SetSRID(ST_MakePoint(14.1875, 50.1428), 4326), '1850-1942', 'Obec zničená nacisty 10. června 1942', 'Historické záznamy'),
    ('Ležáky', NULL, ST_SetSRID(ST_MakePoint(15.9923, 49.8303), 4326), '1850-1942', 'Osada zničená nacisty 24. června 1942', 'Historické záznamy'),
    ('Sudety', 'Sudetenland', ST_SetSRID(ST_MakePoint(14.9889, 50.6591), 4326), '1938-1945', 'Pohraniční území ČSR obsazené nacistickým Německem', 'Historické prameny')
ON CONFLICT DO NOTHING;

-- Insert some sample data into osm_data
INSERT INTO osm_data (id, name, tags, way, osm_type)
VALUES
    (1, 'Praha', 'name:de=>Prag, name:en=>Prague, place=>city', ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326), 'node'),
    (2, 'Brno', 'name:de=>Brünn, name:en=>Brno, place=>city', ST_SetSRID(ST_MakePoint(16.6068, 49.1951), 4326), 'node'),
    (5, 'Lidice', 'name:en=>Lidice, place=>village, historic=>yes', ST_SetSRID(ST_MakePoint(14.1875, 50.1428), 4326), 'node')
ON CONFLICT DO NOTHING;

-- Insert some sample data into memories
INSERT INTO memories (text, location, source, year_of_event, year_of_record, person_name, birth_year, keywords) VALUES
    ('Pamatuji si den, kdy jsme museli opustit náš dům v Jablonci. Bylo mi tehdy 12 let. Otec nás večer probudil a měli jsme jen dvě hodiny na sbalení. Mohli jsme si vzít jen to, co uneseme v rukou. Většina našeho majetku tam zůstala. Přestěhovali nás do sběrného tábora v Liberci a později do Německa.', ST_SetSRID(ST_MakePoint(15.171, 50.724), 4326), 'Rozhovor s pamětníkem', 1946, 2005, 'Hans Müller', 1934, '{"vysídlení","Sudety","Němci","Jablonec","odsun"}'),
    ('Když jsme se do Karlových Varů nastěhovali v létě 1946, město bylo jako vylidněné. Naše rodina dostala byt po německé rodině Schneiderových. V bytě zůstal nábytek, oblečení, dokonce i fotografie. Bylo mi to tehdy líto, ale rodiče říkali, že ti lidé se dopustili hrozných věcí za války.', ST_SetSRID(ST_MakePoint(12.880, 50.231), 4326), 'Paměť národa', 1946, 2010, 'Marie Horáková', 1939, '{"dosídlení","Sudety","Karlovy Vary","konfiskace","osídlování"}')
ON CONFLICT DO NOTHING;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE memorymap TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- V PostgreSQL konzoli spusťte nejprve aktualizaci tabulky
ALTER TABLE memories 
ADD COLUMN IF NOT EXISTS year_of_event INTEGER,
ADD COLUMN IF NOT EXISTS year_of_record INTEGER,
ADD COLUMN IF NOT EXISTS person_name TEXT,
ADD COLUMN IF NOT EXISTS birth_year INTEGER;

-- Poté vložte data
INSERT INTO memories (text, location, source, year_of_event, year_of_record, person_name, birth_year, keywords) VALUES
('Pamatuji si den, kdy jsme museli opustit náš dům v Jablonci...', ST_SetSRID(ST_MakePoint(15.171, 50.724), 4326), 'Rozhovor s pamětníkem', 1946, 2005, 'Hans Müller', 1934, '{"vysídlení","Sudety","Němci","Jablonec","odsun"}');
-- Pokračujte dalšími záznamy... 