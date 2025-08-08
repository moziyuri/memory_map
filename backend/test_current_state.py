#!/usr/bin/env python3
"""
Test script pro kontrolu aktuálního stavu backendu
"""

import requests
import json
from datetime import datetime

# Konfigurace
BACKEND_URL = "https://risk-analyst.onrender.com"

def test_backend_health():
    """Test zdraví backendu"""
    print("🔍 Testuji zdraví backendu...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 Odpověď: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return False

def test_chmi_endpoints():
    """Test CHMI endpointů"""
    print("\n🔍 Testuji CHMI endpointy...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/test-chmi", timeout=10)
        print(f"✅ CHMI test: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📄 Data: {json.dumps(data, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return False

def test_scraping():
    """Test scrapingu"""
    print("\n🔍 Testuji scraping...")
    try:
        response = requests.get(f"{BACKEND_URL}/api/scrape/run-all", timeout=60)
        print(f"✅ Scraping: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"📄 Výsledky:")
            if 'results' in data:
                results = data['results']
                print(f"  - CHMI: {results.get('chmi', {}).get('saved_count', 0)} událostí")
                print(f"  - RSS: {results.get('rss', {}).get('saved_count', 0)} událostí")
                print(f"  - Test data: {results.get('test_data_created', 0)} událostí")
                print(f"  - Celkem: {results.get('total_events_saved', 0)} událostí")
            else:
                print(f"  - Nečekaná struktura: {json.dumps(data, indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Chyba: {e}")
        return False

def test_data_retrieval():
    """Test načítání dat"""
    print("\n🔍 Testuji načítání dat...")
    
    # Test událostí
    try:
        response = requests.get(f"{BACKEND_URL}/api/risks", timeout=10)
        print(f"✅ Události: {response.status_code}")
        if response.status_code == 200:
            events = response.json()
            print(f"  - Počet událostí: {len(events)}")
            if events:
                print(f"  - První událost: {events[0].get('title', 'N/A')}")
        else:
            print(f"  - Chyba: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Chyba událostí: {e}")
    
    # Test dodavatelů
    try:
        response = requests.get(f"{BACKEND_URL}/api/suppliers", timeout=10)
        print(f"✅ Dodavatelé: {response.status_code}")
        if response.status_code == 200:
            suppliers = response.json()
            print(f"  - Počet dodavatelů: {len(suppliers)}")
            if suppliers:
                print(f"  - První dodavatel: {suppliers[0].get('name', 'N/A')}")
        else:
            print(f"  - Chyba: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Chyba dodavatelů: {e}")

def test_chmi_api_directly():
    """Test CHMI API přímo"""
    print("\n🔍 Testuji CHMI API přímo...")
    chmi_endpoints = [
        "https://hydro.chmi.cz/hpps/",
        "https://hydro.chmi.cz/hpps/index.php",
        "https://hydro.chmi.cz/hpps/hpps_act.php",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=1"
    ]
    
    for endpoint in chmi_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            print(f"✅ {endpoint}: {response.status_code} ({len(response.text)} znaků)")
            if response.status_code == 200:
                print(f"  - Prvních 200 znaků: {response.text[:200]}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def test_openmeteo_api():
    """Test OpenMeteo API"""
    print("\n🌤️ Testuji OpenMeteo API...")
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.0755&longitude=14.4378&current_weather=true&hourly=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        response = requests.get(url, timeout=10)
        print(f"✅ OpenMeteo API: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            current_weather = data.get('current_weather', {})
            temp = current_weather.get('temperature', 'N/A')
            wind = current_weather.get('windspeed', 'N/A')
            print(f"  - Teplota: {temp}°C")
            print(f"  - Vítr: {wind} km/h")
            return True
        else:
            print(f"❌ OpenMeteo API: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chyba OpenMeteo API: {e}")
        return False

def main():
    """Hlavní funkce"""
    print("🚀 Spouštím testy backendu...")
    print(f"📍 Backend URL: {BACKEND_URL}")
    print(f"⏰ Čas: {datetime.now()}")
    print("=" * 50)
    
    # Spuštění testů
    health_ok = test_backend_health()
    chmi_ok = test_chmi_endpoints()
    openmeteo_ok = test_openmeteo_api()
    scraping_ok = test_scraping()
    test_data_retrieval()
    test_chmi_api_directly()
    
    # Shrnutí
    print("\n" + "=" * 50)
    print("📊 SHRNUTÍ:")
    print(f"  - Backend zdraví: {'✅' if health_ok else '❌'}")
    print(f"  - CHMI endpointy: {'✅' if chmi_ok else '❌'}")
    print(f"  - OpenMeteo API: {'✅' if openmeteo_ok else '❌'}")
    print(f"  - Scraping: {'✅' if scraping_ok else '❌'}")
    
    if not chmi_ok:
        print("\n⚠️ CHMI endpointy nefungují - možná je potřeba redeploy backendu")
    
    if openmeteo_ok:
        print("\n✅ OpenMeteo API funguje - bude použit jako fallback")
    
    print("\n🏁 Testy dokončeny!")

if __name__ == "__main__":
    main() 