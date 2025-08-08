#!/usr/bin/env python3
"""
Test script pro ověření meteorologických API
"""

import requests
import json
from datetime import datetime

def test_openweathermap():
    """Test OpenWeatherMap API"""
    print("🌤️ Testuji OpenWeatherMap API...")
    
    # Bezplatný API key (demo)
    api_key = "demo"  # V produkci by byl skutečný API key
    city = "Prague"
    
    try:
        # Test aktuálního počasí
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        
        print(f"📊 Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ OpenWeatherMap funguje")
            print(f"🌡️ Teplota: {data.get('main', {}).get('temp', 'N/A')}°C")
            print(f"💧 Vlhkost: {data.get('main', {}).get('humidity', 'N/A')}%")
            print(f"🌪️ Vítr: {data.get('wind', {}).get('speed', 'N/A')} m/s")
            return True
        else:
            print(f"❌ OpenWeatherMap nefunguje: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Chyba OpenWeatherMap: {e}")
        return False

def test_alternative_chmi():
    """Test alternativních CHMI endpointů"""
    print("\n🌊 Testuji alternativní CHMI endpointy...")
    
    # Nové možné CHMI endpointy
    chmi_endpoints = [
        "https://hydro.chmi.cz/hpps/hpps_act.php",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=1",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=2",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=3",
        # Nové možné endpointy
        "https://hydro.chmi.cz/hpps/",
        "https://hydro.chmi.cz/hpps/index.php",
        "https://hydro.chmi.cz/hpps/hpps.php",
        "https://hydro.chmi.cz/hpps/quick.php",
        "https://hydro.chmi.cz/hpps/act.php"
    ]
    
    working_endpoints = []
    
    for endpoint in chmi_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            status = response.status_code
            content_len = len(response.text)
            
            print(f"  {endpoint}: {status} ({content_len} znaků)")
            
            if status == 200 and content_len > 100:
                working_endpoints.append(endpoint)
                print(f"    ✅ FUNGUJE!")
            elif status == 200:
                print(f"    ⚠️ Status OK, ale málo dat")
            else:
                print(f"    ❌ Neúspěšné")
                
        except Exception as e:
            print(f"  {endpoint}: ERROR - {str(e)}")
    
    return working_endpoints

def test_povodi_cr():
    """Test Povodí ČR"""
    print("\n🏞️ Testuji Povodí ČR...")
    
    povodi_endpoints = [
        "https://www.pvl.cz/portal/sap/cz/",
        "https://www.pvl.cz/portal/sap/cz/hydro/",
        "https://www.pvl.cz/portal/sap/cz/hydro/aktualni-stavy/",
        "https://www.pvl.cz/portal/sap/cz/hydro/aktualni-stavy/vltava/",
        "https://www.pvl.cz/portal/sap/cz/hydro/aktualni-stavy/labe/"
    ]
    
    working_endpoints = []
    
    for endpoint in povodi_endpoints:
        try:
            response = requests.get(endpoint, timeout=10)
            status = response.status_code
            content_len = len(response.text)
            
            print(f"  {endpoint}: {status} ({content_len} znaků)")
            
            if status == 200 and content_len > 1000:
                working_endpoints.append(endpoint)
                print(f"    ✅ FUNGUJE!")
            elif status == 200:
                print(f"    ⚠️ Status OK, ale málo dat")
            else:
                print(f"    ❌ Neúspěšné")
                
        except Exception as e:
            print(f"  {endpoint}: ERROR - {str(e)}")
    
    return working_endpoints

def test_weather_apis():
    """Test dalších weather API"""
    print("\n🌦️ Testuji další weather API...")
    
    # OpenMeteo (bezplatné, bez API key)
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.0755&longitude=14.4378&current_weather=true"
        response = requests.get(url, timeout=10)
        
        print(f"  OpenMeteo: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            temp = data.get('current_weather', {}).get('temperature', 'N/A')
            print(f"    ✅ FUNGUJE! Teplota: {temp}°C")
        else:
            print(f"    ❌ Neúspěšné")
    except Exception as e:
        print(f"  OpenMeteo: ERROR - {str(e)}")
    
    # WeatherAPI (demo)
    try:
        url = "http://api.weatherapi.com/v1/current.json?key=demo&q=Prague"
        response = requests.get(url, timeout=10)
        
        print(f"  WeatherAPI: {response.status_code}")
        if response.status_code == 200:
            print(f"    ✅ FUNGUJE!")
        else:
            print(f"    ❌ Neúspěšné")
    except Exception as e:
        print(f"  WeatherAPI: ERROR - {str(e)}")

def main():
    """Hlavní test funkce"""
    print("🧪 Testuji meteorologické API...")
    print("=" * 60)
    
    # Test 1: OpenWeatherMap
    openweather_works = test_openweathermap()
    
    # Test 2: Alternativní CHMI
    working_chmi = test_alternative_chmi()
    
    # Test 3: Povodí ČR
    working_povodi = test_povodi_cr()
    
    # Test 4: Další weather API
    test_weather_apis()
    
    print("\n" + "=" * 60)
    print("📊 SHRNUTÍ:")
    print(f"  OpenWeatherMap: {'✅' if openweather_works else '❌'}")
    print(f"  CHMI alternativy: {len(working_chmi)} funkčních")
    print(f"  Povodí ČR: {len(working_povodi)} funkčních")
    
    if working_chmi:
        print(f"\n✅ FUNKČNÍ CHMI ENDPOINTY:")
        for endpoint in working_chmi:
            print(f"  - {endpoint}")
    
    if working_povodi:
        print(f"\n✅ FUNKČNÍ POVODÍ ČR ENDPOINTY:")
        for endpoint in working_povodi:
            print(f"  - {endpoint}")

if __name__ == "__main__":
    main() 