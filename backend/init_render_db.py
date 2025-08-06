import os
import psycopg2
from dotenv import load_dotenv
import time

def init_render_db():
    # Načtení proměnných prostředí
    load_dotenv()
    
    # Získání DATABASE_URL z prostředí
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("DATABASE_URL není nastavena")
    
    # Úprava URL pro psycopg2
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Několik pokusů o připojení (databáze může potřebovat čas na start)
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Pokus o připojení k databázi {attempt + 1}/{max_retries}")
            # SSL parametry pro Render.com PostgreSQL
            ssl_params = {
                'sslmode': 'require',
                'sslcert': None,
                'sslkey': None,
                'sslrootcert': None
            }
            # Připojení k databázi
            conn = psycopg2.connect(DATABASE_URL, **ssl_params)
            conn.autocommit = True
            cur = conn.cursor()
            
            print("Vytvářím PostGIS rozšíření...")
            # Vytvoření PostGIS rozšíření
            cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
            print("PostGIS rozšíření vytvořeno")
            
            cur.execute('CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;')
            print("Fuzzystrmatch rozšíření vytvořeno")
            
            print("Vytvářím tabulku memories...")
            # Vytvoření tabulky memories
            cur.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    location VARCHAR(255) NOT NULL,
                    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
                    keywords TEXT[],
                    source TEXT,
                    date TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    year_of_event INTEGER,
                    year_of_record INTEGER,
                    person_name TEXT,
                    birth_year INTEGER
                );
            ''')
            print("Tabulka memories vytvořena")
            
            print("Vytvářím indexy...")
            # Vytvoření indexů
            cur.execute('CREATE INDEX IF NOT EXISTS idx_memories_coordinates ON memories USING GIST (coordinates);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_memories_keywords ON memories USING GIN (keywords);')
            print("Indexy vytvořeny")
            
            # Kontrola, že tabulka existuje
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')")
            table_exists = cur.fetchone()[0]
            
            if table_exists:
                print("Databáze byla úspěšně inicializována")
                break
            else:
                raise Exception("Tabulka memories nebyla vytvořena")
                
        except Exception as e:
            print(f"Chyba při inicializaci databáze (pokus {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                print("Čekám 5 sekund před dalším pokusem...")
                time.sleep(5)
            else:
                raise
        finally:
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    init_render_db() 