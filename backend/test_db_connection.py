"""
Test připojení k databázi pro Render

Tento skript testuje připojení k databázi pomocí různých metod
pro pomoc při diagnóze problémů s připojením.
"""

import os
import psycopg2
import sys
from urllib.parse import urlparse
import time

def test_connection():
    print("=== Test připojení k databázi ===")
    
    # Kontrola proměnných prostředí
    print("\n1. Kontrola proměnných prostředí:")
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL není nastavena!")
        return False
    
    print(f"DATABASE_URL existuje a začíná: {DATABASE_URL[:10]}...")
    
    # Analýza URL
    print("\n2. Analýza DATABASE_URL:")
    try:
        parsed = urlparse(DATABASE_URL)
        print(f"Schema: {parsed.scheme}")
        print(f"Netloc: {parsed.netloc}")
        print(f"Path: {parsed.path}")
        
        host = parsed.hostname or ''
        port = parsed.port or ''
        username = parsed.username or ''
        password_present = bool(parsed.password)
        
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Username: {username}")
        print(f"Password existuje: {password_present}")
        
        # Test správnosti schématu
        if parsed.scheme == 'postgres':
            print("URL začíná 'postgres://' - zkusíme upravit na 'postgresql://'")
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
    except Exception as e:
        print(f"Chyba při analýze URL: {str(e)}")
    
    # Pokus o připojení
    print("\n3. Pokus o připojení k databázi:")
    try:
        print("Připojování...")
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        print("✅ Připojení úspěšné!")
        
        # Test dotazu
        print("\n4. Test dotazu:")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"Verze databáze: {version}")
        
        # Test PostGIS
        print("\n5. Test PostGIS:")
        try:
            cursor.execute("SELECT PostGIS_Version();")
            postgis_version = cursor.fetchone()[0]
            print(f"✅ PostGIS je nainstalován, verze: {postgis_version}")
        except Exception as e:
            print(f"❌ PostGIS není nainstalován: {str(e)}")
        
        # Test tabulky
        print("\n6. Test tabulky memories:")
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')")
        table_exists = cursor.fetchone()[0]
        if table_exists:
            print("✅ Tabulka 'memories' existuje")
            
            # Kontrola počtu záznamů
            cursor.execute("SELECT COUNT(*) FROM memories")
            count = cursor.fetchone()[0]
            print(f"   Počet záznamů: {count}")
            
            if count > 0:
                # Ukázka prvního záznamu
                cursor.execute("SELECT id, text, location FROM memories LIMIT 1")
                row = cursor.fetchone()
                print(f"   První záznam: ID={row[0]}, Místo={row[1]}, Text={row[2]}")
        else:
            print("❌ Tabulka 'memories' NEEXISTUJE")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Chyba při připojení: {str(e)}")
        
        # Zkusíme ještě psycopg2.connect s jednotlivými parametry
        try:
            # Extrahujeme parametry z URL
            parsed = urlparse(DATABASE_URL)
            dbname = parsed.path[1:] if parsed.path else ''
            user = parsed.username
            password = parsed.password
            host = parsed.hostname
            port = parsed.port
            
            print("\nZkouším alternativní připojení s parametry:")
            print(f"host={host}, port={port}, dbname={dbname}, user={user}, password=***")
            
            alt_conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=user,
                password=password,
                connect_timeout=10
            )
            print("✅ Alternativní připojení úspěšné!")
            alt_conn.close()
        except Exception as alt_e:
            print(f"❌ Alternativní připojení také selhalo: {str(alt_e)}")
        
        return False

if __name__ == "__main__":
    if test_connection():
        print("\n✅ Test připojení k databázi ÚSPĚŠNÝ")
        sys.exit(0)
    else:
        print("\n❌ Test připojení k databázi NEÚSPĚŠNÝ")
        sys.exit(1) 