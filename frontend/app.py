"""
Risk Analyst Dashboard - Interaktivní mapa rizikových událostí

Dashboard pro analýzu rizik v dodavatelském řetězci.

⚠️ Události: Rizikové situace (záplavy, protesty, dodavatelské problémy)
🏭 Dodavatelé: Dodavatelé s hodnocením rizika
📊 Analýza: Vzájemné vztahy a dopady na dodavatelský řetězec

Autor: Vytvořeno jako ukázka dovedností pro Risk Analyst pozici.
"""
# Update: Risk Analyst Dashboard - 2025

import streamlit as st  # Knihovna pro tvorbu webových aplikací
import folium  # Knihovna pro práci s mapami
import requests  # Knihovna pro HTTP požadavky
from streamlit_folium import folium_static, st_folium  # Pro zobrazení folium map ve Streamlitu
from datetime import datetime, timedelta  # Pro práci s datem a časem
import time  # Pro práci s časem
import json  # Pro práci s JSON daty
import os  # Pro práci s proměnnými prostředí
import pandas as pd  # Pro práci s daty

# Konfigurace backendu
BACKEND_URL = os.getenv('BACKEND_URL', 'https://risk-analyst.onrender.com')

# Nastavení stránky - základní konfigurace Streamlit aplikace
st.set_page_config(
    page_title="Risk Analyst Dashboard",  # Titulek stránky v prohlížeči
    page_icon="⚠️",  # Ikona stránky v prohlížeči
    layout="wide",  # Široké rozložení stránky
    initial_sidebar_state="expanded"  # Postranní panel bude na začátku rozbalený
)

# Konstanty aplikace - ČR koordináty
DEFAULT_LAT = 49.8  # Výchozí zeměpisná šířka (zhruba střed ČR)
DEFAULT_LON = 15.5  # Výchozí zeměpisná délka (zhruba střed ČR)

# Omezení na ČR
CZECH_BOUNDS = {
    'min_lat': 48.5, 'max_lat': 51.1,
    'min_lon': 12.0, 'max_lon': 18.9
}

# Nastavení CSS stylů pro lepší vzhled aplikace
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #D32F2F;
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #B71C1C;
        margin-bottom: 1.5rem;
    }
    .success-msg {
        background-color: #DCEDC8;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #8BC34A;
    }
    .error-msg {
        background-color: #FFCCBC;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #FF5722;
    }
    .warning-msg {
        background-color: #FFF3E0;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #FF9800;
    }
    .risk-high {
        color: #D32F2F;
        font-weight: bold;
    }
    .risk-medium {
        color: #FF9800;
        font-weight: bold;
    }
    .risk-low {
        color: #4CAF50;
        font-weight: bold;
    }
    .data-source {
        background-color: #E8F5E8;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        color: #2E7D32;
    }
    .data-fallback {
        background-color: #FFF3E0;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        color: #F57C00;
    }
    .data-scraped {
        background-color: #E3F2FD;
        padding: 2px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        color: #1976D2;
    }
    .tooltip {
        position: relative;
        display: inline-block;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
    }
</style>
""", unsafe_allow_html=True)

# Inicializace session state pro mapu
if 'map_key' not in st.session_state:
    st.session_state.map_key = 0

# Funkce pro kontrolu koordinát v ČR
def is_in_czech_republic(lat, lon):
    """Kontrola, zda jsou koordináty v České republice"""
    return (CZECH_BOUNDS['min_lat'] <= lat <= CZECH_BOUNDS['max_lat'] and 
            CZECH_BOUNDS['min_lon'] <= lon <= CZECH_BOUNDS['max_lon'])

# Funkce pro získání konzistentních statistik
def get_consistent_statistics(events, suppliers):
    """Získání konzistentních statistik napříč celou aplikací - pouze položky zobrazené na mapě"""
    if not events:
        return {
            'total_events': 0,
            'czech_events': 0,
            'high_critical_events': 0,
            'recent_events': 0,
            'total_suppliers': 0,
            'czech_suppliers': 0,
            'high_risk_suppliers': 0
        }
    
    # Počítání událostí v ČR (pouze ty, které se zobrazí na mapě)
    czech_events = 0
    high_critical_events = 0
    recent_events = 0
    
    for event in events:
        try:
            lat = float(event.get("latitude", 0))
            lon = float(event.get("longitude", 0))
            
            # Kontrola, že souřadnice jsou v rozumném rozsahu a v ČR
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                continue
                
            if is_in_czech_republic(lat, lon):
                czech_events += 1
                
                if event.get("severity") in ["high", "critical"]:
                    high_critical_events += 1
                
                # Události z posledních 7 dní
                created_at = event.get("created_at", "")
                if created_at:
                    try:
                        event_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if (datetime.now() - event_date).days <= 7:
                            recent_events += 1
                    except:
                        pass
        except:
            pass
    
    # Počítání dodavatelů v ČR (pouze ti, kteří se zobrazí na mapě)
    czech_suppliers = 0
    high_risk_suppliers = 0
    
    if suppliers:
        for supplier in suppliers:
            try:
                lat = float(supplier.get("latitude", 0))
                lon = float(supplier.get("longitude", 0))
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu a v ČR
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                    
                if is_in_czech_republic(lat, lon):
                    czech_suppliers += 1
                    
                    if supplier.get("risk_level") == "high":
                        high_risk_suppliers += 1
            except:
                pass
    
    return {
        'total_events': czech_events,  # Pouze události zobrazené na mapě
        'czech_events': czech_events,
        'high_critical_events': high_critical_events,
        'recent_events': recent_events,
        'total_suppliers': czech_suppliers,  # Pouze dodavatelé zobrazení na mapě
        'czech_suppliers': czech_suppliers,
        'high_risk_suppliers': high_risk_suppliers
    }

# Funkce pro získání barvy podle zdroje dat
def get_source_color(source):
    """Získání barvy podle zdroje dat"""
    if 'scraped' in source.lower():
        return 'data-scraped'
    elif 'fallback' in source.lower():
        return 'data-fallback'
    else:
        return 'data-source'

# Funkce pro formátování data
def format_date(date_str):
    """Formátování data do čitelné podoby"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return date_str

