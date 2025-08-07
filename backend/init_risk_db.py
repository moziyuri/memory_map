"""
Inicializace databáze pro Risk Analyst feature

Tento skript vytvoří nové tabulky pro risk events a související funkce
pro analýzu rizik dodavatelských řetězců VW Group.
"""
import psycopg2
import sys
import time
import os
from dotenv import load_dotenv

load_dotenv()

def init_risk_db():
    """Inicializuje databázi pro risk analyst feature"""
    
    # NOVÁ DATABÁZE PRO RISK ANALYST FEATURE
    # TODO: Nahradit skutečnými hodnotami z Render.com
    host = "dpg-xxxxx-a.frankfurt-postgres.render.com"  # TODO: Skutečný host
    port = "5432"
    dbname = "memorymap_risk_analyst"  # TODO: Skutečný název databáze
    user = "memorymap_risk_analyst_user"  # TODO: Skutečný uživatel
    password = "xxxxx"  # TODO: Skutečné heslo
    
    print(f"Připojuji se k databázi: {host}:{port}/{dbname} jako {user}")
    print("⚠️  POZOR: Používám placeholder hodnoty. Nahraď skutečnými hodnotami z Render.com!")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            connect_timeout=10,
            sslmode='require'
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Připojení úspěšné!")
        
        # 1. Vytvoření PostGIS rozšíření (pokud neexistuje)
        print("Kontroluji PostGIS rozšíření...")
        try:
            cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
            print("PostGIS rozšíření je dostupné")
        except Exception as e:
            print(f"Chyba při kontrole PostGIS: {str(e)}")
        
        # 2. Vytvoření hlavní tabulky risk_events
        print("Vytvářím tabulku risk_events...")
        try:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS risk_events (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    location GEOGRAPHY(POINT, 4326),  -- Geografická pozice
                    event_type VARCHAR(50), -- 'flood', 'protest', 'supply_chain', 'geopolitical'
                    severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
                    source VARCHAR(100), -- 'chmi_api', 'rss', 'manual', 'copernicus'
                    url TEXT, -- Zdroj dat
                    scraped_at TIMESTAMP DEFAULT NOW(),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            ''')
            print("Tabulka risk_events vytvořena")
        except Exception as e:
            print(f"Chyba při vytváření tabulky risk_events: {str(e)}")
        
        # 3. Vytvoření geografických indexů
        print("Vytvářím geografické indexy...")
        try:
            cur.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_location ON risk_events USING GIST (location);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_type ON risk_events (event_type);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_severity ON risk_events (severity);')
            cur.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_created_at ON risk_events (created_at);')
            print("Geografické indexy vytvořeny")
        except Exception as e:
            print(f"Chyba při vytváření indexů: {str(e)}")
        
        # 4. Vytvoření tabulky pro dodavatele VW Group
        print("Vytvářím tabulku vw_suppliers...")
        try:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vw_suppliers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    location GEOGRAPHY(POINT, 4326) NOT NULL,
                    category VARCHAR(100), -- 'electronics', 'tires', 'steering', etc.
                    risk_level VARCHAR(20) DEFAULT 'medium', -- 'low', 'medium', 'high'
                    created_at TIMESTAMP DEFAULT NOW()
                );
            ''')
            print("Tabulka vw_suppliers vytvořena")
        except Exception as e:
            print(f"Chyba při vytváření tabulky vw_suppliers: {str(e)}")
        
        # 5. Vytvoření funkce pro analýzu rizik
        print("Vytvářím funkci pro analýzu rizik...")
        try:
            cur.execute('''
                CREATE OR REPLACE FUNCTION calculate_risk_in_radius(
                    point_lat DECIMAL, 
                    point_lon DECIMAL, 
                    radius_km INTEGER DEFAULT 50
                )
                RETURNS TABLE(
                    event_count INTEGER,
                    high_risk_count INTEGER,
                    risk_score DECIMAL
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(*)::INTEGER as event_count,
                        COUNT(*) FILTER (WHERE severity IN ('high', 'critical'))::INTEGER as high_risk_count,
                        CASE 
                            WHEN COUNT(*) = 0 THEN 0.0
                            ELSE (COUNT(*) FILTER (WHERE severity IN ('high', 'critical'))::DECIMAL / COUNT(*)) * 100
                        END as risk_score
                    FROM risk_events
                    WHERE ST_DWithin(
                        location::geography, 
                        ST_SetSRID(ST_MakePoint(point_lon, point_lat), 4326)::geography, 
                        radius_km * 1000
                    );
                END;
                $$ LANGUAGE plpgsql;
            ''')
            print("Funkce calculate_risk_in_radius vytvořena")
        except Exception as e:
            print(f"Chyba při vytváření funkce: {str(e)}")
        
        # 6. Přidání demo dat pro VW Group dodavatele
        print("Přidávám demo data pro VW Group dodavatele...")
        try:
            cur.execute('''
                INSERT INTO vw_suppliers (name, location, category, risk_level) VALUES
                ('Bosch Electronics', ST_SetSRID(ST_MakePoint(15.4730, 49.8175), 4326), 'electronics', 'medium'),
                ('Continental Tires', ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326), 'tires', 'low'),
                ('ZF Steering Systems', ST_SetSRID(ST_MakePoint(16.6068, 49.1951), 4326), 'steering', 'high')
                ON CONFLICT DO NOTHING;
            ''')
            print("Demo data pro dodavatele přidána")
        except Exception as e:
            print(f"Chyba při přidávání demo dat: {str(e)}")
        
        # 7. Přidání demo risk events
        print("Přidávám demo risk events...")
        try:
            cur.execute('''
                INSERT INTO risk_events (title, description, location, event_type, severity, source) VALUES
                ('Záplavy v jižních Čechách', 'Záplavy ovlivňují dodávky z Bosch Electronics', 
                 ST_SetSRID(ST_MakePoint(15.4730, 49.8175), 4326), 'flood', 'high', 'chmi_api'),
                ('Protesty v Praze', 'Dopravní omezení v centru Prahy', 
                 ST_SetSRID(ST_MakePoint(14.4378, 50.0755), 4326), 'protest', 'medium', 'rss'),
                ('Dopravní nehoda na D1', 'Uzavírka dálnice D1 u Brna', 
                 ST_SetSRID(ST_MakePoint(16.6068, 49.1951), 4326), 'supply_chain', 'high', 'manual')
                ON CONFLICT DO NOTHING;
            ''')
            print("Demo risk events přidány")
        except Exception as e:
            print(f"Chyba při přidávání risk events: {str(e)}")
        
        # 8. Kontrola dat
        print("Kontroluji počet záznamů...")
        try:
            cur.execute("SELECT COUNT(*) FROM risk_events")
            risk_count = cur.fetchone()[0]
            print(f"Počet risk events: {risk_count}")
            
            cur.execute("SELECT COUNT(*) FROM vw_suppliers")
            supplier_count = cur.fetchone()[0]
            print(f"Počet dodavatelů: {supplier_count}")
        except Exception as e:
            print(f"Chyba při kontrole dat: {str(e)}")
        
        conn.close()
        print("✅ Inicializace risk analyst databáze dokončena!")
        return True
        
    except Exception as e:
        print(f"❌ Chyba při připojení k databázi: {str(e)}")
        print("💡 Zkontroluj, že jsi vytvořil novou PostgreSQL databázi na Render.com")
        return False

if __name__ == "__main__":
    success = init_risk_db()
    sys.exit(0 if success else 1) 