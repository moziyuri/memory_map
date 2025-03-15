-- Instalace potřebných rozšíření
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

-- Vytvoření tabulky pro historické názvy míst
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

-- Vytvoření indexu pro rychlejší vyhledávání
CREATE INDEX IF NOT EXISTS place_names_name_idx ON place_names (name);
CREATE INDEX IF NOT EXISTS place_names_alt_name_idx ON place_names (alt_name);
CREATE INDEX IF NOT EXISTS place_names_historical_period_idx ON place_names (historical_period);

-- Vytvoření prostorového indexu pro geografii
CREATE INDEX IF NOT EXISTS place_names_location_idx ON place_names USING GIST (location);

-- Vložení několika základních historických míst pro testování
INSERT INTO place_names (name, alt_name, location, historical_period, description, source)
VALUES
    ('Praha', 'Praga', ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326), '1850-2023', 'Hlavní město České republiky', 'Oficiální záznam'),
    ('Brno', 'Brünn', ST_SetSRID(ST_MakePoint(16.6068, 49.1951), 4326), '1850-2023', 'Druhé největší město České republiky', 'Oficiální záznam'),
    ('Plzeň', 'Pilsen', ST_SetSRID(ST_MakePoint(13.3826, 49.7384), 4326), '1850-2023', 'Západočeské město proslulé pivovarem', 'Oficiální záznam'),
    ('Ostrava', 'Ostrau', ST_SetSRID(ST_MakePoint(18.2625, 49.8209), 4326), '1850-2023', 'Severomoravské průmyslové centrum', 'Oficiální záznam'),
    ('Olomouc', 'Olmütz', ST_SetSRID(ST_MakePoint(17.2513, 49.5938), 4326), '1850-2023', 'Historické město na Moravě', 'Oficiální záznam'),
    ('Liberec', 'Reichenberg', ST_SetSRID(ST_MakePoint(15.0543, 50.7663), 4326), '1850-2023', 'Severočeské město pod Ještědem', 'Oficiální záznam'),
    ('Karlovy Vary', 'Karlsbad', ST_SetSRID(ST_MakePoint(12.8730, 50.2304), 4326), '1850-2023', 'Lázeňské město v západních Čechách', 'Oficiální záznam'),
    ('Hradec Králové', 'Königgrätz', ST_SetSRID(ST_MakePoint(15.8328, 50.2092), 4326), '1850-2023', 'Východočeské město', 'Oficiální záznam'),
    ('Lidice', NULL, ST_SetSRID(ST_MakePoint(14.1875, 50.1428), 4326), '1850-1942', 'Obec zničená nacisty 10. června 1942', 'Historické záznamy'),
    ('Ležáky', NULL, ST_SetSRID(ST_MakePoint(15.9923, 49.8303), 4326), '1850-1942', 'Osada zničená nacisty 24. června 1942', 'Historické záznamy'),
    ('Mladotice', NULL, ST_SetSRID(ST_MakePoint(13.4077, 50.0295), 4326), '1850-2023', 'Obec v okresu Plzeň-sever', 'Místní kronika'),
    ('Sudety', 'Sudetenland', ST_SetSRID(ST_MakePoint(14.9889, 50.6591), 4326), '1938-1945', 'Pohraniční území ČSR obsazené nacistickým Německem', 'Historické prameny'),
    ('Mariánské Lázně', 'Marienbad', ST_SetSRID(ST_MakePoint(12.7010, 49.9646), 4326), '1850-2023', 'Lázeňské město', 'Oficiální záznam'),
    ('Podkarpatská Rus', 'Subcarpathian Ruthenia', ST_SetSRID(ST_MakePoint(22.2879, 48.5472), 4326), '1919-1939', 'Historické území Československa', 'Historické mapy'),
    ('Rakousko-Uhersko', 'Österreich-Ungarn', ST_SetSRID(ST_MakePoint(16.3738, 48.2083), 4326), '1867-1918', 'Historický státní útvar', 'Historický atlas'),
    ('Protektorát Čechy a Morava', 'Protektorat Böhmen und Mähren', ST_SetSRID(ST_MakePoint(14.4212, 50.0874), 4326), '1939-1945', 'Okupační zřízení během 2. světové války', 'Historické prameny'),
    ('Československo', 'Czechoslovakia', ST_SetSRID(ST_MakePoint(14.4212, 50.0874), 4326), '1918-1992', 'Bývalý společný stát Čechů a Slováků', 'Historický atlas'),
    ('Krkonoše', 'Riesengebirge', ST_SetSRID(ST_MakePoint(15.7399, 50.7360), 4326), '1850-2023', 'Nejvyšší pohoří v České republice', 'Geografický atlas'),
    ('Český Krumlov', 'Krumau', ST_SetSRID(ST_MakePoint(14.3157, 48.8127), 4326), '1850-2023', 'Historické město v jižních Čechách', 'Turistické průvodce'),
    ('Kutná Hora', 'Kuttenberg', ST_SetSRID(ST_MakePoint(15.2684, 49.9479), 4326), '1850-2023', 'Historické hornické město', 'Historické prameny')
ON CONFLICT DO NOTHING; 