# Funkce pro komunikaci s backendem
def api_request(endpoint, method='GET', data=None):
    """Základní funkce pro komunikaci s API"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, timeout=30)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return None

# Funkce pro získání rizikových událostí
def get_risk_events():
    """Získání všech rizikových událostí z API"""
    try:
        print(f"Pokouším se o připojení k: {BACKEND_URL}/api/risks")
        response = requests.get(f"{BACKEND_URL}/api/risks", timeout=30)
        print(f"Status odpovědi: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Získáno {len(data)} rizikových událostí")
            return data
        else:
            st.error(f"Chyba při načítání rizikových událostí (Status: {response.status_code})")
            return []
    except requests.exceptions.ConnectionError:
        st.error(f"Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží.")
        return []
    except Exception as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return []

# Funkce pro získání dodavatelů
def get_suppliers():
    """Získání všech dodavatelů z API"""
    try:
        print(f"Pokouším se o připojení k: {BACKEND_URL}/api/suppliers")
        response = requests.get(f"{BACKEND_URL}/api/suppliers", timeout=30)
        print(f"Status odpovědi: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Získáno {len(data)} dodavatelů")
            return data
        else:
            st.error(f"Chyba při načítání dodavatelů (Status: {response.status_code})")
            return []
    except requests.exceptions.ConnectionError:
        st.error(f"Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží.")
        return []
    except Exception as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return []

# Funkce pro získání analýzy rizik
def get_risk_analysis():
    """Získání analýzy rizik z API"""
    try:
        print(f"Pokouším se o připojení k: {BACKEND_URL}/api/analysis/risk-map")
        response = requests.get(f"{BACKEND_URL}/api/analysis/risk-map", timeout=30)
        print(f"Status odpovědi: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Získána analýza rizik")
            return data
        else:
            st.error(f"Chyba při načítání analýzy rizik (Status: {response.status_code})")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží.")
        return None
    except Exception as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return None

# Funkce pro spuštění scraping
def run_scraping():
    """Spuštění scraping procesu"""
    try:
        print(f"Spouštím scraping na: {BACKEND_URL}/api/scrape/run-all")
        response = requests.get(f"{BACKEND_URL}/api/scrape/run-all", timeout=60)
        print(f"Status odpovědi: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Scraping dokončen")
            return data
        else:
            st.error(f"Chyba při spouštění scraping (Status: {response.status_code})")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží.")
        return None
    except Exception as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return None

def get_advanced_analysis():
    """Získání dat pro pokročilou analýzu"""
    try:
        # River flood simulation
        response = requests.get(f"{BACKEND_URL}/api/analysis/river-flood-simulation")
        if response.status_code == 200:
            flood_data = response.json()
        else:
            flood_data = {"error": "Nepodařilo se načíst data o záplavách"}
        
        # Supply chain impact
        response = requests.get(f"{BACKEND_URL}/api/analysis/supply-chain-impact")
        if response.status_code == 200:
            supply_chain_data = response.json()
        else:
            supply_chain_data = {"error": "Nepodařilo se načíst data o dodavatelském řetězci"}
        return flood_data, supply_chain_data
    except Exception as e:
        return {"error": f"Chyba: {str(e)}"}, {"error": f"Chyba: {str(e)}"}

# Helper funkce pro vytvoření mapy s rizikovými událostmi
def create_risk_map(events, suppliers, center_lat=DEFAULT_LAT, center_lon=DEFAULT_LON, zoom_start=8, flood_data=None, geo_data=None):
    """Vytvoření mapy s rizikovými událostmi, dodavateli a pokročilou analýzou - pouze v ČR"""
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=zoom_start,  # Dynamický zoom podle dat
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Přidání pouze OpenStreetMap a satelitní mapy
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap',
        overlay=False
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        name='Satelitní mapa',
        overlay=False
    ).add_to(m)
    
    # Přidání ovladače vrstev s lepším umístěním
    folium.LayerControl(position='topright').add_to(m)
    
    # Omezení mapy na ČR pro lepší navigaci
    folium.LatLngPopup().add_to(m)
    
    # Barvy pro různé typy událostí
    event_colors = {
        'flood': 'blue',
        'protest': 'red',
        'supply_chain': 'orange',
        'geopolitical': 'purple',
        'manual': 'gray',
        'chmi': 'cyan',
        'rss': 'magenta'
    }
    
    # Ikony pro různé závažnosti
    severity_icons = {
        'critical': 'exclamation-triangle',
        'high': 'exclamation-circle',
        'medium': 'info-circle',
        'low': 'check-circle'
    }
    
    # Vysvětlení závažnosti rizik
    severity_explanations = {
        'critical': '🚨 KRITICKÉ: Okamžitý dopad na výrobu, nutná okamžitá akce',
        'high': '⚠️ VYSOKÉ: Významný dopad na dodavatelský řetězec, sledování nutné',
        'medium': '⚡ STŘEDNÍ: Možný dopad na výrobu, preventivní opatření doporučena',
        'low': '✅ NÍZKÉ: Minimální riziko, rutinní monitoring'
    }
    
    # Vysvětlení typů událostí
    event_type_explanations = {
        'flood': '🌊 ZÁPLAVY: Poškození infrastruktury, přerušení dodávek',
        'protest': '🚨 PROTESTY: Blokády, přerušení dopravy, sociální nepokoje',
        'supply_chain': '🏭 DODAVATELSKÝ ŘETĚZEC: Problémy s dodavateli, nedostatek materiálů',
        'geopolitical': '🌍 GEOPOLITICKÉ: Sankce, embarga, mezinárodní napětí',
        'manual': '✋ RUČNĚ PŘIDANÉ: Manuálně zadané rizikové události',
        'chmi': '🌤️ CHMI: Meteorologická data, extrémní počasí',
        'rss': '📰 RSS: Zprávy z médií, aktuální události'
    }
    
    # Počítadla pro statistiky
    czech_events = 0
    total_events = 0
    
    # Přidání rizikových událostí
    if events:
        for event in events:
            try:
                lat = float(event.get("latitude", 0))
                lon = float(event.get("longitude", 0))
                total_events += 1
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu a v ČR
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                
                # Kontrola, zda je událost v ČR
                if not is_in_czech_republic(lat, lon):
                    continue
                
                czech_events += 1
                
                # Získání dat události
                title = event.get("title", "Neznámá událost")
                description = event.get("description", "")
                event_type = event.get("event_type", "unknown")
                severity = event.get("severity", "medium")
                source = event.get("source", "unknown")
                created_at = event.get("created_at", "")
                
                # Barva podle typu události
                color = event_colors.get(event_type, 'gray')
                
                # Ikona podle závažnosti
                icon_name = severity_icons.get(severity, 'info-circle')
                
                # Formátování data
                formatted_date = format_date(created_at)
                
                # Zdroj dat s barvou
                source_class = get_source_color(source)
                
                # Vysvětlení rizika
                severity_explanation = severity_explanations.get(severity, 'Neznámá závažnost')
                event_type_explanation = event_type_explanations.get(event_type, 'Neznámý typ události')
                
                # Popup obsah s jasným vysvětlením rizika
                popup_content = f"""
                <div style='width: 380px; padding: 15px; font-family: Arial, sans-serif;'>
                    <h3 style='color: {color}; margin-top: 0; border-bottom: 2px solid {color}; padding-bottom: 5px;'>
                        ⚠️ RIZIKOVÁ UDÁLOST: {title}
                    </h3>
                    
                    <div style='background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid #ffc107;'>
                        <strong>📊 HODNOCENÍ RIZIKA:</strong><br>
                        {severity_explanation}
                    </div>
                    
                    <div style='background-color: #d1ecf1; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid #17a2b8;'>
                        <strong>🏷️ TYP UDÁLOSTI:</strong><br>
                        {event_type_explanation}
                    </div>
                    
                    <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid {color};'>
                        <strong>📝 POPIS:</strong><br>
                        {description if description else "Žádný detailní popis není k dispozici"}
                    </div>
                    
                    <div style='margin-top: 15px; background-color: #e9ecef; padding: 10px; border-radius: 5px;'>
                        <p style='margin: 5px 0;'>
                            <strong style='color: #0D47A1;'>📅 Datum detekce:</strong> {formatted_date}
                        </p>
                        <p style='margin: 5px 0;'>
                            <strong style='color: #0D47A1;'>🔗 Zdroj dat:</strong> 
                            <span class='{source_class}'>{source}</span>
                        </p>
                        <p style='margin: 5px 0;'>
                            <strong style='color: #0D47A1;'>📍 Lokace:</strong> {lat:.4f}, {lon:.4f}
                        </p>
                    </div>
                    
                    <div style='background-color: #d4edda; padding: 8px; border-radius: 5px; margin-top: 10px; 
                               border-left: 4px solid #28a745;'>
                        <strong>💡 DOPAD NA DODAVATELSKÝ ŘETĚZEC:</strong><br>
                        Tato událost může ovlivnit dodavatelský řetězec v této oblasti.
                    </div>
                </div>
                """
                
                # Přidání markeru pro rizikové události (červené ikony)
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=380),
                    tooltip=f"⚠️ RIZIKO: {title} ({severity})",
                    icon=folium.Icon(icon=icon_name, prefix="fa", color="red")
                ).add_to(m)
                
            except Exception as e:
                print(f"Chyba při zpracování události: {str(e)}")
    
    # Přidání dodavatelů
    czech_suppliers = 0
    total_suppliers = 0
    
    if suppliers:
        for supplier in suppliers:
            try:
                lat = float(supplier.get("latitude", 0))
                lon = float(supplier.get("longitude", 0))
                total_suppliers += 1
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu a v ČR
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                
                # Kontrola, zda je dodavatel v ČR
                if not is_in_czech_republic(lat, lon):
                    continue
                
                czech_suppliers += 1
                
                # Získání dat dodavatele
                name = supplier.get("name", "Neznámý dodavatel")
                category = supplier.get("category", "unknown")
                risk_level = supplier.get("risk_level", "medium")
                created_at = supplier.get("created_at", "")
                
                # Barva podle úrovně rizika
                risk_colors = {
                    'high': 'red',
                    'medium': 'orange',
                    'low': 'green'
                }
                color = risk_colors.get(risk_level, 'gray')
                
                # Vysvětlení rizika dodavatele
                supplier_risk_explanations = {
                    'high': '🚨 VYSOKÉ RIZIKO: Kritický dodavatel, vysoká pravděpodobnost problémů',
                    'medium': '⚠️ STŘEDNÍ RIZIKO: Důležitý dodavatel, sledování nutné',
                    'low': '✅ NÍZKÉ RIZIKO: Stabilní dodavatel, minimální riziko'
                }
                
                # Vysvětlení kategorií dodavatelů
                category_explanations = {
                    'electronics': '🔌 ELEKTRONIKA: Čipy, senzory, řídicí systémy',
                    'steel': '🏗️ OCEL: Karoserie, konstrukční prvky',
                    'plastics': '🔲 PLASTY: Interiérové prvky, izolace',
                    'rubber': '🛞 GUMÁRENSKÉ: Pneumatiky, těsnění',
                    'glass': '🪟 SKLO: Čelní skla, zrcátka',
                    'textiles': '🧵 TEXTIL: Čalounění, izolace',
                    'chemicals': '🧪 CHEMICKÉ: Barvy, lepidla, maziva'
                }
                
                # Formátování data
                formatted_date = format_date(created_at)
                
                # Vysvětlení rizika
                risk_explanation = supplier_risk_explanations.get(risk_level, 'Neznámá úroveň rizika')
                category_explanation = category_explanations.get(category, 'Neznámá kategorie')
                
                # Popup obsah pro dodavatele s jasným vysvětlením
                popup_content = f"""
                <div style='width: 380px; padding: 15px; font-family: Arial, sans-serif;'>
                    <h3 style='color: {color}; margin-top: 0; border-bottom: 2px solid {color}; padding-bottom: 5px;'>
                        🏭 DODAVATEL: {name}
                    </h3>
                    
                    <div style='background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid #ffc107;'>
                        <strong>📊 HODNOCENÍ RIZIKA:</strong><br>
                        {risk_explanation}
                    </div>
                    
                    <div style='background-color: #d1ecf1; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid #17a2b8;'>
                        <strong>🏷️ KATEGORIE:</strong><br>
                        {category_explanation}
                    </div>
                    
                    <div style='margin-top: 15px; background-color: #e9ecef; padding: 10px; border-radius: 5px;'>
                        <p style='margin: 5px 0;'>
                            <strong style='color: #0D47A1;'>📅 Datum registrace:</strong> {formatted_date}
                        </p>
                        <p style='margin: 5px 0;'>
                            <strong style='color: #0D47A1;'>📍 Lokace:</strong> {lat:.4f}, {lon:.4f}
                        </p>
                    </div>
                    
                    <div style='background-color: #d4edda; padding: 8px; border-radius: 5px; margin-top: 10px; 
                               border-left: 4px solid #28a745;'>
                        <strong>💡 VÝZNAM PRO DODAVATELSKÝ ŘETĚZEC:</strong><br>
                        Tento dodavatel je součástí dodavatelského řetězce a jeho stabilita je klíčová pro výrobu.
                    </div>
                    
                    <div style='background-color: #f8d7da; padding: 8px; border-radius: 5px; margin-top: 10px; 
                               border-left: 4px solid #dc3545;'>
                        <strong>⚠️ MOŽNÉ DOPADY:</strong><br>
                        Problémy s tímto dodavatelem mohou vést k přerušení výroby nebo zvýšení nákladů.
                    </div>
                </div>
                """
                
                # Přidání markeru dodavatele (modré ikony pro odlišení od rizik)
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=380),
                    tooltip=f"🏭 DODAVATEL: {name} ({risk_level})",
                    icon=folium.Icon(icon="industry", prefix="fa", color="blue")
                ).add_to(m)
                
            except Exception as e:
                print(f"Chyba při zpracování dodavatele: {str(e)}")
    
    # Uložení statistik do session state
    st.session_state.czech_events = czech_events
    st.session_state.total_events = total_events
    st.session_state.czech_suppliers = czech_suppliers
    st.session_state.total_suppliers = total_suppliers
    
    # Přidání pokročilé analýzy na mapu
    if flood_data and "flood_analysis" in flood_data:
        for analysis in flood_data['flood_analysis']:
            try:
                supplier = analysis['supplier']
                flood_risk = analysis['flood_risk']
                
                lat = float(supplier.get("latitude", 0))
                lon = float(supplier.get("longitude", 0))
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu a v ČR
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                
                if not is_in_czech_republic(lat, lon):
                    continue
                
                # Popup pro simulaci záplav
                flood_popup_content = f"""
                <div style='width: 380px; padding: 15px; font-family: Arial, sans-serif;'>
                    <h3 style='color: #D32F2F; margin-top: 0; border-bottom: 2px solid #D32F2F; padding-bottom: 5px;'>
                        🌊 SIMULACE ZÁPLAV: {supplier['name']}
                    </h3>
                    
                    <div style='background-color: #ffebee; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid #D32F2F;'>
                        <strong>📊 VÝSLEDKY SIMULACE:</strong><br>
                        <strong>Pravděpodobnost záplav:</strong> {flood_risk['probability']:.1%}<br>
                        <strong>Úroveň dopadu:</strong> {flood_risk['impact_level'].upper()}<br>
                        <strong>Vzdálenost od řeky:</strong> {flood_risk['river_distance_km']:.1f} km<br>
                        <strong>Nadmořská výška:</strong> {flood_risk['elevation_m']:.0f} m
                    </div>
                    
                    <div style='background-color: #fff3e0; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid #ff9800;'>
                        <strong>⚠️ MITIGACE:</strong><br>
                        {'Potřebná mitigace - doporučeno přemístění' if flood_risk['mitigation_needed'] else 'Bezpečná oblast - žádná akce nutná'}
                    </div>
                    
                    <div style='background-color: #e8f5e8; padding: 8px; border-radius: 5px; margin-top: 10px; 
                               border-left: 4px solid #4caf50;'>
                        <strong>💡 DOPORUČENÍ:</strong><br>
                        {'• Přesunout výrobu do bezpečnější lokace<br>• Instalovat protipovodňová opatření<br>• Vytvořit záložní dodavatelský řetězec' if flood_risk['mitigation_needed'] else '• Pokračovat v rutinním monitoringu<br>• Pravidelně kontrolovat stav lokace'}
                    </div>
                </div>
                """
                
                # Přidání markeru pro simulaci záplav (červené ikony s vodou)
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(flood_popup_content, max_width=380),
                    tooltip=f"🌊 ZÁPLAVY: {supplier['name']} ({flood_risk['impact_level']})",
                    icon=folium.Icon(icon="tint", prefix="fa", color="red")
                ).add_to(m)
                
                # Přidání kruhu pro rizikovou zónu (simulace)
                risk_radius = 5 if flood_risk['mitigation_needed'] else 2  # km
                folium.Circle(
                    radius=risk_radius * 1000,  # Převod na metry
                    location=[lat, lon],
                    popup=f'Riziková zóna záplav: {risk_radius} km',
                    color='red' if flood_risk['mitigation_needed'] else 'green',
                    fill=True,
                    fillOpacity=0.2,
                    weight=2
                ).add_to(m)
                
            except Exception as e:
                print(f"Chyba při zpracování simulace záplav: {str(e)}")
    
    # Přidání geografické analýzy na mapu
    if geo_data and "combined_risk_assessment" in geo_data:
        try:
            # Získání dat z geografické analýzy
            risk_assessment = geo_data['combined_risk_assessment']
            river_analysis = geo_data['river_analysis']
            elevation_analysis = geo_data['elevation_analysis']
            
            # Použijeme střední souřadnice ČR pro zobrazení analýzy
            analysis_lat = 50.0755
            analysis_lon = 14.4378
            
            # Popup pro geografickou analýzu
            geo_popup_content = f"""
            <div style='width: 380px; padding: 15px; font-family: Arial, sans-serif;'>
                <h3 style='color: #1976D2; margin-top: 0; border-bottom: 2px solid #1976D2; padding-bottom: 5px;'>
                    🗺️ GEOGRAFICKÁ ANALÝZA RIZIK
                </h3>
                
                <div style='background-color: #e3f2fd; padding: 10px; border-radius: 5px; margin: 10px 0; 
                           border-left: 4px solid #1976D2;'>
                    <strong>📊 CELKOVÉ HODNOCENÍ:</strong><br>
                    <strong>Celkové riziko:</strong> {risk_assessment['overall_risk_level'].upper()}<br>
                    <strong>Risk score:</strong> {risk_assessment['risk_score']}/100
                </div>
                
                <div style='background-color: #fff3e0; padding: 10px; border-radius: 5px; margin: 10px 0; 
                           border-left: 4px solid #ff9800;'>
                    <strong>🌊 ANALÝZA ŘEK:</strong><br>
                    <strong>Vzdálenost od řeky:</strong> {river_analysis['nearest_river_distance_km']:.1f} km<br>
                    <strong>Záplavová zóna:</strong> {'Ano' if river_analysis['flood_risk_zone'] else 'Ne'}
                </div>
                
                <div style='background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 10px 0; 
                           border-left: 4px solid #4caf50;'>
                    <strong>🏔️ ANALÝZA TERÉNU:</strong><br>
                    <strong>Nadmořská výška:</strong> {elevation_analysis['elevation_m']:.0f} m<br>
                    <strong>Typ terénu:</strong> {elevation_analysis['terrain_type']}
                </div>
                
                <div style='background-color: #f3e5f5; padding: 8px; border-radius: 5px; margin-top: 10px; 
                           border-left: 4px solid #9c27b0;'>
                    <strong>💡 DOPORUČENÍ:</strong><br>
                    {chr(10).join([f"• {rec}" for rec in risk_assessment['recommendations'][:3]])}
                </div>
            </div>
            """
            
            # Barva podle úrovně rizika
            risk_color = {
                'high': 'red',
                'medium': 'orange', 
                'low': 'green'
            }.get(risk_assessment['overall_risk_level'].lower(), 'gray')
            
            # Přidání markeru pro geografickou analýzu
            folium.Marker(
                [analysis_lat, analysis_lon],
                popup=folium.Popup(geo_popup_content, max_width=380),
                tooltip=f"🗺️ GEOGRAFICKÁ ANALÝZA: {risk_assessment['overall_risk_level'].upper()}",
                icon=folium.Icon(icon="map-marker", prefix="fa", color=risk_color)
            ).add_to(m)
            
        except Exception as e:
            print(f"Chyba při zpracování geografické analýzy: {str(e)}")
    
    return m

# Funkce pro filtrování událostí
def filter_events(events, event_type=None, severity=None, source=None, date_from=None, date_to=None):
    """Filtrování událostí podle zadaných kritérií"""
    filtered_events = events.copy()
    
    # Překladové slovníky pro zpětný překlad
    event_type_translations = {
        'Záplavy': 'flood',
        'Protesty': 'protest', 
        'Dodavatelský řetězec': 'supply_chain',
        'Geopolitické': 'geopolitical',
        'Ručně přidané': 'manual',
        'CHMI (počasí)': 'chmi',
        'RSS (zprávy)': 'rss',
        'Neznámé': 'unknown'
    }
    
    severity_translations = {
        'Kritické': 'critical',
        'Vysoké': 'high',
        'Střední': 'medium', 
        'Nízké': 'low',
        'Neznámé': 'unknown'
    }
    
    source_translations = {
        'CHMI API': 'chmi_api',
        'RSS feeds': 'rss',
        'Ručně přidané': 'manual',
        'Neznámé': 'unknown'
    }
    
    if event_type and event_type != "Všechny":
        # Překlad z češtiny do angličtiny
        event_type_en = event_type_translations.get(event_type, event_type)
        filtered_events = [e for e in filtered_events if e.get("event_type") == event_type_en]
    
    if severity and severity != "Všechny":
        # Překlad z češtiny do angličtiny
        severity_en = severity_translations.get(severity, severity)
        filtered_events = [e for e in filtered_events if e.get("severity") == severity_en]
    
    if source and source != "Všechny":
        # Překlad z češtiny do angličtiny
        source_en = source_translations.get(source, source)
        filtered_events = [e for e in filtered_events if e.get("source") == source_en]
    
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            filtered_events = [e for e in filtered_events 
                             if datetime.fromisoformat(e.get("created_at", "").replace('Z', '+00:00')) >= date_from_dt]
        except:
            pass
    
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            filtered_events = [e for e in filtered_events 
                             if datetime.fromisoformat(e.get("created_at", "").replace('Z', '+00:00')) <= date_to_dt]
        except:
            pass
    
    return filtered_events

# Sidebar - informace o aplikaci v postranním panelu
with st.sidebar:
    # Stylizované logo pomocí emoji a textu
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <div style='font-size: 50px;'>⚠️ 🏭 📊</div>
        <div style='background: linear-gradient(90deg, #D32F2F, #B71C1C); 
                   -webkit-background-clip: text; 
                   -webkit-text-fill-color: transparent; 
                   font-size: 28px; 
                   font-weight: bold;
                   margin-top: 10px;'>
            Risk Analyst Dashboard
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Účel aplikace přesunut do sekce "O aplikaci"
    
    # Vysvětlení hodnocení rizik
    st.markdown("""
    <div style='background-color: #FFF8E1; padding: 15px; border-radius: 10px; border-left: 4px solid #FFB300; margin-top: 15px;'>
        <h4 style='color: #F57F17; margin-top: 0;'>📊 Hodnocení rizik</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>🚨 KRITICKÉ:</strong> Okamžitý dopad na výrobu, nutná akce<br>
            <strong>⚠️ VYSOKÉ:</strong> Významný dopad na dodavatelský řetězec<br>
            <strong>⚡ STŘEDNÍ:</strong> Možný dopad, preventivní opatření doporučena<br>
            <strong>✅ NÍZKÉ:</strong> Minimální riziko, rutinní monitoring
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Zdroje dat přesunuty do sekce "O aplikaci"
    
    # Kontrola připojení k API
    st.subheader("🔌 Stav připojení")
    try:
        response = requests.get(f"{BACKEND_URL}", timeout=5)
        if response.status_code == 200:
            st.success("✅ Backend API je dostupné")
        else:
            st.warning(f"⚠️ Backend API odpovídá s kódem: {response.status_code}")
    except:
        st.error("❌ Backend API není dostupné")
        st.info("💡 Zkontrolujte připojení k internetu nebo zkuste později.")
    
    # Oddělovací čára
    st.markdown("---")
    
    # Filtry
    st.markdown("""
    <div style='background-color: #F5F5F5; padding: 15px; border-radius: 10px; margin: 15px 0;'>
        <h4 style='color: #333; margin-top: 0;'>🔍 Filtry</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>📊 Typ události:</strong> Kategorie rizikových událostí<br>
            <strong>⚠️ Závažnost:</strong> Úroveň rizika od nízké po kritické<br>
            <strong>🔗 Zdroj dat:</strong> Původ dat (CHMI, RSS, ruční)<br>
            <strong>📅 Časové období:</strong> Filtrování podle data události
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Získání unikátních hodnot pro filtry
    events = get_risk_events()
    suppliers = get_suppliers()
    
    if events:
        # Přeložení typů událostí do češtiny
        event_type_translations = {
            'flood': 'Záplavy',
            'protest': 'Protesty',
            'supply_chain': 'Dodavatelský řetězec',
            'geopolitical': 'Geopolitické',
            'manual': 'Ručně přidané',
            'chmi': 'CHMI (počasí)',
            'rss': 'RSS (zprávy)',
            'unknown': 'Neznámé'
        }
        
        # Přeložení závažností do češtiny
        severity_translations = {
            'critical': 'Kritické',
            'high': 'Vysoké',
            'medium': 'Střední',
            'low': 'Nízké',
            'unknown': 'Neznámé'
        }
        
        # Přeložení zdrojů do češtiny
        source_translations = {
            'chmi_scraped': 'CHMI API',
            'rss_scraped': 'RSS feeds',
            'chmi_api': 'CHMI API',
            'rss': 'RSS feeds',
            'manual': 'Ručně přidané',
            'unknown': 'Neznámé'
        }
        
        # Získání unikátních hodnot
        event_types = ["Všechny"] + [event_type_translations.get(et, et) for et in set([e.get("event_type", "unknown") for e in events])]
        severities = ["Všechny"] + [severity_translations.get(sev, sev) for sev in set([e.get("severity", "medium") for e in events])]
        sources = ["Všechny"] + [source_translations.get(src, src) for src in set([e.get("source", "unknown") for e in events])]
        
        selected_event_type = st.selectbox("📊 Typ události:", event_types, help="Vyberte typ rizikové události")
        selected_severity = st.selectbox("⚠️ Závažnost:", severities, help="Vyberte úroveň závažnosti")
        selected_source = st.selectbox("🔗 Zdroj dat:", sources, help="Vyberte zdroj dat")
        
        # Filtry bez duplicitního vysvětlení
        
        # Datové filtry
        st.markdown("""
        <div style='background-color: #E8F5E8; padding: 10px; border-radius: 8px; margin: 10px 0;'>
            <h5 style='color: #2E7D32; margin-top: 0;'>📅 Časové období</h5>
            <p style='margin: 3px 0; font-size: 0.8em;'>
                Filtrujte události podle data jejich vzniku
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("Od:", value=datetime.now().date() - timedelta(days=7), help="Začátek časového období")
        with col2:
            date_to = st.date_input("Do:", value=datetime.now().date(), help="Konec časového období")
    else:
        st.warning("⚠️ Nelze načíst data pro filtry")

# Hlavní obsah aplikace
st.markdown("<h1 class='main-header'>⚠️ Risk Analyst Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Komplexní analýza rizik v dodavatelském řetězci</p>", unsafe_allow_html=True)

# Přehledný dashboard s klíčovými metrikami
if events and suppliers:
    # Získání konzistentních statistik
    stats = get_consistent_statistics(events, suppliers)
    
    # Klíčové metriky na vrcholu
    st.markdown("""
    <div style='background-color: #F8F9FA; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #495057; margin-top: 0;'>📊 Přehled rizik</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Rychlé metriky
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🚨 Kritická rizika", stats['high_critical_events'], help="Události s kritickou nebo vysokou závažností")
    with col2:
        st.metric("🏭 Rizikoví dodavatelé", stats['high_risk_suppliers'], help="Dodavatelé s vysokým rizikem")
    with col3:
        st.metric("📅 Posledních 7 dní", stats['recent_events'], help="Události z posledního týdne")
    with col4:
        st.metric("🇨🇿 Události v ČR", stats['czech_events'], help="Události na území České republiky")

# Záložky pro různé části aplikace
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Mapa rizik", 
    "🔍 Scraping", 
    "🏭 Dodavatelé", 
    "🔬 Pokročilá analýza",
    "ℹ️ O aplikaci"
])

with tab1:
    # Mapa rizik
    st.markdown("""
    <div style='background-color: #E3F2FD; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #1976D2; margin-top: 0;'>🗺️ Interaktivní mapa rizik</h3>
        <p style='margin: 5px 0;'>
            <strong>⚠️ Červené body:</strong> Rizikové události (záplavy, protesty, dodavatelské problémy)<br>
            <strong>🏭 Modré body:</strong> Dodavatelé s hodnocením rizika<br>
            <strong>🎯 Cíl:</strong> Identifikace rizikových oblastí a jejich dopadů na dodavatelský řetězec
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vysvětlení mapy a rizik
    st.markdown("""
    <div style='background-color: #FFF3E0; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #F57C00; margin-top: 0;'>💡 Jak číst mapu a hodnotit rizika</h4>
        <div style='display: flex; justify-content: space-between; margin-top: 10px;'>
            <div style='flex: 1; margin-right: 15px;'>
                <strong>�� KRITICKÉ riziko:</strong><br>
                • Okamžitý dopad na výrobu VW Group<br>
                • Nutná okamžitá akce<br>
                • Možné přerušení dodávek
            </div>
            <div style='flex: 1; margin-right: 15px;'>
                <strong>⚠️ VYSOKÉ riziko:</strong><br>
                • Významný dopad na dodavatelský řetězec<br>
                • Sledování nutné<br>
                • Možné zvýšení nákladů
            </div>
            <div style='flex: 1;'>
                <strong>⚡ STŘEDNÍ/NÍZKÉ riziko:</strong><br>
                • Možný dopad na výrobu<br>
                • Preventivní opatření doporučena<br>
                • Rutinní monitoring
            </div>
        </div>
        <p style='margin-top: 10px; font-size: 0.9em; color: #666;'>
            <strong>💡 Tip:</strong> Klikněte na body v mapě pro detailní informace o riziku a jeho dopadech na VW Group.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Filtrování událostí
    if events:
        filtered_events = filter_events(
            events, 
            selected_event_type if 'selected_event_type' in locals() else None,
            selected_severity if 'selected_severity' in locals() else None,
            selected_source if 'selected_source' in locals() else None,
            date_from if 'date_from' in locals() else None,
            date_to if 'date_to' in locals() else None
        )
        
        # Použití konzistentních statistik
        stats = get_consistent_statistics(filtered_events, suppliers)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Zobrazené události", len(filtered_events))
        with col2:
            st.metric("🇨🇿 Události v ČR", stats['czech_events'])
        with col3:
            st.metric("🌍 Celkem událostí", stats['total_events'])
        
        # Vytvoření a zobrazení mapy s klíčem pro prevenci reloadingu
        try:
            # Automatické přizpůsobení mapy podle dat
            if filtered_events or suppliers:
                # Najít střed dat pro lepší zobrazení
                all_lats = []
                all_lons = []
                
                for event in filtered_events:
                    try:
                        lat = float(event.get("latitude", 0))
                        lon = float(event.get("longitude", 0))
                        if is_in_czech_republic(lat, lon):
                            all_lats.append(lat)
                            all_lons.append(lon)
                    except:
                        pass
                
                for supplier in suppliers:
                    try:
                        lat = float(supplier.get("latitude", 0))
                        lon = float(supplier.get("longitude", 0))
                        if is_in_czech_republic(lat, lon):
                            all_lats.append(lat)
                            all_lons.append(lon)
                    except:
                        pass
                
                # Pokud máme data v ČR, použít jejich střed
                if all_lats and all_lons:
                    center_lat = sum(all_lats) / len(all_lats)
                    center_lon = sum(all_lons) / len(all_lons)
                    zoom_start = 9  # Větší zoom pro detailnější zobrazení
                else:
                    center_lat, center_lon = DEFAULT_LAT, DEFAULT_LON
                    zoom_start = 8
            else:
                center_lat, center_lon = DEFAULT_LAT, DEFAULT_LON
                zoom_start = 8
            
            # Získání dat pro pokročilou analýzu
            flood_data, geo_data = get_advanced_analysis()
            
            m = create_risk_map(filtered_events, suppliers, center_lat, center_lon, zoom_start, flood_data, geo_data)
            map_data = st_folium(
                m, 
                width=None,  # Automatická šířka
                height=700,  # Větší výška
                key=f"map_{st.session_state.map_key}",
                returned_objects=["last_object_clicked"]
            )
            
            # Informace o zobrazených datech
            if len(filtered_events) == 0 and len(suppliers) == 0:
                st.info("ℹ️ Žádná data k zobrazení - zkuste upravit filtry nebo spustit scraping pro získání nových dat.")
            elif len(filtered_events) == 0:
                st.info("ℹ️ Žádné rizikové události k zobrazení - zobrazují se pouze dodavatelé.")
            elif len(suppliers) == 0:
                st.info("ℹ️ Žádní dodavatelé k zobrazení - zobrazují se pouze rizikové události.")
            # Odstraněno zobrazení počtu událostí a dodavatelů
                
        except Exception as e:
            st.error(f"❌ Chyba při vytváření mapy: {str(e)}")
            st.info("💡 Zkuste obnovit stránku nebo kontaktujte správce aplikace.")
    else:
        st.error("❌ Nelze načíst rizikové události")
        st.info("💡 Zkuste spustit scraping pro získání dat nebo zkontrolujte připojení k backendu.")

with tab2:
    # Scraping
    st.markdown("""
    <div style='background-color: #E3F2FD; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #1976D2; margin-top: 0;'>🔍 Aktualizace dat</h3>
        <p style='margin: 5px 0;'>
            <strong>🌤️ CHMI API:</strong> Meteorologická data a výstrahy<br>
            <strong>📰 RSS feeds:</strong> Zprávy z českých médií<br>
            <strong>💡 Cíl:</strong> Získání aktuálních rizikových událostí pro analýzu
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vysvětlení scraping procesu
    st.info("💡 **Jak funguje scraping**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌤️ CHMI (Český hydrometeorologický ústav):**")
        st.markdown("• Získává data o extrémním počasí a záplavách")
        st.markdown("• Analýza meteorologických výstrah")
        st.markdown("• Lokalizace rizikových oblastí v ČR")
    
    with col2:
        st.markdown("**📰 RSS feeds (česká média):**")
        st.markdown("• Monitoruje zprávy o protestech a nepokojích")
        st.markdown("• Sleduje dodavatelské problémy a přerušení")
        st.markdown("• Analýza geopolitických událostí")
    
    st.success("**🎯 Výsledek:** Automatické vytvoření rizikových událostí v databázi")
    
    # Tlačítko pro spuštění scraping
    st.subheader("🔄 Spuštění scraping")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🚀 Spustit scraping", type="primary", help="Spustí web scraping pro získání aktuálních dat"):
            with st.spinner("Spouštím scraping..."):
                result = run_scraping()
                if result and isinstance(result, dict):
                    # Uživatelsky přívětivé zobrazení výsledků
                    st.success("✅ Scraping dokončen!")
                    
                    # Zobrazení přehledných výsledků
                    if 'results' in result:
                        results = result['results']
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if 'chmi' in results:
                                chmi_data = results['chmi']
                                if chmi_data.get('status') == 'success':
                                    st.info(f"🌤️ CHMI (počasí): {chmi_data.get('scraped_count', 0)} nových událostí")
                                else:
                                    st.warning("🌤️ CHMI: Žádná nová data")
                            
                            if 'rss' in results:
                                rss_data = results['rss']
                                if rss_data.get('status') == 'success':
                                    st.info(f"📰 RSS (zprávy): {rss_data.get('scraped_count', 0)} nových událostí")
                                else:
                                    st.warning("📰 RSS: Žádná nová data")
                        
                        with col2:
                            total_saved = result.get('total_events_saved', 0)
                            if total_saved > 0:
                                st.success(f"💾 Celkem uloženo: {total_saved} nových událostí")
                            else:
                                st.info("ℹ️ Žádné nové události k uložení")
                        
                        # Přidání tlačítka pro obnovení dat
                        if st.button("🔄 Obnovit zobrazení", help="Načte nejnovější data z databáze"):
                            st.rerun()
                    else:
                        st.info("ℹ️ Scraping dokončen, ale žádná nová data nebyla nalezena")
                else:
                    st.error("❌ Chyba při scraping - zkuste to prosím znovu")
    
    with col2:
        st.info("💡 Tip: Spusťte scraping pro získání nejnovějších dat o rizicích")
    
    # Statistiky nejnovějších událostí
    st.subheader("📊 Nejnovější události")
    events = get_risk_events()
    if events:
        # Použití konzistentních statistik
        stats = get_consistent_statistics(events, suppliers)
        
        # Převod na DataFrame pro analýzu
        df_events = pd.DataFrame(events)
        
        # Překladové slovníky pro lepší zobrazení
        event_type_translations = {
            'flood': 'Záplavy',
            'protest': 'Protesty',
            'supply_chain': 'Dodavatelský řetězec',
            'geopolitical': 'Geopolitické',
            'manual': 'Ručně přidané',
            'chmi': 'CHMI (počasí)',
            'rss': 'RSS (zprávy)',
            'unknown': 'Neznámé'
        }
        
        severity_translations = {
            'critical': 'Kritické',
            'high': 'Vysoké',
            'medium': 'Střední',
            'low': 'Nízké',
            'unknown': 'Neznámé'
        }
        
        # Přidání přeložených sloupců
        df_events['event_type_cz'] = df_events['event_type'].map(event_type_translations).fillna('Neznámé')
        df_events['severity_cz'] = df_events['severity'].map(severity_translations).fillna('Neznámé')
        df_events['created_at'] = pd.to_datetime(df_events['created_at'])
        
        # Nejnovější události s lepším formátováním
        if not df_events.empty:
            latest_events = df_events.sort_values('created_at', ascending=False).head(10)
            
            # Vylepšené zobrazení tabulky
            display_df = latest_events[['title', 'event_type_cz', 'severity_cz', 'source', 'created_at']].copy()
            display_df['created_at'] = display_df['created_at'].dt.strftime('%d.%m.%Y %H:%M')
            display_df.columns = ['Název', 'Typ', 'Závažnost', 'Zdroj', 'Datum']
            
            # Přidání barevného formátování
            def color_severity(val):
                if val == 'Kritické':
                    return 'background-color: #ffcdd2'
                elif val == 'Vysoké':
                    return 'background-color: #ffecb3'
                elif val == 'Střední':
                    return 'background-color: #c8e6c9'
                else:
                    return 'background-color: #e8f5e8'
            
            st.dataframe(display_df.style.applymap(color_severity, subset=['Závažnost']), 
                        use_container_width=True, height=400)
        else:
            st.info("ℹ️ Žádné události k zobrazení")
    else:
        st.error("❌ Nelze načíst rizikové události")
        st.info("💡 Zkuste spustit scraping pro získání dat nebo zkontrolujte připojení k backendu.")

with tab3:
    # Dodavatelé - vylepšené
    st.markdown("""
    <div style='background-color: #FFF3E0; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #F57C00; margin-top: 0;'>🏭 Dodavatelé - Risk Management</h3>
        <p style='margin: 5px 0;'>
            <strong>🎯 Účel:</strong> Sledování dodavatelů a jejich rizikových profilů<br>
            <strong>📊 Co znamenají sloupce:</strong><br>
            &nbsp;&nbsp;• <strong>Název:</strong> Jméno dodavatele<br>
            &nbsp;&nbsp;• <strong>Kategorie:</strong> Typ dodavatele (Elektronika, Ocel, Plasty...)<br>
            &nbsp;&nbsp;• <strong>Úroveň rizika:</strong> Jak kritické je riziko (Nízké/Střední/Vysoké)<br>
            &nbsp;&nbsp;• <strong>Datum:</strong> Kdy byl dodavatel přidán do systému<br>
            <strong>⚠️ Praktický význam:</strong> Identifikace nejkritičtějších dodavatelů
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if suppliers:
        # Použití konzistentních statistik
        stats = get_consistent_statistics(events, suppliers)
        
        # Filtrování dodavatelů - pouze ti, kteří se zobrazí na mapě
        filtered_suppliers = []
        for supplier in suppliers:
            try:
                lat = float(supplier.get("latitude", 0))
                lon = float(supplier.get("longitude", 0))
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu a v ČR
                if (-90 <= lat <= 90) and (-180 <= lon <= 180) and is_in_czech_republic(lat, lon):
                    filtered_suppliers.append(supplier)
            except:
                pass
        
        # Převod na DataFrame - pouze filtrovaní dodavatelé
        df_suppliers = pd.DataFrame(filtered_suppliers)
        
        # Překladové slovníky
        category_translations = {
            'electronics': 'Elektronika',
            'steel': 'Ocel',
            'plastics': 'Plasty',
            'rubber': 'Guma',
            'glass': 'Sklo',
            'textiles': 'Textil',
            'chemicals': 'Chemikálie',
            'logistics': 'Logistika',
            'unknown': 'Neznámé'
        }
        
        risk_translations = {
            'high': 'Vysoké',
            'medium': 'Střední',
            'low': 'Nízké',
            'unknown': 'Neznámé'
        }
        
        # Přidání přeložených sloupců
        if not df_suppliers.empty:
            df_suppliers['category_cz'] = df_suppliers['category'].map(category_translations).fillna('Neznámé')
            df_suppliers['risk_level_cz'] = df_suppliers['risk_level'].map(risk_translations).fillna('Neznámé')
            df_suppliers['created_at'] = pd.to_datetime(df_suppliers['created_at'])
        
        # Klíčové metriky dodavatelů
        st.subheader("🎯 Přehled dodavatelů")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🏭 Celkem dodavatelů", stats['total_suppliers'], help="Celkový počet dodavatelů")
        
        with col2:
            risk_percentage = (stats['high_risk_suppliers'] / stats['total_suppliers'] * 100) if stats['total_suppliers'] > 0 else 0
            st.metric("⚠️ Vysoké riziko", f"{stats['high_risk_suppliers']} ({risk_percentage:.1f}%)", 
                     delta=f"{risk_percentage:.1f}%", help="Dodavatelé s vysokým rizikem")
        
        with col3:
            st.metric("🇨🇿 Dodavatelé v ČR", stats['czech_suppliers'], help="Dodavatelé na území České republiky")
        
        # Seznam dodavatelů - vylepšená tabulka
        st.subheader("📋 Seznam dodavatelů")
        if not df_suppliers.empty:
            # Vylepšené zobrazení tabulky
            display_df = df_suppliers[['name', 'category_cz', 'risk_level_cz', 'created_at']].copy()
            display_df['created_at'] = display_df['created_at'].dt.strftime('%d.%m.%Y')
            display_df.columns = ['Název dodavatele', 'Kategorie', 'Úroveň rizika', 'Datum přidání']
            
            # Přidání barevného formátování
            def color_risk(val):
                if val == 'Vysoké':
                    return 'background-color: #ffcdd2'
                elif val == 'Střední':
                    return 'background-color: #ffecb3'
                else:
                    return 'background-color: #c8e6c9'
            
            st.dataframe(display_df.style.applymap(color_risk, subset=['Úroveň rizika']), 
                        use_container_width=True, height=500)
            
            # Vysvětlení - tabulka zobrazuje pouze dodavatele z mapy
            st.success("✅ Tabulka zobrazuje pouze dodavatele, kteří jsou zobrazeni na mapě (v ČR s platnými souřadnicemi)")
        else:
            st.info("ℹ️ Žádní dodavatelé k zobrazení")
    else:
        st.error("❌ Nelze načíst data dodavatelů")
        st.info("💡 Zkontrolujte připojení k backendu nebo zkuste později.")

with tab4:
    # Pokročilá analýza - vylepšená
    st.markdown("""
    <div style='background-color: #E8F5E8; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #2E7D32; margin-top: 0;'>🔬 Pokročilá analýza rizik</h3>
        <p style='margin: 5px 0;'>
            <strong>🎯 Účel:</strong> Hlubší analýza rizik a jejich dopadů na dodavatelský řetězec<br>
            <strong>🌊 Simulace záplav:</strong> Modelování dopadů povodní na konkrétní dodavatele<br>
            <strong>🔗 Analýza dodavatelského řetězce:</strong> Hodnocení dopadů událostí na dodávky<br>
            <strong>🗺️ Geografická analýza:</strong> Komplexní posouzení rizik pro libovolnou lokaci
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Přidání srovnání nástrojů
    st.markdown("""
    <div style='background-color: #FFF8E1; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #F57C00; margin-top: 0;'>📊 Srovnání analytických nástrojů</h4>
        <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
            <div style='flex: 1; margin-right: 20px;'>
                <strong>🌊 Simulace záplav:</strong><br>
                • Zaměřeno na dodavatele<br>
                • Analýza polygonů řek<br>
                • Výstup: pravděpodobnost záplav<br>
                • Praktické využití: identifikace ohrožených dodavatelů
            </div>
            <div style='flex: 1;'>
                <strong>🗺️ Geografická analýza:</strong><br>
                • Zaměřeno na lokace<br>
                • Kombinace více faktorů<br>
                • Výstup: celkový risk score<br>
                • Praktické využití: výběr bezpečných lokalit
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Získání dat pro pokročilou analýzu
    flood_data, supply_chain_data = get_advanced_analysis()
    
    # Sekce 1: Simulace záplav - zjednodušená
    st.markdown("#### 🌊 Simulace záplav")
    
    st.markdown("""
    <div style='background-color: #FFF3E0; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #F57C00; margin-top: 0;'>💡 Jak funguje simulace záplav</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>🎯 Cíl:</strong> Simulace dopadů povodní na konkrétní dodavatele<br>
            <strong>📊 Metodika:</strong> Analýza vzdálenosti od polygonů řek + nadmořská výška<br>
            <strong>⚠️ Výstup:</strong> Pravděpodobnost záplav pro každého dodavatele<br>
            <strong>💡 Praktický význam:</strong> Identifikace dodavatelů ohrožených povodněmi<br>
            <strong>🗺️ Vizualizace:</strong> Výsledky se zobrazí na mapě s červenými značkami (🌊)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if "error" not in flood_data:
        if "flood_analysis" in flood_data:
            st.success(f"✅ Simulace dokončena pro {flood_data['total_suppliers_analyzed']} dodavatelů")
            st.info(f"⚠️ {flood_data['high_risk_suppliers']} dodavatelů v rizikových oblastech")
            
            # Zobrazení výsledků - zjednodušené
            for analysis in flood_data['flood_analysis'][:3]:  # Zobrazíme prvních 3
                supplier = analysis['supplier']
                flood_risk = analysis['flood_risk']
                
                with st.expander(f"🏭 {supplier['name']} - {flood_risk['impact_level'].upper()}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Pravděpodobnost záplav", f"{flood_risk['probability']:.1%}")
                        st.metric("Úroveň dopadu", flood_risk['impact_level'].upper())
                    
                    with col2:
                        st.metric("Vzdálenost od řeky", f"{flood_risk['river_distance_km']:.1f} km")
                        st.metric("Nadmořská výška", f"{flood_risk['elevation_m']:.0f} m")
                    
                    with col3:
                        if flood_risk['mitigation_needed']:
                            st.error("⚠️ Potřebná mitigace")
                            st.markdown("**Doporučení:**")
                            st.markdown("• Přesunout výrobu do bezpečnější lokace")
                            st.markdown("• Instalovat protipovodňová opatření")
                            st.markdown("• Vytvořit záložní dodavatelský řetězec")
                        else:
                            st.success("✅ Bezpečná oblast")
                    
                    # Informace o vizualizaci na hlavní mapě
                    st.info("🗺️ Výsledky simulace se zobrazují na hlavní mapě v záložce 'Mapa rizik' s červenými značkami pro rizikové dodavatele.")
        else:
            st.warning("Žádná data k zobrazení")
    else:
        st.error(f"❌ Chyba: {flood_data['error']}")
    
    st.markdown("---")
    
    # Sekce 2: Supply Chain Impact Analysis - zjednodušená
    st.markdown("#### 🔗 Analýza dopadu na dodavatelský řetězec")
    
    st.markdown("""
    <div style='background-color: #E3F2FD; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #1976D2; margin-top: 0;'>💡 Jak funguje analýza dodavatelského řetězce</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>🎯 Cíl:</strong> Hodnocení dopadů rizikových událostí na dodávky<br>
            <strong>📊 Metodika:</strong> Analýza událostí v okolí dodavatelů a jejich kritičnosti<br>
            <strong>⚠️ Výstup:</strong> Pravděpodobnost přerušení dodávek a doba obnovy<br>
            <strong>💡 Praktický význam:</strong> Plánování záložních dodavatelů a krizového managementu
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if "error" not in supply_chain_data:
        if "supply_chain_analysis" in supply_chain_data:
            st.success(f"✅ Analýza dokončena pro {supply_chain_data['total_suppliers']} dodavatelů")
            st.info(f"⚠️ {supply_chain_data['high_risk_suppliers']} dodavatelů s vysokým rizikem")
            
            # Zobrazení výsledků - zjednodušené
            for analysis in supply_chain_data['supply_chain_analysis'][:3]:  # Zobrazíme prvních 3
                supplier = analysis['supplier']
                impact = analysis['impact_assessment']
                
                with st.expander(f"🏭 {supplier['name']} - {impact['impact_level'].upper()}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Riziko přerušení", f"{impact['disruption_probability']:.1%}")
                        st.metric("Doba obnovy", f"{impact['estimated_recovery_days']} dní")
                    
                    with col2:
                        st.metric("Úroveň dopadu", impact['impact_level'].upper())
                        if impact['alternative_suppliers_needed']:
                            st.error("⚠️ Potřební záložní dodavatelé")
                        else:
                            st.success("✅ Stabilní dodávky")
                    
                    with col3:
                        st.markdown("**Mitigační opatření:**")
                        for action in impact['mitigation_actions'][:3]:
                            st.markdown(f"• {action}")
        else:
            st.warning("Žádná data k zobrazení")
    else:
        st.error(f"❌ Chyba: {supply_chain_data['error']}")
    
    st.markdown("---")
    
    # Sekce 3: Geographic Risk Assessment Tool - zjednodušená
    st.markdown("#### 🗺️ Geografická analýza rizik")
    
    st.markdown("""
    <div style='background-color: #F3E5F5; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
        <h4 style='color: #7B1FA2; margin-top: 0;'>💡 Jak funguje geografická analýza</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>🎯 Cíl:</strong> Komplexní posouzení rizik pro libovolnou lokaci<br>
            <strong>📊 Metodika:</strong> Kombinace analýzy řek + terénu + historických událostí<br>
            <strong>⚠️ Výstup:</strong> Celkový risk score a doporučení pro lokaci<br>
            <strong>💡 Praktický význam:</strong> Výběr bezpečných lokalit pro nové dodavatele<br>
            <strong>🗺️ Vizualizace:</strong> Výsledky se zobrazí na mapě s barevným kódováním (🗺️)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        lat = st.number_input("Zeměpisná šířka", value=50.0755, format="%.4f", help="Zadejte souřadnice pro analýzu")
        lon = st.number_input("Zeměpisná délka", value=14.4378, format="%.4f")
        radius = st.slider("Poloměr analýzy (km)", 10, 100, 50)
    
    with col2:
        if st.button("🔍 Spustit geografickou analýzu", type="primary"):
            try:
                response = requests.get(
                    f"{BACKEND_URL}/api/analysis/geographic-risk-assessment",
                    params={"lat": lat, "lon": lon, "radius_km": radius}
                )
                
                if response.status_code == 200:
                    geo_data = response.json()
                    
                    st.success("✅ Analýza dokončena")
                    
                    # Zobrazení výsledků
                    risk_assessment = geo_data['combined_risk_assessment']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Celkové riziko", risk_assessment['overall_risk_level'].upper())
                        st.metric("Risk score", f"{risk_assessment['risk_score']}/100")
                    
                    with col2:
                        river_analysis = geo_data['river_analysis']
                        st.metric("Vzdálenost od řeky", f"{river_analysis['nearest_river_distance_km']:.1f} km")
                        if river_analysis['flood_risk_zone']:
                            st.error("⚠️ Záplavová zóna")
                        else:
                            st.success("✅ Bezpečná oblast")
                    
                    with col3:
                        elevation_analysis = geo_data['elevation_analysis']
                        st.metric("Nadmořská výška", f"{elevation_analysis['elevation_m']:.0f} m")
                        st.metric("Typ terénu", elevation_analysis['terrain_type'])
                    
                    # Doporučení
                    st.markdown("**📋 Doporučení:**")
                    for rec in risk_assessment['recommendations']:
                        st.markdown(f"• {rec}")
                    
                    # Informace o vizualizaci na hlavní mapě
                    st.info("🗺️ Výsledky geografické analýzy se zobrazují na hlavní mapě v záložce 'Mapa rizik' s barevným kódováním rizik (červená = vysoké, oranžová = střední, zelená = nízké).")
                    
                else:
                    st.error(f"❌ Chyba při analýze: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Chyba: {str(e)}")
        else:
            st.info("💡 Zadejte souřadnice a spusťte analýzu")

with tab5:
    st.header("ℹ️ O aplikaci")
    
    st.markdown("""
    <div style='background-color: #E8F5E8; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #2E7D32; margin-top: 0;'>🎯 Účel aplikace</h3>
        <p style='margin: 10px 0;'>
            <strong>Risk Analyst Dashboard</strong> je komplexní nástroj pro analýzu rizik v dodavatelském řetězci. 
            Aplikace byla vytvořena jako ukázka technických dovedností pro pozici <strong>Risk Analyst</strong>.
        </p>
        <p style='margin: 10px 0;'>
            <strong>Hlavní cíle:</strong><br>
            • Identifikace rizikových oblastí v dodavatelském řetězci<br>
            • Monitoring událostí s dopadem na výrobu<br>
            • Analýza vztahů mezi dodavateli a rizikovými událostmi<br>
            • Predikce možných dopadů na dodavatelský řetězec
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style='background-color: #E3F2FD; padding: 15px; border-radius: 10px;'>
            <h4 style='color: #1976D2; margin-top: 0;'>🔍 Klíčové funkce</h4>
            <ul style='margin: 5px 0; padding-left: 20px;'>
                <li><strong>🗺️ Interaktivní mapa</strong> - vizualizace rizikových událostí a dodavatelů</li>
                <li><strong>🔍 Pokročilé filtry</strong> - filtrování podle typu, závažnosti, zdroje a času</li>
                <li><strong>🔍 Automatický scraping</strong> - získávání aktuálních dat z RSS a API</li>
                <li><strong>🏭 Dodavatelská analýza</strong> - hodnocení rizik dodavatelů</li>
                <li><strong>🔬 Pokročilá analýza</strong> - simulace záplav a geografická analýza</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background-color: #FFF3E0; padding: 15px; border-radius: 10px;'>
            <h4 style='color: #F57C00; margin-top: 0;'>⚙️ Technologie</h4>
            <p style='margin: 5px 0;'><strong>Frontend:</strong></p>
            <ul style='margin: 5px 0; padding-left: 20px;'>
                <li>Streamlit (web framework)</li>
                <li>Folium (interaktivní mapy)</li>
                <li>Pandas (datová analýza)</li>
            </ul>
            <p style='margin: 5px 0;'><strong>Backend:</strong></p>
            <ul style='margin: 5px 0; padding-left: 20px;'>
                <li>FastAPI (REST API)</li>
                <li>PostgreSQL + PostGIS (GIS databáze)</li>
                <li>Web scraping (requests, xml)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background-color: #F3E5F5; padding: 20px; border-radius: 10px; margin: 20px 0;'>
        <h3 style='color: #7B1FA2; margin-top: 0;'>📊 Zdroje dat a jejich význam</h3>
        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 20px;'>
            <div>
                <h4 style='color: #7B1FA2; margin-top: 0;'>🌤️ CHMI API</h4>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Hydrologické výstrahy:</strong> Záplavy a povodně</li>
                    <li><strong>Meteorologická data:</strong> Extrémní počasí</li>
                    <li><strong>Význam:</strong> Aktuální přírodní rizika</li>
                </ul>
            </div>
            <div>
                <h4 style='color: #7B1FA2; margin-top: 0;'>📰 RSS feeds</h4>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Novinky.cz:</strong> Aktuální zprávy a události</li>
                    <li><strong>Seznam Zprávy, HN, iRozhlas:</strong> Další česká média</li>
                    <li><strong>Význam:</strong> Sociální a geopolitická rizika</li>
                </ul>
            </div>
        </div>
        <div style='margin-top: 15px; padding: 10px; background-color: #FFF3E0; border-radius: 5px;'>
            <h4 style='color: #F57C00; margin-top: 0;'>🔍 Filtry a jejich význam</h4>
            <p style='margin: 5px 0; font-size: 0.9em;'>
                <strong>📊 Typ události:</strong> Záplavy, protesty, dodavatelské problémy, geopolitické události<br>
                <strong>⚠️ Závažnost:</strong> Kritické (okamžitý dopad) až Nízké (minimální riziko)<br>
                <strong>🔗 Zdroj dat:</strong> CHMI API (počasí), RSS feeds (zprávy), ručně přidané<br>
                <strong>📅 Časové období:</strong> Filtrování podle data události
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background-color: #E0F2F1; padding: 20px; border-radius: 10px; margin: 20px 0;'>
        <h3 style='color: #00695C; margin-top: 0;'>🎯 Praktické využití</h3>
        <p style='margin: 10px 0;'>
            <strong>Risk Analyst Dashboard</strong> umožňuje efektivně monitorovat a analyzovat rizika v dodavatelském řetězci:
        </p>
        <ul style='margin: 10px 0; padding-left: 20px;'>
            <li><strong>Včasné varování:</strong> Identifikace rizikových oblastí před dopadem na výrobu</li>
            <li><strong>Dodavatelská analýza:</strong> Hodnocení rizik jednotlivých dodavatelů</li>
            <li><strong>Geografická analýza:</strong> Vizualizace rizikových oblastí na mapě</li>
            <li><strong>Automatický monitoring:</strong> Sledování vývoje rizik v čase</li>
            <li><strong>Pokročilé simulace:</strong> Modelování dopadů záplav a událostí</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
        © 2025 Risk Analyst Dashboard | Vytvořeno jako ukázka technických dovedností
    </div>
    """, unsafe_allow_html=True)
    