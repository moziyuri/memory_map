#!/usr/bin/env python3
"""
Script pro kompletní vyčištění databáze risk analyst
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

def clear_all_data():
    """Vyčistí všechna data z databáze"""
    
    # Zjištění URL databáze
    DATABASE_URL = os.getenv('RISK_DATABASE_URL') or os.getenv('DATABASE_URL')
    
    if not DATABASE_URL:
        print("❌ Chyba: DATABASE_URL není nastavena")
        return False
    
    # Úprava URL pro psycopg2
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Připojení k databázi s SSL
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        print("✅ Připojení k databázi úspěšné")
        
        with conn.cursor() as cur:
            # Vyčištění všech tabulek
            print("🗑️ Mažu všechna data...")
            
            # Smazání všech risk_events
            cur.execute("DELETE FROM risk_events")
            events_deleted = cur.rowcount
            print(f"🗑️ Smazáno {events_deleted} risk událostí")
            
            # Smazání všech suppliers (kromě základních)
            cur.execute("DELETE FROM vw_suppliers WHERE id > 10")
            suppliers_deleted = cur.rowcount
            print(f"🗑️ Smazáno {suppliers_deleted} dodavatelů")
            
            # Smazání všech rivers (kromě základních)
            cur.execute("DELETE FROM rivers WHERE id > 5")
            rivers_deleted = cur.rowcount
            print(f"🗑️ Smazáno {rivers_deleted} řek")
            
            # Reset sekvencí
            cur.execute("ALTER SEQUENCE risk_events_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE vw_suppliers_id_seq RESTART WITH 11")
            cur.execute("ALTER SEQUENCE rivers_id_seq RESTART WITH 6")
            
            conn.commit()
            print("✅ Databáze vyčištěna")
            
            # Kontrola stavu
            cur.execute("SELECT COUNT(*) FROM risk_events")
            events_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM vw_suppliers")
            suppliers_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM rivers")
            rivers_count = cur.fetchone()[0]
            
            print(f"📊 Aktuální stav:")
            print(f"   Události: {events_count}")
            print(f"   Dodavatelé: {suppliers_count}")
            print(f"   Řeky: {rivers_count}")
            
            return True
            
    except Exception as e:
        print(f"❌ Chyba při čištění databáze: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🧹 Spouštím kompletní vyčištění databáze...")
    success = clear_all_data()
    if success:
        print("✅ Vyčištění dokončeno úspěšně")
    else:
        print("❌ Vyčištění selhalo") 