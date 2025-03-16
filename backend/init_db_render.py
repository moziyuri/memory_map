"""
Inicializační skript pro databázi na Render.com

Tento skript vytvoří potřebná rozšíření PostgreSQL a tabulky
pro aplikaci MemoryMap. Měl by být spuštěn jednou při nasazení.
"""

import os
import psycopg2
import time
import sys
from urllib.parse import urlparse

def inspect_database_url():
    """Analyzuje proměnnou DATABASE_URL a vypíše diagnostické informace"""
    DATABASE_URL = os.getenv('DATABASE_URL', '')
    print(f"DATABASE_URL exists: {bool(DATABASE_URL)}")
    
    if not DATABASE_URL:
        return
    
    print(f"DATABASE_URL starts with: {DATABASE_URL[:10]}...")
    
    # Analýza URL
    try:
        if DATABASE_URL.startswith('postgres://'):
            parsed = urlparse(DATABASE_URL)
            print(f"Schema: {parsed.scheme}")
            print(f"Netloc: {parsed.netloc}")
            print(f"Path: {parsed.path}")
            
            # Není potřeba vypisovat heslo, stačí zjistit, zda je přítomné
            username = parsed.username or ''
            password_present = bool(parsed.password)
            host = parsed.hostname or ''
            port = parsed.port or ''
            
            print(f"Username present: {bool(username)}")
            print(f"Password present: {password_present}")
            print(f"Host present: {bool(host)}")
            print(f"Port present: {bool(port)}")
    except Exception as e:
        print(f"Error parsing DATABASE_URL: {str(e)}")

def init_db():
    print("Starting database initialization...")
    
    # Výpis diagnostických informací
    print("Environment variables:")
    for key in os.environ.keys():
        if key.startswith('DATABASE') or key.startswith('POSTGRES'):
            # Bezpečný výpis - neukazovat celé hodnoty
            print(f"  {key} exists: {bool(os.getenv(key))}")
    
    # Kontrola a diagnostika DATABASE_URL
    inspect_database_url()
    
    # Získání DATABASE_URL z prostředí
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL není nastavena")
        return False
    
    # Úprava URL pro psycopg2
    if DATABASE_URL.startswith('postgres://'):
        print("Converting postgres:// to postgresql://")
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    print(f"Připojuji se k databázi...")
    
    # Několik pokusů o připojení
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Pokus o připojení {attempt + 1}/{max_retries}")
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
            conn.autocommit = True
            cur = conn.cursor()
            
            # 1. Vytvoření PostGIS rozšíření
            print("Vytvářím PostGIS rozšíření...")
            cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
            
            # 2. Vytvoření tabulky memories
            print("Vytvářím tabulku memories...")
            cur.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    location TEXT NOT NULL,
                    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
                    keywords TEXT[],
                    source TEXT,
                    date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            # 3. Vytvoření indexů
            print("Vytvářím indexy...")
            cur.execute('CREATE INDEX IF NOT EXISTS idx_memories_coordinates ON memories USING GIST (coordinates);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_memories_keywords ON memories USING GIN (keywords);')
            
            # 4. Kontrola existence tabulky
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')")
            if cur.fetchone()[0]:
                print("✅ Tabulka memories byla úspěšně vytvořena.")
            else:
                print("❌ Tabulka memories NEBYLA vytvořena!")
                
            # 5. Přidání testovacích dat
            print("Přidávám testovací data...")
            cur.execute('''
                INSERT INTO memories (text, location, keywords, coordinates)
                VALUES (
                    'Testovací vzpomínka na Prahu', 
                    'Praha', 
                    ARRAY['Praha', 'vzpomínka', 'testovací'], 
                    ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326)
                )
                ON CONFLICT DO NOTHING;
            ''')
            
            # 6. Ověření dat
            cur.execute("SELECT COUNT(*) FROM memories")
            count = cur.fetchone()[0]
            print(f"Počet záznamů v tabulce: {count}")
            
            print("✅ Inicializace databáze dokončena úspěšně!")
            conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Chyba při inicializaci (pokus {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                print("Čekám 5 sekund před dalším pokusem...")
                time.sleep(5)
            else:
                print("Inicializace selhala po všech pokusech.")
                return False
                
    return False

if __name__ == "__main__":
    success = init_db()
    # Explicitní návratový kód pro build proces
    sys.exit(0 if success else 1) 