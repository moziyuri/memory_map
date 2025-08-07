"""
Inicializace databáze pro Risk Analyst feature
"""
import psycopg2
import os
import sys

def init_risk_db():
    """Inicializuje databázi pro risk analyst feature"""
    
    print("🚀 Spouštím inicializaci risk analyst databáze...")
    
    # Zkusíme environment variable, pak fallback
    database_url = os.getenv('RISK_DATABASE_URL')
    
    if database_url:
        print(f"✅ Používám RISK_DATABASE_URL: {database_url[:20]}...")
        try:
            conn = psycopg2.connect(database_url, sslmode='require')
        except Exception as e:
            print(f"❌ Chyba při připojení přes DATABASE_URL: {str(e)}")
            return False
    else:
        print("⚠️ RISK_DATABASE_URL není nastavena, používám hardcoded hodnoty")
        # Fallback na hardcoded hodnoty
        host = "dpg-d2a54tp5pdvs73acu64g-a.frankfurt-postgres.render.com"
        port = "5432"
        dbname = "risk_analyst"
        user = "risk_analyst_user"
        password = "uN3Zogp6tvoTmnjNV4owD92Nnm6UlGkf"
        
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                sslmode='require'
            )
        except Exception as e:
            print(f"❌ Chyba při připojení: {str(e)}")
            return False
    
    print("✅ Připojení k databázi úspěšné!")
    
    try:
        cur = conn.cursor()
        
        # 1. Kontrola PostGIS
        print("📊 Kontroluji PostGIS...")
        try:
            cur.execute("SELECT PostGIS_Version()")
            version = cur.fetchone()[0]
            print(f"✅ PostGIS verze: {version}")
        except Exception as e:
            print(f"❌ PostGIS chyba: {str(e)}")
            return False
        
        # 2. Vytvoření tabulek
        print("🏗️ Vytvářím tabulky...")
        
        # Tabulka risk_events
        cur.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                location POINT,  -- Geografická pozice
                event_type VARCHAR(50), -- 'flood', 'protest', 'supply_chain', 'geopolitical'
                severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
                source VARCHAR(100), -- 'chmi_api', 'rss', 'manual', 'copernicus'
                url TEXT, -- Zdroj dat
                scraped_at TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        print("✅ Tabulka risk_events vytvořena/zkontrolována")
        
        # Tabulka vw_suppliers
        cur.execute("""
            CREATE TABLE IF NOT EXISTS vw_suppliers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                location POINT,  -- Geografická pozice
                category VARCHAR(100), -- 'electronics', 'tires', 'steering', 'brakes'
                risk_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        print("✅ Tabulka vw_suppliers vytvořena/zkontrolována")
        
        # 3. Vytvoření geografických indexů
        print("🗺️ Vytvářím geografické indexy...")
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_events_location ON risk_events USING GIST (location);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_location ON vw_suppliers USING GIST (location);")
            print("✅ Geografické indexy vytvořeny")
        except Exception as e:
            print(f"⚠️ Chyba při vytváření indexů: {str(e)}")
        
        # 4. Vytvoření funkce pro výpočet rizik
        print("🧮 Vytvářím funkci pro výpočet rizik...")
        cur.execute("""
            CREATE OR REPLACE FUNCTION calculate_risk_in_radius(
                lat DOUBLE PRECISION,
                lon DOUBLE PRECISION,
                radius_km INTEGER
            ) RETURNS TABLE (
                event_count INTEGER,
                high_risk_count INTEGER,
                risk_score NUMERIC
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    COUNT(*)::INTEGER as event_count,
                    COUNT(CASE WHEN severity IN ('high', 'critical') THEN 1 END)::INTEGER as high_risk_count,
                    CASE 
                        WHEN COUNT(*) > 0 THEN 
                            (COUNT(CASE WHEN severity IN ('high', 'critical') THEN 1 END)::NUMERIC / COUNT(*)::NUMERIC * 100)
                        ELSE 0 
                    END as risk_score
                FROM risk_events
                WHERE ST_DWithin(
                    location::geography,
                    ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
                    radius_km * 1000
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("✅ Funkce calculate_risk_in_radius vytvořena")
        
        # 5. Vložení demo dat
        print("📝 Vkládám demo data...")
        
        # Demo risk events
        demo_events = [
            ("Záplavy v jižních Čechách", "Silné deště způsobily záplavy v jižních Čechách", 49.0, 14.5, "flood", "high", "chmi_api"),
            ("Protesty v Praze", "Demonstrace proti vládním opatřením", 50.0755, 14.4378, "protest", "medium", "rss"),
            ("Dopravní nehoda na D1", "Havárie kamionu blokuje dálnici D1", 49.8, 14.5, "supply_chain", "high", "manual"),
            ("Politické napětí v regionu", "Eskalace politického napětí", 50.1, 14.4, "geopolitical", "medium", "rss"),
            ("Povodně na Vltavě", "Vzestup hladiny Vltavy ohrožuje okolní oblasti", 49.2, 14.4, "flood", "critical", "chmi_api"),
            ("Stávka dopravců", "Stávka dopravních společností", 50.0, 14.3, "supply_chain", "high", "rss"),
            ("Extrémní počasí", "Silné bouřky a krupobití", 49.5, 14.6, "flood", "medium", "chmi_api"),
            ("Problémy s dodávkami", "Opoždění dodávek komponentů", 50.2, 14.5, "supply_chain", "medium", "manual"),
            ("Sociální nepokoje", "Demonstrace a nepokoje", 49.9, 14.4, "protest", "high", "rss")
        ]
        
        for event in demo_events:
            cur.execute("""
                INSERT INTO risk_events (title, description, location, event_type, severity, source)
                VALUES (%s, %s, point(%s, %s), %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, event)
        
        print(f"✅ Vloženo {len(demo_events)} demo risk events")
        
        # Demo dodavatelé
        demo_suppliers = [
            ("Bosch Electronics", 49.8, 14.4, "electronics", "medium"),
            ("Continental Tires", 50.1, 14.5, "tires", "low"),
            ("ZF Steering Systems", 49.9, 14.3, "steering", "high"),
            ("Brembo Brakes", 50.2, 14.6, "brakes", "medium"),
            ("Valeo Lighting", 49.7, 14.5, "electronics", "low"),
            ("Michelin Tires", 50.0, 14.4, "tires", "medium"),
            ("TRW Safety Systems", 49.6, 14.3, "safety", "high"),
            ("Delphi Electronics", 50.3, 14.5, "electronics", "medium"),
            ("Goodyear Tires", 49.5, 14.6, "tires", "low")
        ]
        
        for supplier in demo_suppliers:
            cur.execute("""
                INSERT INTO vw_suppliers (name, location, category, risk_level)
                VALUES (%s, point(%s, %s), %s, %s)
                ON CONFLICT DO NOTHING
            """, supplier)
        
        print(f"✅ Vloženo {len(demo_suppliers)} demo dodavatelů")
        
        conn.commit()
        print("✅ Všechny změny commitnuty!")
        
        # 6. Kontrola výsledku
        cur.execute("SELECT COUNT(*) FROM risk_events")
        events_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM vw_suppliers")
        suppliers_count = cur.fetchone()[0]
        
        print(f"📊 Finální stav:")
        print(f"   - Risk events: {events_count}")
        print(f"   - Suppliers: {suppliers_count}")
        
        conn.close()
        print("🎉 Inicializace risk analyst databáze dokončena úspěšně!")
        return True
        
    except Exception as e:
        print(f"❌ Chyba při inicializaci: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("RISK ANALYST DATABASE INITIALIZATION")
    print("=" * 50)
    
    success = init_risk_db()
    
    if success:
        print("✅ Inicializace úspěšná!")
        sys.exit(0)
    else:
        print("❌ Inicializace selhala!")
        sys.exit(1) 