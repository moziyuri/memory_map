"""
Risk Analyst Dashboard - Interaktivní mapa rizikových událostí

Streamlit aplikace pro vizualizaci a analýzu rizikových událostí v dodavatelském řetězci.
Součást projektu vytvořeného pro VW Group Risk Analyst pozici.

Funkce:
- Interaktivní mapa pro zobrazení rizikových událostí
- Filtry podle typu události, závažnosti, zdroje
- Zobrazení dodavatelů a jejich rizik
- Analýza rizik v okolí dodavatelů

Autor: Vytvořeno jako ukázka dovedností pro VW Group Risk Analyst pozici.
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
    """Získání konzistentních statistik napříč celou aplikací"""
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
    
    # Počítání událostí v ČR
    czech_events = 0
    high_critical_events = 0
    recent_events = 0
    
    for event in events:
        try:
            lat = float(event.get("latitude", 0))
            lon = float(event.get("longitude", 0))
            
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
    
    # Počítání dodavatelů
    czech_suppliers = 0
    high_risk_suppliers = 0
    
    if suppliers:
        for supplier in suppliers:
            try:
                lat = float(supplier.get("latitude", 0))
                lon = float(supplier.get("longitude", 0))
                
                if is_in_czech_republic(lat, lon):
                    czech_suppliers += 1
                
                if supplier.get("risk_level") == "high":
                    high_risk_suppliers += 1
            except:
                pass
    
    return {
        'total_events': len(events),
        'czech_events': czech_events,
        'high_critical_events': high_critical_events,
        'recent_events': recent_events,
        'total_suppliers': len(suppliers) if suppliers else 0,
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

# Helper funkce pro vytvoření mapy s rizikovými událostmi
def create_risk_map(events, suppliers, center_lat=DEFAULT_LAT, center_lon=DEFAULT_LON, zoom_start=8):
    """Vytvoření mapy s rizikovými událostmi a dodavateli - pouze v ČR"""
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
    
    # Vysvětlení aplikace
    st.markdown("""
    <div style='background-color: #E8F5E8; padding: 15px; border-radius: 10px; border-left: 4px solid #4CAF50;'>
        <h4 style='color: #2E7D32; margin-top: 0;'>🎯 Účel aplikace</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            Dashboard pro analýzu rizik v dodavatelském řetězci.
        </p>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>⚠️ Události:</strong> Rizikové situace (záplavy, protesty, dodavatelské problémy)<br>
            <strong>🏭 Dodavatelé:</strong> Dodavatelé s hodnocením rizika<br>
            <strong>📊 Analýza:</strong> Vzájemné vztahy a dopady na dodavatelský řetězec
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    # Vysvětlení zdrojů dat - zjednodušené
    st.markdown("""
    <div style='background-color: #FFF3E0; padding: 15px; border-radius: 10px; border-left: 4px solid #FF9800; margin-top: 15px;'>
        <h4 style='color: #F57C00; margin-top: 0;'>🔗 Zdroje dat</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>🌤️ CHMI:</strong> Meteorologická data a výstrahy<br>
            <strong>📰 RSS:</strong> Zprávy z českých médií<br>
            <strong>✋ Ruční:</strong> Manuálně přidané události<br>
            <strong>📊 V mapě:</strong> Červené ikony = rizikové události, modré ikony = dodavatelé<br>
            <strong>💡 Tip:</strong> Spusťte scraping pro získání aktuálních dat
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        # Vysvětlení filtrů
        st.markdown("""
        <div style='background-color: #F0F8FF; padding: 10px; border-radius: 8px; margin: 10px 0;'>
            <h5 style='color: #1E90FF; margin-top: 0;'>💡 Vysvětlení filtrů</h5>
            <p style='margin: 3px 0; font-size: 0.8em;'>
                <strong>📊 Typ události:</strong> Záplavy, protesty, dodavatelské problémy, geopolitické události<br>
                <strong>⚠️ Závažnost:</strong> Kritické (okamžitý dopad) až Nízké (minimální riziko)<br>
                <strong>🔗 Zdroj dat:</strong> CHMI API (počasí), RSS feeds (zprávy), ručně přidané
            </p>
        </div>
        """, unsafe_allow_html=True)
        
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
        
        # Tlačítko pro spuštění scraping
        st.subheader("🔄 Aktualizace dat")
        if st.button("🔄 Spustit scraping", type="primary", help="Spustí web scraping pro získání aktuálních dat"):
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
    "📊 Statistiky", 
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
            
            m = create_risk_map(filtered_events, suppliers, center_lat, center_lon, zoom_start)
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
            else:
                st.success(f"✅ Zobrazeno {len(filtered_events)} událostí a {len(suppliers)} dodavatelů")
                
        except Exception as e:
            st.error(f"❌ Chyba při vytváření mapy: {str(e)}")
            st.info("💡 Zkuste obnovit stránku nebo kontaktujte správce aplikace.")
    else:
        st.error("❌ Nelze načíst rizikové události")
        st.info("💡 Zkuste spustit scraping pro získání dat nebo zkontrolujte připojení k backendu.")

with tab2:
    # Statistiky
    st.markdown("""
    <div style='background-color: #E3F2FD; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #1976D2; margin-top: 0;'>📊 Komplexní analýza rizik</h3>
        <p style='margin: 5px 0;'>
            <strong>📈 Trendy:</strong> Vývoj rizik v čase<br>
            <strong>🎯 Klíčové metriky:</strong> Přehled nejdůležitějších ukazatelů<br>
            <strong>📊 Rozložení:</strong> Analýza podle typu a závažnosti<br>
            <strong>🏭 Dopady:</strong> Vztahy mezi událostmi a dodavateli
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
        
        # Klíčové metriky
        st.subheader("🎯 Klíčové metriky")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Celkem událostí", stats['total_events'], help="Celkový počet rizikových událostí")
        
        with col2:
            risk_percentage = (stats['high_critical_events'] / stats['total_events'] * 100) if stats['total_events'] > 0 else 0
            st.metric("⚠️ Vysoké/Kritické riziko", f"{stats['high_critical_events']} ({risk_percentage:.1f}%)", 
                     delta=f"{risk_percentage:.1f}%", help="Události s vysokým nebo kritickým rizikem")
        
        with col3:
            st.metric("🕒 Posledních 7 dní", stats['recent_events'], help="Události z posledního týdne")
        
        with col4:
            st.metric("🇨🇿 Události v ČR", stats['czech_events'], help="Události na území České republiky")
        
        # Zjednodušené grafy s lepšími vysvětleními
        st.subheader("📊 Rozložení rizik")
        col1, col2 = st.columns(2)
        
        with col1:
            # Rozložení podle typu události - pouze pokud máme data
            if not df_events.empty and 'event_type_cz' in df_events.columns:
                event_type_counts = df_events['event_type_cz'].value_counts()
                if not event_type_counts.empty:
                    st.bar_chart(event_type_counts)
                    st.caption("📊 Rozložení rizikových událostí podle typu")
                else:
                    st.info("ℹ️ Žádná data pro zobrazení grafu")
            else:
                st.info("ℹ️ Žádná data pro zobrazení grafu")
        
        with col2:
            # Rozložení podle závažnosti - pouze pokud máme data
            if not df_events.empty and 'severity_cz' in df_events.columns:
                severity_counts = df_events['severity_cz'].value_counts()
                if not severity_counts.empty:
                    st.bar_chart(severity_counts)
                    st.caption("⚠️ Rozložení událostí podle závažnosti")
                else:
                    st.info("ℹ️ Žádná data pro zobrazení grafu")
            else:
                st.info("ℹ️ Žádná data pro zobrazení grafu")
        
        # Nejnovější události s lepším formátováním
        st.subheader("🕒 Nejnovější události")
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
        
        # Převod na DataFrame
        df_suppliers = pd.DataFrame(suppliers)
        
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
        df_suppliers['category_cz'] = df_suppliers['category'].map(category_translations).fillna('Neznámé')
        df_suppliers['risk_level_cz'] = df_suppliers['risk_level'].map(risk_translations).fillna('Neznámé')
        df_suppliers['created_at'] = pd.to_datetime(df_suppliers['created_at'])
        
        # Klíčové metriky dodavatelů
        st.subheader("🎯 Klíčové metriky dodavatelů")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏭 Celkem dodavatelů", stats['total_suppliers'], help="Celkový počet dodavatelů")
        
        with col2:
            risk_percentage = (stats['high_risk_suppliers'] / stats['total_suppliers'] * 100) if stats['total_suppliers'] > 0 else 0
            st.metric("⚠️ Vysoké riziko", f"{stats['high_risk_suppliers']} ({risk_percentage:.1f}%)", 
                     delta=f"{risk_percentage:.1f}%", help="Dodavatelé s vysokým rizikem")
        
        with col3:
            categories_count = len(set([s.get("category", "unknown") for s in suppliers]))
            st.metric("🏷️ Kategorie", categories_count, help="Počet různých kategorií dodavatelů")
        
        with col4:
            st.metric("🇨🇿 Dodavatelé v ČR", stats['czech_suppliers'], help="Dodavatelé na území České republiky")
        
        # Zjednodušené grafy
        st.subheader("📊 Rozložení dodavatelů")
        col1, col2 = st.columns(2)
        
        with col1:
            # Rozložení podle kategorie - pouze pokud máme data
            if not df_suppliers.empty and 'category_cz' in df_suppliers.columns:
                category_counts = df_suppliers['category_cz'].value_counts()
                if not category_counts.empty:
                    st.bar_chart(category_counts)
                    st.caption("Rozložení podle kategorie")
                else:
                    st.info("ℹ️ Žádná data pro zobrazení grafu")
            else:
                st.info("ℹ️ Žádná data pro zobrazení grafu")
        
        with col2:
            # Rozložení podle rizika - pouze pokud máme data
            if not df_suppliers.empty and 'risk_level_cz' in df_suppliers.columns:
                risk_counts = df_suppliers['risk_level_cz'].value_counts()
                if not risk_counts.empty:
                    st.bar_chart(risk_counts)
                    st.caption("Rozložení podle úrovně rizika")
                else:
                    st.info("ℹ️ Žádná data pro zobrazení grafu")
            else:
                st.info("ℹ️ Žádná data pro zobrazení grafu")
        
        # Seznam dodavatelů s vylepšeným formátováním
        st.subheader("📋 Seznam dodavatelů")
        if not df_suppliers.empty:
            # Vylepšené zobrazení tabulky
            display_df = df_suppliers[['name', 'category_cz', 'risk_level_cz', 'created_at']].copy()
            display_df['created_at'] = display_df['created_at'].dt.strftime('%d.%m.%Y %H:%M')
            display_df.columns = ['Název', 'Kategorie', 'Úroveň rizika', 'Datum']
            
            # Přidání barevného formátování
            def color_risk(val):
                if val == 'Vysoké':
                    return 'background-color: #ffcdd2'
                elif val == 'Střední':
                    return 'background-color: #ffecb3'
                else:
                    return 'background-color: #c8e6c9'
            
            st.dataframe(display_df.style.applymap(color_risk, subset=['Úroveň rizika']), 
                        use_container_width=True, height=400)
        else:
            st.info("ℹ️ Žádní dodavatelé k zobrazení")
        
        # Souhrnné statistiky dodavatelů
        st.subheader("📋 Souhrnné statistiky dodavatelů")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style='background-color: #F5F5F5; padding: 15px; border-radius: 8px;'>
                <h5 style='margin-top: 0;'>📊 Přehled dodavatelů</h5>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Celkem dodavatelů:</strong> {}</li>
                    <li><strong>Vysoké riziko:</strong> {} ({:.1f}%)</li>
                    <li><strong>Dodavatelé v ČR:</strong> {}</li>
                    <li><strong>Různé kategorie:</strong> {}</li>
                </ul>
            </div>
            """.format(
                stats['total_suppliers'],
                stats['high_risk_suppliers'],
                (stats['high_risk_suppliers'] / stats['total_suppliers'] * 100) if stats['total_suppliers'] > 0 else 0,
                stats['czech_suppliers'],
                len(set([s.get("category", "unknown") for s in suppliers]))
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style='background-color: #E8F5E8; padding: 15px; border-radius: 8px;'>
                <h5 style='margin-top: 0;'>🎯 Doporučení pro dodavatele</h5>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Priorita 1:</strong> Monitorovat dodavatele s vysokým rizikem</li>
                    <li><strong>Priorita 2:</strong> Analyzovat rizikové kategorie</li>
                    <li><strong>Priorita 3:</strong> Kontaktovat kritické dodavatele</li>
                    <li><strong>Priorita 4:</strong> Aktualizovat data pravidelně</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.warning("⚠️ Nelze načíst data dodavatelů")

with tab4:
    st.markdown("## 🔬 Pokročilá analýza rizik")
    st.markdown("### Simulace záplav a geografická analýza")
    
    # Načtení dat
    flood_data, supply_chain_data = get_advanced_analysis()
    
    # Sekce 1: River Flood Simulation
    st.markdown("#### 🌊 Simulace záplav")
    
    if "error" not in flood_data:
        if "flood_analysis" in flood_data:
            st.success(f"✅ Analýza dokončena pro {flood_data['total_suppliers_analyzed']} dodavatelů")
            st.info(f"⚠️ {flood_data['high_risk_suppliers']} dodavatelů v rizikových oblastech")
            
            # Zobrazení výsledků
            for analysis in flood_data['flood_analysis'][:5]:  # Zobrazíme prvních 5
                supplier = analysis['supplier']
                flood_risk = analysis['flood_risk']
                
                with st.expander(f"🏭 {supplier['name']} ({supplier['category']})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Pravděpodobnost záplav", f"{flood_risk['probability']:.1%}")
                        st.metric("Úroveň dopadu", flood_risk['impact_level'].upper())
                    
                    with col2:
                        st.metric("Vzdálenost od řeky", f"{flood_risk['river_distance_km']:.1f} km")
                        st.metric("Nadmořská výška", f"{flood_risk['elevation_m']:.0f} m")
                    
                    with col3:
                        st.metric("Hladina záplav", f"{flood_risk['flood_level_m']} m")
                        if flood_risk['mitigation_needed']:
                            st.error("⚠️ Potřebná mitigace")
                        else:
                            st.success("✅ Bezpečná oblast")
        else:
            st.warning("Žádná data k zobrazení")
    else:
        st.error(f"❌ Chyba: {flood_data['error']}")
    
    st.markdown("---")
    
    # Sekce 2: Supply Chain Impact Analysis
    st.markdown("#### 🔗 Analýza dopadu na dodavatelský řetězec")
    
    if "error" not in supply_chain_data:
        if "supply_chain_analysis" in supply_chain_data:
            st.success(f"✅ Analýza dokončena pro {supply_chain_data['total_suppliers']} dodavatelů")
            st.info(f"⚠️ {supply_chain_data['high_risk_suppliers']} dodavatelů s vysokým rizikem")
            
            # Zobrazení výsledků
            for analysis in supply_chain_data['supply_chain_analysis'][:5]:  # Zobrazíme prvních 5
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
    
    # Sekce 3: Geographic Risk Assessment Tool
    st.markdown("#### 🗺️ Geografická analýza rizik")
    
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
                        
                else:
                    st.error("❌ Chyba při analýze")
                    
            except Exception as e:
                st.error(f"❌ Chyba: {str(e)}")
    
    st.markdown("---")
    
    # Sekce 4: Informace o funkcích
    st.markdown("#### 💡 Informace o pokročilých funkcích")
    
    st.markdown("""
    **🌊 Simulace záplav:**
    - Výpočet vzdálenosti od hlavních řek ČR
    - Analýza nadmořské výšky a terénu
    - Simulace pravděpodobnosti záplav
    - Hodnocení dopadu na dodavatele
    
    **🔗 Analýza dodavatelského řetězce:**
    - Identifikace kritických dodavatelů
    - Simulace dopadu událostí na dodávky
    - Odhad doby obnovy po přerušení
    - Generování mitigačních opatření
    
    **🗺️ Geografická analýza:**
    - Komplexní hodnocení rizik pro danou lokaci
    - Kombinace více faktorů (řeky, výška, historie)
    - Doporučení pro snížení rizik
    - Monitoring změn v čase
    """)

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
                <li><strong>📊 Analytické statistiky</strong> - analýza rozložení rizik</li>
                <li><strong>🔄 Automatický scraping</strong> - získávání aktuálních dat z RSS a API</li>
                <li><strong>🏭 Dodavatelská analýza</strong> - hodnocení rizik dodavatelů</li>
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
            <li><strong>Trendová analýza:</strong> Sledování vývoje rizik v čase</li>
            <li><strong>Reportování:</strong> Generování reportů pro management</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# Patička aplikace
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 10px;'>
        <p>© 2025 Risk Analyst Dashboard</p>
        <p style='font-size: 0.8em;'>
            Vytvořeno jako ukázka technických dovedností pro pozici Risk Analyst
        </p>
    </div>
    """,
    unsafe_allow_html=True
) 

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
    