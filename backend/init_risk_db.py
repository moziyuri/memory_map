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
                location GEOGRAPHY(POINT, 4326),  -- Geografická pozice
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
                location GEOGRAPHY(POINT, 4326),  -- Geografická pozice
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
        
        # 5. Databáze je připravena pro reálná data
        print("📝 Databáze je připravena pro reálná data z web scrapingu...")
        
        # 6. Přidání ukázkových dodavatelů pro testování pokročilých funkcí
        print("🏭 Přidávám ukázkové dodavatele pro testování...")
        
        sample_suppliers = [
            # Kritičtí dodavatelé v rizikových oblastech
            ("Bosch Electronics", 50.0755, 14.4378, "electronics", "critical"),  # Praha - blízko Vltavy
            ("Continental Tires", 49.1951, 16.6068, "tires", "critical"),  # Brno - blízko Moravy
            ("ZF Steering", 50.2092, 15.8327, "steering", "high"),  # Hradec Králové - blízko Labe
            ("Brembo Brakes", 49.7475, 13.3776, "brakes", "high"),  # Plzeň - blízko Berounky
            ("Magna Body Parts", 50.231, 12.880, "body_parts", "medium"),  # Karlovy Vary - blízko Ohře
            
            # Dodavatelé v bezpečnějších oblastech
            ("Siemens Electronics", 50.7663, 15.0543, "electronics", "medium"),  # Liberec
            ("Michelin Tires", 49.5938, 17.2507, "tires", "medium"),  # Olomouc
            ("TRW Steering", 48.9745, 14.4747, "steering", "low"),  # České Budějovice
            ("ATE Brakes", 50.0343, 15.7812, "brakes", "low"),  # Pardubice
            ("Lear Body Parts", 49.2264, 17.6683, "body_parts", "low")  # Zlín
        ]
        
        for supplier in sample_suppliers:
            try:
                cur.execute("""
                    INSERT INTO vw_suppliers (name, location, category, risk_level)
                    VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, supplier)
            except Exception as e:
                print(f"⚠️ Chyba při vkládání dodavatele {supplier[0]}: {str(e)}")
        
        print(f"✅ Přidáno {len(sample_suppliers)} ukázkových dodavatelů")
        
        # 7. Potvrzení, že demo data již nejsou vkládána
        print("📝 Demo data pro risk events již nejsou vkládána - pouze reálná data z web scrapingu")
        print("📝 Demo data pro suppliers jsou vkládána pouze pro testování pokročilých funkcí")
        
        conn.commit()
        print("✅ Databáze úspěšně inicializována pro Risk Analyst Dashboard")
        return True
        
    except Exception as e:
        print(f"❌ Chyba při inicializaci databáze: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

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