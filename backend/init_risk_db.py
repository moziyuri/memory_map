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
        try:
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
        except Exception as e:
            print(f"⚠️ Chyba při vytváření risk_events: {str(e)}")
        
        # Tabulka vw_suppliers
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vw_suppliers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    location GEOGRAPHY(POINT, 4326),  -- Geografická pozice
                    category VARCHAR(100), -- 'electronics', 'tires', 'steering', 'brakes'
                    risk_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            print("✅ Tabulka vw_suppliers vytvořena/zkontrolována")
        except Exception as e:
            print(f"⚠️ Chyba při vytváření vw_suppliers: {str(e)}")
        
        # Přidání tabulky pro řeky (polygony)
        try:
            cur.execute("""
CREATE TABLE IF NOT EXISTS rivers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    geometry GEOMETRY(POLYGON, 4326),
    river_type VARCHAR(50),
    flow_direction VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
        except Exception as e:
            print(f"⚠️ Chyba při vytváření rivers: {str(e)}")

        # Vytvoření indexu pro prostorové vyhledávání
        try:
            cur.execute("""
CREATE INDEX IF NOT EXISTS idx_rivers_geometry 
ON rivers USING GIST (geometry);
""")
        except Exception as e:
            print(f"⚠️ Chyba při vytváření rivers indexu: {str(e)}")

        # Vložení základních řek ČR jako polygony (simulované, ale reálné struktury)
        rivers_data = [
            {
                'name': 'Vltava',
                'geometry': 'POLYGON((14.0 50.0, 14.5 50.1, 14.8 50.2, 15.0 50.3, 14.8 50.4, 14.5 50.5, 14.0 50.4, 13.8 50.3, 13.5 50.2, 13.2 50.1, 14.0 50.0))',
                'river_type': 'major',
                'flow_direction': 'north'
            },
            {
                'name': 'Labe',
                'geometry': 'POLYGON((15.5 50.0, 16.0 50.1, 16.5 50.2, 17.0 50.3, 16.8 50.4, 16.5 50.5, 16.0 50.4, 15.5 50.3, 15.2 50.2, 15.0 50.1, 15.5 50.0))',
                'river_type': 'major',
                'flow_direction': 'north'
            },
            {
                'name': 'Morava',
                'geometry': 'POLYGON((16.5 49.0, 17.0 49.1, 17.5 49.2, 18.0 49.3, 17.8 49.4, 17.5 49.5, 17.0 49.4, 16.5 49.3, 16.2 49.2, 16.0 49.1, 16.5 49.0))',
                'river_type': 'major',
                'flow_direction': 'south'
            },
            {
                'name': 'Ohře',
                'geometry': 'POLYGON((12.5 50.0, 13.0 50.1, 13.5 50.2, 14.0 50.3, 13.8 50.4, 13.5 50.5, 13.0 50.4, 12.5 50.3, 12.2 50.2, 12.0 50.1, 12.5 50.0))',
                'river_type': 'major',
                'flow_direction': 'east'
            },
            {
                'name': 'Berounka',
                'geometry': 'POLYGON((13.0 49.5, 13.5 49.6, 14.0 49.7, 14.5 49.8, 14.3 49.9, 14.0 50.0, 13.5 49.9, 13.0 49.8, 12.7 49.7, 12.5 49.6, 13.0 49.5))',
                'river_type': 'major',
                'flow_direction': 'north'
            }
        ]

        for river in rivers_data:
            try:
                cur.execute("""
                    INSERT INTO rivers (name, geometry, river_type, flow_direction)
                    VALUES (%s, ST_GeomFromText(%s, 4326), %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (river['name'], river['geometry'], river['river_type'], river['flow_direction']))
            except Exception as e:
                print(f"⚠️ Chyba při vkládání řeky {river['name']}: {str(e)}")

        # Funkce pro výpočet vzdálenosti od řeky pomocí polygonů
        try:
            cur.execute("""
CREATE OR REPLACE FUNCTION calculate_river_distance(lat DOUBLE PRECISION, lon DOUBLE PRECISION)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    min_distance DOUBLE PRECISION := 999999;
    river_distance DOUBLE PRECISION;
    river_record RECORD;
BEGIN
    FOR river_record IN 
        SELECT name, ST_Distance(
            ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
            geometry::geography
        ) as distance
        FROM rivers
    LOOP
        river_distance := river_record.distance / 1000; -- Převod na km
        IF river_distance < min_distance THEN
            min_distance := river_distance;
        END IF;
    END LOOP;
    
    RETURN min_distance;
END;
$$ LANGUAGE plpgsql;
""")
        except Exception as e:
            print(f"⚠️ Chyba při vytváření calculate_river_distance: {str(e)}")

        # Funkce pro analýzu rizika záplav na základě polygonů řek
        try:
            cur.execute("""
CREATE OR REPLACE FUNCTION analyze_flood_risk_from_rivers(lat DOUBLE PRECISION, lon DOUBLE PRECISION)
RETURNS JSON AS $$
DECLARE
    nearest_river_name VARCHAR(255);
    nearest_river_distance DOUBLE PRECISION;
    flood_risk_level VARCHAR(50);
    flood_probability DOUBLE PRECISION;
    result JSON;
BEGIN
    -- Najít nejbližší řeku
    SELECT name, ST_Distance(
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
        geometry::geography
    ) / 1000 as distance
    INTO nearest_river_name, nearest_river_distance
    FROM rivers
    ORDER BY ST_Distance(
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
        geometry::geography
    )
    LIMIT 1;
    
    -- Výpočet rizika na základě vzdálenosti
    IF nearest_river_distance < 2.0 THEN
        flood_risk_level := 'critical';
        flood_probability := 0.9;
    ELSIF nearest_river_distance < 5.0 THEN
        flood_risk_level := 'high';
        flood_probability := 0.7;
    ELSIF nearest_river_distance < 10.0 THEN
        flood_risk_level := 'medium';
        flood_probability := 0.4;
    ELSE
        flood_risk_level := 'low';
        flood_probability := 0.1;
    END IF;
    
    result := json_build_object(
        'nearest_river_name', nearest_river_name,
        'nearest_river_distance_km', nearest_river_distance,
        'flood_risk_level', flood_risk_level,
        'flood_probability', flood_probability,
        'mitigation_needed', flood_risk_level IN ('critical', 'high')
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
""")
        except Exception as e:
            print(f"⚠️ Chyba při vytváření analyze_flood_risk_from_rivers: {str(e)}")
        
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
        try:
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
        except Exception as e:
            print(f"⚠️ Chyba při vytváření calculate_risk_in_radius: {str(e)}")
        
        # 5. Databáze je připravena pro reálná data
        print("📝 Databáze je připravena pro reálná data z web scrapingu...")
        
        # 6. Přidání ukázkových dodavatelů pro testování pokročilých funkcí
        print("🏭 Přidávám ukázkové dodavatele pro testování...")
        
        sample_suppliers = [
            # Kritičtí dodavatelé v rizikových oblastech (blízko řek)
            ("Bosch Electronics Praha", 50.0755, 14.4378, "electronics", "critical"),  # Praha - blízko Vltavy
            ("Continental Tires Brno", 49.1951, 16.6068, "tires", "critical"),  # Brno - blízko Moravy
            ("ZF Steering Hradec", 50.2092, 15.8327, "steering", "high"),  # Hradec Králové - blízko Labe
            ("Brembo Brakes Plzeň", 49.7475, 13.3776, "brakes", "high"),  # Plzeň - blízko Berounky
            ("Magna Body Parts Karlovy Vary", 50.231, 12.880, "body_parts", "medium"),  # Karlovy Vary - blízko Ohře
            
            # Dodavatelé v bezpečnějších oblastech (dále od řek)
            ("Siemens Electronics Liberec", 50.7663, 15.0543, "electronics", "medium"),  # Liberec
            ("Michelin Tires Olomouc", 49.5938, 17.2507, "tires", "medium"),  # Olomouc
            ("TRW Steering České Budějovice", 48.9745, 14.4747, "steering", "low"),  # České Budějovice
            ("ATE Brakes Pardubice", 50.0343, 15.7812, "brakes", "low"),  # Pardubice
            ("Lear Body Parts Zlín", 49.2264, 17.6683, "body_parts", "low")  # Zlín
        ]
        
        # Vylepšená logika pro přidání dodavatelů s lepším error handlingem
        suppliers_added = 0
        suppliers_skipped = 0
        
        for supplier in sample_suppliers:
            try:
                # Nejdříve zkontrolujeme, zda dodavatel již existuje
                cur.execute("SELECT COUNT(*) FROM vw_suppliers WHERE name = %s", (supplier[0],))
                exists = cur.fetchone()[0] > 0
                
                if not exists:
                    # Vložíme nového dodavatele
                    cur.execute("""
                        INSERT INTO vw_suppliers (name, location, category, risk_level)
                        VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
                    """, supplier)
                    suppliers_added += 1
                else:
                    suppliers_skipped += 1
                    
            except Exception as e:
                print(f"⚠️ Chyba při vkládání dodavatele {supplier[0]}: {str(e)}")
                suppliers_skipped += 1
                # Pokračujeme s dalšími dodavateli místo přerušení transakce
                continue
        
        print(f"✅ Přidáno {suppliers_added} nových dodavatelů, {suppliers_skipped} přeskočeno (již existují)")
        
        # 7. Potvrzení, že demo data již nejsou vkládána
        print("📝 Demo data pro risk events již nejsou vkládána - pouze reálná data z web scrapingu")
        print("📝 Demo data pro suppliers jsou vkládána pouze pro testování pokročilých funkcí")
        
        # Pokusíme se commitnout transakci
        try:
            conn.commit()
            print("✅ Databáze úspěšně inicializována pro Risk Analyst Dashboard")
            return True
        except Exception as e:
            print(f"❌ Chyba při commitování transakce: {str(e)}")
            try:
                conn.rollback()
                print("🔄 Transakce byla rollbackována")
            except Exception as rollback_error:
                print(f"⚠️ Chyba při rollbacku: {str(rollback_error)}")
            return False
        
    except Exception as e:
        print(f"❌ Chyba při inicializaci databáze: {str(e)}")
        try:
            if conn:
                conn.rollback()
                print("🔄 Transakce byla rollbackována kvůli chybě")
        except Exception as rollback_error:
            print(f"⚠️ Chyba při rollbacku: {str(rollback_error)}")
        return False
    finally:
        try:
            if conn:
                conn.close()
                print("🔌 Připojení k databázi uzavřeno")
        except Exception as close_error:
            print(f"⚠️ Chyba při uzavírání připojení: {str(close_error)}")

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