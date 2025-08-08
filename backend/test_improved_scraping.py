#!/usr/bin/env python3
"""
Test script pro ověření vylepšeného scrapingu
"""

import requests
import json
from datetime import datetime

# Konfigurace
BACKEND_URL = "https://risk-analyst.onrender.com"

def test_improved_scraping():
    """Test vylepšeného scrapingu"""
    print("🔍 Testuji vylepšený scraping...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/test-scraping-improved", timeout=120)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Vylepšený scraping test úspěšný!")
            
            results = data.get('results', {})
            
            # CHMI test
            chmi_test = results.get('chmi_test', {})
            if 'error' in chmi_test:
                print(f"❌ CHMI test selhal: {chmi_test['error']}")
            else:
                print(f"✅ CHMI test: {chmi_test.get('saved_count', 0)} událostí uloženo")
                print(f"   Zdroj: {chmi_test.get('source_url', 'unknown')}")
            
            # RSS test
            rss_test = results.get('rss_test', {})
            if 'error' in rss_test:
                print(f"❌ RSS test selhal: {rss_test['error']}")
            else:
                print(f"✅ RSS test: {rss_test.get('saved_count', 0)} událostí uloženo")
            
            # OpenMeteo test
            openmeteo_test = results.get('openmeteo_test', {})
            if 'error' in openmeteo_test:
                print(f"❌ OpenMeteo test selhal: {openmeteo_test['error']}")
            else:
                print(f"✅ OpenMeteo test: {openmeteo_test.get('scraped_count', 0)} událostí nalezeno")
                events = openmeteo_test.get('events', [])
                if events:
                    print(f"   Ukázka událostí:")
                    for i, event in enumerate(events[:3], 1):
                        print(f"   {i}. {event.get('title', 'N/A')}")
            
            return True
        else:
            print(f"❌ Test selhal: {response.status_code}")
            print(f"Odpověď: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Chyba při testování: {str(e)}")
        return False

def test_individual_scrapers():
    """Test jednotlivých scraperů"""
    print("\n🔍 Testuji jednotlivé scrapery...")
    
    # Test CHMI
    try:
        response = requests.get(f"{BACKEND_URL}/api/scrape/chmi", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ CHMI scraper: {data.get('saved_count', 0)} událostí")
        else:
            print(f"❌ CHMI scraper selhal: {response.status_code}")
    except Exception as e:
        print(f"❌ CHMI scraper chyba: {str(e)}")
    
    # Test RSS
    try:
        response = requests.get(f"{BACKEND_URL}/api/scrape/rss", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ RSS scraper: {data.get('saved_count', 0)} událostí")
        else:
            print(f"❌ RSS scraper selhal: {response.status_code}")
    except Exception as e:
        print(f"❌ RSS scraper chyba: {str(e)}")
    
    # Test OpenMeteo
    try:
        response = requests.get(f"{BACKEND_URL}/api/test-openmeteo", timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                temp = data.get('temperature', 'N/A')
                wind = data.get('windspeed', 'N/A')
                print(f"✅ OpenMeteo API: Teplota {temp}°C, Vítr {wind} km/h")
            else:
                print(f"❌ OpenMeteo API: {data.get('error', 'Neznámá chyba')}")
        else:
            print(f"❌ OpenMeteo API selhal: {response.status_code}")
    except Exception as e:
        print(f"❌ OpenMeteo API chyba: {str(e)}")

def main():
    """Hlavní test funkce"""
    print("🧪 Testuji vylepšený scraping...")
    print(f"📍 Backend URL: {BACKEND_URL}")
    print(f"⏰ Čas: {datetime.now()}")
    print("=" * 60)
    
    # Test 1: Vylepšený scraping
    improved_success = test_improved_scraping()
    
    # Test 2: Jednotlivé scrapery
    test_individual_scrapers()
    
    print("\n" + "=" * 60)
    print("📊 SHRNUTÍ:")
    print(f"  Vylepšený scraping: {'✅' if improved_success else '❌'}")
    
    if improved_success:
        print("✅ Vylepšený scraping funguje!")
    else:
        print("❌ Vylepšený scraping selhal")
    
    print("\n🏁 Testy dokončeny!")

if __name__ == "__main__":
    main() 