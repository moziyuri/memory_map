-- Instalace potřebných rozšíření
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS hstore;

-- Vytvoření tabulky pro OSM data
CREATE TABLE IF NOT EXISTS osm_data (
    id BIGINT PRIMARY KEY,
    name TEXT,
    tags HSTORE,
    way GEOMETRY(GEOMETRY, 4326),
    osm_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vytvoření indexů pro rychlejší vyhledávání
CREATE INDEX IF NOT EXISTS osm_data_name_idx ON osm_data (name);
CREATE INDEX IF NOT EXISTS osm_data_tags_idx ON osm_data USING GIN (tags);
CREATE INDEX IF NOT EXISTS osm_data_way_idx ON osm_data USING GIST (way);

-- Příklady dat (obvykle by se importovala z OSM)
INSERT INTO osm_data (id, name, tags, way, osm_type)
VALUES
    (1, 'Praha', 'name:de=>Prag, name:en=>Prague, place=>city, population=>1309000, capital=>yes', ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326), 'node'),
    (2, 'Brno', 'name:de=>Brünn, name:en=>Brno, place=>city, population=>377028', ST_SetSRID(ST_MakePoint(16.6068, 49.1951), 4326), 'node'),
    (3, 'Plzeň', 'name:de=>Pilsen, name:en=>Pilsen, place=>city, population=>169858', ST_SetSRID(ST_MakePoint(13.3826, 49.7384), 4326), 'node'),
    (4, 'Ostrava', 'name:de=>Ostrau, name:en=>Ostrava, place=>city, population=>289128', ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326), 'node'),
    (5, 'Lidice', 'name:en=>Lidice, place=>village, historic=>yes, memorial=>martyrs', ST_SetSRID(ST_MakePoint(14.1875, 50.1428), 4326), 'node'),
    (6, 'Ležáky', 'name:en=>Lezaky, place=>hamlet, historic=>yes, memorial=>martyrs', ST_SetSRID(ST_MakePoint(15.9923, 49.8303), 4326), 'node'),
    (7, 'Karlštejn', 'name:de=>Karlstein, name:en=>Karlstejn, historic=>castle, tourism=>attraction', ST_SetSRID(ST_MakePoint(14.1883, 49.9394), 4326), 'node'),
    (8, 'Terezín', 'name:de=>Theresienstadt, name:en=>Terezin, historic=>fortress, memorial=>yes', ST_SetSRID(ST_MakePoint(14.1478, 50.5139), 4326), 'node'),
    (9, 'Kutná Hora', 'name:de=>Kuttenberg, name:en=>Kutna Hora, historic=>city, unesco=>yes', ST_SetSRID(ST_MakePoint(15.2684, 49.9479), 4326), 'node'),
    (10, 'Český Krumlov', 'name:de=>Krumau, name:en=>Cesky Krumlov, historic=>city, unesco=>yes', ST_SetSRID(ST_MakePoint(14.3157, 48.8127), 4326), 'node')
ON CONFLICT DO NOTHING; 