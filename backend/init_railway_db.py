"""
import os
import psycopg2
from dotenv import load_dotenv

def init_railway_db():
    # Načtení proměnných prostředí
    load_dotenv()
    
    # Získání DATABASE_URL z prostředí
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise Exception("DATABASE_URL není nastavena")
    
    # Úprava URL pro psycopg2
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Připojení k databázi
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Vytvoření PostGIS rozšíření
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
        cur.execute('CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;')
        
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Vytvoření indexů
        cur.execute('CREATE INDEX IF NOT EXISTS idx_memories_coordinates ON memories USING GIST (coordinates);')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_memories_keywords ON memories USING GIN (keywords);')
        
        print("Databáze byla úspěšně inicializována")
        
    except Exception as e:
        print(f"Chyba při inicializaci databáze: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_railway_db()
""" 