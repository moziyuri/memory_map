-- Aktualizace tabulky memories, aby obsahovala nové sloupce
ALTER TABLE memories 
ADD COLUMN IF NOT EXISTS year_of_event INTEGER,
ADD COLUMN IF NOT EXISTS year_of_record INTEGER,
ADD COLUMN IF NOT EXISTS person_name TEXT,
ADD COLUMN IF NOT EXISTS birth_year INTEGER;

-- Vložení 100 záznamů vzpomínek (upraveno pro GEOGRAPHY typ)
INSERT INTO memories (text, location, source, year_of_event, year_of_record, person_name, birth_year, keywords) VALUES
-- Sudety a poválečné vysídlení
('Pamatuji si den, kdy jsme museli opustit náš dům v Jablonci. Bylo mi tehdy 12 let. Otec nás večer probudil a měli jsme jen dvě hodiny na sbalení. Mohli jsme si vzít jen to, co uneseme v rukou. Většina našeho majetku tam zůstala. Přestěhovali nás do sběrného tábora v Liberci a později do Německa.', ST_SetSRID(ST_MakePoint(15.171, 50.724), 4326), 'Rozhovor s pamětníkem', 1946, 2005, 'Hans Müller', 1934, '{"vysídlení","Sudety","Němci","Jablonec","odsun"}'),

('Když jsme se do Karlových Varů nastěhovali v létě 1946, město bylo jako vylidněné. Naše rodina dostala byt po německé rodině Schneiderových. V bytě zůstal nábytek, oblečení, dokonce i fotografie. Bylo mi to tehdy líto, ale rodiče říkali, že ti lidé se dopustili hrozných věcí za války.', ST_SetSRID(ST_MakePoint(12.880, 50.231), 4326), 'Paměť národa', 1946, 2010, 'Marie Horáková', 1939, '{"dosídlení","Sudety","Karlovy Vary","konfiskace","osídlování"}')
-- Přidejte další záznamy podobným způsobem...