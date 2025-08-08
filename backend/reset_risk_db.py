"""
Reset Risk Analyst Database
==========================

Skript pro resetování databáze a čistou inicializaci.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Načtení environment variables
load_dotenv()

def reset_risk_db():
    """Reset a čistá inicializace databáze"""
    
    # Získání DATABASE_URL
    database_url = os.getenv('RISK_DATABASE_URL')
    if not database_url:
        print("❌ Chyba: RISK_DATABASE_URL není nastavena")
        return False
    
    conn = None
    try:
        print("🔗 Připojuji k databázi...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        print("🗑️ Mažu existující data...")
        
        # Smazání existujících dat (ale zachování struktury)
        cur.execute("DELETE FROM risk_events;")
        cur.execute("DELETE FROM vw_suppliers;")
        cur.execute("DELETE FROM rivers;")
        
        print("✅ Existující data smazána")
        
        # Reset sekvencí
        cur.execute("ALTER SEQUENCE risk_events_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE vw_suppliers_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE rivers_id_seq RESTART WITH 1;")
        
        print("✅ Sekvence resetovány")
        
        # Vložení řek
        print("🌊 Vkládám data o řekách...")
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
            cur.execute("""
                INSERT INTO rivers (name, geometry, river_type, flow_direction)
                VALUES (%s, ST_GeomFromText(%s, 4326), %s, %s)
            """, (river['name'], river['geometry'], river['river_type'], river['flow_direction']))

        print("✅ Řeky vloženy")
        
        # Vložení dodavatelů
        print("🏭 Vkládám ukázkové dodavatele...")
        
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
        
        for supplier in sample_suppliers:
            cur.execute("""
                INSERT INTO vw_suppliers (name, location, category, risk_level)
                VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s)
            """, supplier)
        
        print("✅ Dodavatelé vloženi")
        
        # Vložení několika ukázkových rizikových událostí pro testování
        print("⚠️ Vkládám ukázkové rizikové události...")
        
        sample_events = [
            ("Záplavy v Praze", "flood", "critical", 50.0755, 14.4378, "Vysoké srážky způsobily záplavy v centru Prahy"),
            ("Dopravní nehoda na D1", "traffic", "high", 49.1951, 16.6068, "Hromadná nehoda na dálnici D1 u Brna"),
            ("Výpadek elektřiny v Hradci", "infrastructure", "medium", 50.2092, 15.8327, "Plánovaná údržba elektrické sítě"),
            ("Protesty v Plzni", "social", "low", 49.7475, 13.3776, "Demonstrace proti zvýšení cen")
        ]
        
        for event in sample_events:
            cur.execute("""
                INSERT INTO risk_events (title, event_type, severity, location, description, created_at)
                VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, NOW())
            """, event)
        
        print("✅ Ukázkové události vloženy")
        
        conn.commit()
        print("✅ Databáze úspěšně resetována a inicializována")
        return True
        
    except Exception as e:
        print(f"❌ Chyba při resetování databáze: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("RISK ANALYST DATABASE RESET")
    print("=" * 50)
    
    success = reset_risk_db()
    
    if success:
        print("✅ Reset úspěšný!")
        sys.exit(0)
    else:
        print("❌ Reset selhal!")
        sys.exit(1) 