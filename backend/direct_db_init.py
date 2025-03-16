"""
Přímá inicializace databáze na Render.com

Tento skript inicializuje databázi přímo z hodnot zadaných v Render dashboardu.
"""
import psycopg2
import sys
import time

def init_db_direct():
    # Aktuální hodnoty pro připojení k Render PostgreSQL
    host = "dpg-cn8bjt7109ks7395a720-a.frankfurt-postgres.render.com"
    port = "5432"
    dbname = "memorymap"
    user = "memorymap_user"
    password = "DY7iZEJA0Oy1GDBRwIlysGb2CkW0zluJ"  # Aktualizované heslo
    
    print(f"Připojuji se k databázi: {host}:{port}/{dbname} jako {user}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=10
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Připojení úspěšné!")
        
        # Vytvoření PostGIS rozšíření
        print("Vytvářím PostGIS rozšíření...")
        try:
            cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
            print("PostGIS rozšíření úspěšně vytvořeno")
        except Exception as e:
            print(f"Chyba při vytváření PostGIS: {str(e)}")
        
        # Vytvoření tabulky memories
        print("Vytvářím tabulku memories...")
        try:
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
            print("Tabulka memories vytvořena")
        except Exception as e:
            print(f"Chyba při vytváření tabulky: {str(e)}")
        
        # Přidání testovacích dat
        print("Přidávám testovací data...")
        try:
            cur.execute('''
                INSERT INTO memories (text, location, keywords, coordinates)
                VALUES (
                    'Test z přímé inicializace', 
                    'Praha', 
                    ARRAY['test', 'Praha', 'inicializace'], 
                    ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326)
                )
                ON CONFLICT DO NOTHING;
            ''')
            print("Testovací data úspěšně přidána")
        except Exception as e:
            print(f"Chyba při přidávání dat: {str(e)}")
        
        # Kontrola dat
        print("Kontroluji počet záznamů...")
        try:
            cur.execute("SELECT COUNT(*) FROM memories")
            count = cur.fetchone()[0]
            print(f"Počet záznamů v tabulce: {count}")
        except Exception as e:
            print(f"Chyba při kontrole dat: {str(e)}")
        
        conn.close()
        print("Inicializace dokončena!")
        return True
    except Exception as e:
        print(f"Chyba při připojení k databázi: {str(e)}")
        return False

if __name__ == "__main__":
    success = init_db_direct()
    sys.exit(0 if success else 1) 