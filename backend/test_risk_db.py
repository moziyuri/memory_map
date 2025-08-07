"""
Testovací skript pro ověření risk analyst databáze
"""
import psycopg2
import sys

def test_risk_db():
    """Ověří stav risk analyst databáze"""
    
    # Připojení k nové databázi
    host = "dpg-d2a54tp5pdvs73acu64g-a.frankfurt-postgres.render.com"
    port = "5432"
    dbname = "risk_analyst"
    user = "risk_analyst_user"
    password = "uN3Zogp6tvoTmnjNV4owD92Nnm6UlGkf"
    
    print(f"Testuji připojení k databázi: {host}:{port}/{dbname}")
    
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
        
        cur = conn.cursor()
        
        # 1. Ověření PostGIS
        print("\n1. Kontroluji PostGIS...")
        try:
            cur.execute("SELECT PostGIS_Version()")
            version = cur.fetchone()[0]
            print(f"✅ PostGIS verze: {version}")
        except Exception as e:
            print(f"❌ PostGIS chyba: {str(e)}")
        
        # 2. Kontrola tabulek
        print("\n2. Kontroluji tabulky...")
        try:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cur.fetchall()
            print("✅ Dostupné tabulky:")
            for table in tables:
                print(f"   - {table[0]}")
        except Exception as e:
            print(f"❌ Chyba při kontrole tabulek: {str(e)}")
        
        # 3. Kontrola risk_events
        print("\n3. Kontroluji risk_events...")
        try:
            cur.execute("SELECT COUNT(*) FROM risk_events")
            count = cur.fetchone()[0]
            print(f"✅ Počet risk_events: {count}")
            
            if count > 0:
                cur.execute("SELECT id, title, event_type, severity FROM risk_events LIMIT 3")
                events = cur.fetchall()
                print("   První 3 risk events:")
                for event in events:
                    print(f"   - ID {event[0]}: {event[1]} ({event[2]}, {event[3]})")
        except Exception as e:
            print(f"❌ Chyba při kontrole risk_events: {str(e)}")
        
        # 4. Kontrola vw_suppliers
        print("\n4. Kontroluji vw_suppliers...")
        try:
            cur.execute("SELECT COUNT(*) FROM vw_suppliers")
            count = cur.fetchone()[0]
            print(f"✅ Počet vw_suppliers: {count}")
            
            if count > 0:
                cur.execute("SELECT id, name, category, risk_level FROM vw_suppliers LIMIT 3")
                suppliers = cur.fetchall()
                print("   První 3 dodavatelé:")
                for supplier in suppliers:
                    print(f"   - ID {supplier[0]}: {supplier[1]} ({supplier[2]}, {supplier[3]})")
        except Exception as e:
            print(f"❌ Chyba při kontrole vw_suppliers: {str(e)}")
        
        # 5. Test geografické funkce
        print("\n5. Testuji geografickou funkci...")
        try:
            cur.execute("SELECT * FROM calculate_risk_in_radius(50.0755, 14.4378, 50)")
            result = cur.fetchone()
            if result:
                print(f"✅ Funkce calculate_risk_in_radius funguje:")
                print(f"   - Počet eventů: {result[0]}")
                print(f"   - Vysoké riziko: {result[1]}")
                print(f"   - Risk score: {result[2]}%")
            else:
                print("⚠️ Funkce vrátila prázdný výsledek")
        except Exception as e:
            print(f"❌ Chyba při testu funkce: {str(e)}")
        
        conn.close()
        print("\n✅ Test dokončen!")
        return True
        
    except Exception as e:
        print(f"❌ Chyba při připojení: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_risk_db()
    sys.exit(0 if success else 1) 