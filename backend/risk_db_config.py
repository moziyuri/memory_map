"""
Konfigurace pro Risk Analyst databázi

Tento modul poskytuje připojení k nové PostgreSQL databázi
pro risk analyst feature.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Generator

# Konfigurace pro novou risk analyst databázi
RISK_DATABASE_CONFIG = {
    'host': 'dpg-d2a54tp5pdvs73acu64g-a.frankfurt-postgres.render.com',
    'port': '5432',
    'dbname': 'risk_analyst',
    'user': 'risk_analyst_user',
    'password': 'uN3Zogp6tvoTmnjNV4owD92Nnm6UlGkf',
    'sslmode': 'require'
}

def get_risk_db() -> Generator:
    """
    Vytvoří a poskytuje připojení k risk analyst databázi.
    """
    conn = None
    try:
        conn = psycopg2.connect(
            host=RISK_DATABASE_CONFIG['host'],
            port=RISK_DATABASE_CONFIG['port'],
            dbname=RISK_DATABASE_CONFIG['dbname'],
            user=RISK_DATABASE_CONFIG['user'],
            password=RISK_DATABASE_CONFIG['password'],
            sslmode=RISK_DATABASE_CONFIG['sslmode']
        )
        yield conn
    except Exception as e:
        print(f"Chyba při připojení k risk analyst databázi: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()

def test_risk_db_connection():
    """Testuje připojení k risk analyst databázi"""
    try:
        conn = psycopg2.connect(
            host=RISK_DATABASE_CONFIG['host'],
            port=RISK_DATABASE_CONFIG['port'],
            dbname=RISK_DATABASE_CONFIG['dbname'],
            user=RISK_DATABASE_CONFIG['user'],
            password=RISK_DATABASE_CONFIG['password'],
            sslmode=RISK_DATABASE_CONFIG['sslmode']
        )
        
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM risk_events")
            risk_count = cur.fetchone()[0]
            print(f"✅ Připojení k risk analyst databázi úspěšné! Počet risk events: {risk_count}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Chyba při testování risk analyst databáze: {str(e)}")
        return False

if __name__ == "__main__":
    test_risk_db_connection() 