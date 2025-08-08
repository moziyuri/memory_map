#!/usr/bin/env python3
"""
Test script pro ověření funkcionality backendu
"""

import requests
import json
import time

# Konfigurace
BACKEND_URL = "https://risk-analyst.onrender.com"

def test_backend_health():
    """Test zdraví backendu"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        print(f"🏥 Health check: {response.status_code}")
        if response.status_code == 200:
            print("✅ Backend je dostupný")
            return True
        else:
            print(f"❌ Backend není dostupný: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chyba při health check: {e}")
        return False

def test_chmi_endpoints():
    """Test CHMI endpointů"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/test-chmi", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print("🔍 CHMI test výsledky:")
            for endpoint, result in data.get('chmi_test_results', {}).items():
                status = result.get('status_code', 'ERROR')
                content_len = result.get('content_length', 0)
                print(f"  {endpoint}: {status} ({content_len} znaků)")
        else:
            print(f"❌ CHMI test selhal: {response.status_code}")
    except Exception as e:
        print(f"❌ Chyba při CHMI testu: {e}")

def test_openmeteo_api():
    """Test OpenMeteo API"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/test-openmeteo", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                temp = data.get('temperature', 'N/A')
                wind = data.get('windspeed', 'N/A')
                print(f"🌤️ OpenMeteo API: ✅ Teplota: {temp}°C, Vítr: {wind} km/h")
            else:
                print(f"❌ OpenMeteo API: {data.get('error', 'Neznámá chyba')}")
        else:
            print(f"❌ OpenMeteo test selhal: {response.status_code}")
    except Exception as e:
        print(f"❌ Chyba při OpenMeteo testu: {e}")

def test_scraping():
    """Test scrapingu"""
    try:
        print("🔄 Spouštím scraping...")
        response = requests.get(f"{BACKEND_URL}/api/scrape/run-all", timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Scraping dokončen")
            
            results = data.get('results', {})
            chmi_saved = results.get('chmi', {}).get('saved_count', 0)
            rss_saved = results.get('rss', {}).get('saved_count', 0)
            test_data = results.get('test_data_created', 0)
            total = results.get('total_events_saved', 0)
            
            print(f"📊 Výsledky:")
            print(f"  CHMI: {chmi_saved} událostí")
            print(f"  RSS: {rss_saved} událostí")
            print(f"  Test data: {test_data} událostí")
            print(f"  Celkem: {total} událostí")
            
            return total > 0
        else:
            print(f"❌ Scraping selhal: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chyba při scrapingu: {e}")
        return False

def test_data_retrieval():
    """Test načítání dat"""
    try:
        # Test událostí
        response = requests.get(f"{BACKEND_URL}/api/risks", timeout=10)
        if response.status_code == 200:
            events = response.json()
            print(f"📊 Události: {len(events)}")
        else:
            print(f"❌ Chyba při načítání událostí: {response.status_code}")
        
        # Test dodavatelů
        response = requests.get(f"{BACKEND_URL}/api/suppliers", timeout=10)
        if response.status_code == 200:
            suppliers = response.json()
            print(f"🏭 Dodavatelé: {len(suppliers)}")
        else:
            print(f"❌ Chyba při načítání dodavatelů: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Chyba při načítání dat: {e}")

def main():
    """Hlavní test funkce"""
    print("🧪 Spouštím testy backendu...")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_backend_health():
        print("❌ Backend není dostupný, končím testy")
        return
    
    print()
    
    # Test 2: CHMI endpoints
    test_chmi_endpoints()
    print()

    # Test 3: OpenMeteo API
    test_openmeteo_api()
    print()
    
    # Test 4: Scraping
    scraping_success = test_scraping()
    print()
    
    # Test 5: Data retrieval
    test_data_retrieval()
    print()
    
    print("=" * 50)
    if scraping_success:
        print("✅ Testy dokončeny úspěšně")
    else:
        print("⚠️ Testy dokončeny s varováními")

if __name__ == "__main__":
    main() 