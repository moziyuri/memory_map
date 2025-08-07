"""
Konfigurace pro Risk Analyst databázi

Tento modul poskytuje připojení k nové PostgreSQL databázi
pro risk analyst feature.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Generator
import os

# Konfigurace pro novou risk analyst databázi
def get_risk_db_config():
    """Získá konfiguraci databáze z environment variables nebo fallback"""
    # Zkusíme RISK_DATABASE_URL
    risk_db_url = os.getenv('RISK_DATABASE_URL')
    if risk_db_url:
        return risk_db_url
    
    # Fallback na přímé hodnoty
    return {
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
        config = get_risk_db_config()
        
        if isinstance(config, str):
            # Používáme DATABASE_URL
            if config.startswith('postgres://'):
                config = config.replace('postgres://', 'postgresql://', 1)
            conn = psycopg2.connect(config)
        else:
            # Používáme přímé hodnoty
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                dbname=config['dbname'],
                user=config['user'],
                password=config['password'],
                sslmode=config['sslmode']
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
        config = get_risk_db_config()
        
        if isinstance(config, str):
            # Používáme DATABASE_URL
            if config.startswith('postgres://'):
                config = config.replace('postgres://', 'postgresql://', 1)
            conn = psycopg2.connect(config)
        else:
            # Používáme přímé hodnoty
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                dbname=config['dbname'],
                user=config['user'],
                password=config['password'],
                sslmode=config['sslmode']
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