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
    page_title="VW Group Risk Analyst Dashboard",  # Titulek stránky v prohlížeči
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
def create_risk_map(events, suppliers, center_lat=DEFAULT_LAT, center_lon=DEFAULT_LON):
    """Vytvoření mapy s rizikovými událostmi a dodavateli - pouze v ČR"""
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=7,
        tiles='OpenStreetMap',
        control_scale=True
    )
    
    # Přidání různých mapových vrstev
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap',
        overlay=False
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://mapserver.mapy.cz/base-m/{z}-{x}-{y}',
        attr='Mapy.cz',
        name='Mapy.cz',
        overlay=False
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        name='Satelitní mapa',
        overlay=False
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google Maps',
        name='Google Maps',
        overlay=False
    ).add_to(m)
    
    # Přidání ovladače vrstev s lepším umístěním
    folium.LayerControl(position='topright').add_to(m)
    
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
                
                # Popup obsah s lepším rozlišením
                popup_content = f"""
                <div style='width: 350px; padding: 15px; font-family: Arial, sans-serif;'>
                    <h3 style='color: {color}; margin-top: 0; border-bottom: 2px solid {color}; padding-bottom: 5px;'>
                        {title}
                    </h3>
                    <div style='background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin: 10px 0; 
                               border-left: 4px solid {color};'>
                        {description}
                    </div>
                    <div style='margin-top: 15px;'>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>📊 Typ události:</strong> 
                            <span style='background-color: #E3F2FD; padding: 3px 8px; border-radius: 4px; font-weight: bold;'>
                                {event_type.upper()}
                            </span>
                        </p>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>⚠️ Závažnost:</strong> 
                            <span class='risk-{severity}' style='font-size: 1.1em;'>{severity.upper()}</span>
                        </p>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>📅 Datum:</strong> {formatted_date}
                        </p>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>🔗 Zdroj:</strong> 
                            <span class='{source_class}'>{source}</span>
                        </p>
                    </div>
                </div>
                """
                
                # Přidání markeru
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=350),
                    tooltip=f"⚠️ {title} ({severity})",
                    icon=folium.Icon(icon=icon_name, prefix="fa", color=color)
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
                
                # Formátování data
                formatted_date = format_date(created_at)
                
                # Popup obsah pro dodavatele
                popup_content = f"""
                <div style='width: 350px; padding: 15px; font-family: Arial, sans-serif;'>
                    <h3 style='color: {color}; margin-top: 0; border-bottom: 2px solid {color}; padding-bottom: 5px;'>
                        🏭 {name}
                    </h3>
                    <div style='margin-top: 15px;'>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>🏷️ Kategorie:</strong> 
                            <span style='background-color: #E3F2FD; padding: 3px 8px; border-radius: 4px; font-weight: bold;'>
                                {category.upper()}
                            </span>
                        </p>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>⚠️ Úroveň rizika:</strong> 
                            <span class='risk-{risk_level}' style='font-size: 1.1em;'>{risk_level.upper()}</span>
                        </p>
                        <p style='margin: 8px 0;'>
                            <strong style='color: #0D47A1;'>📅 Datum:</strong> {formatted_date}
                        </p>
                    </div>
                </div>
                """
                
                # Přidání markeru dodavatele (jiný styl)
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=350),
                    tooltip=f"🏭 {name} ({risk_level})",
                    icon=folium.Icon(icon="industry", prefix="fa", color=color)
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
        'CHMI API (reálná data)': 'chmi_scraped',
        'RSS feeds (reálná data)': 'rss_scraped',
        'CHMI (demo data)': 'chmi_fallback',
        'RSS (demo data)': 'rss_fallback',
        'Ručně přidané': 'manual',
        'Demo data': 'demo',
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
            Dashboard pro analýzu rizik v dodavatelském řetězci <strong>VW Group</strong>.
        </p>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>⚠️ Události:</strong> Rizikové situace (záplavy, protesty, dodavatelské problémy)<br>
            <strong>🏭 Dodavatelé:</strong> VW Group dodavatelé s hodnocením rizika<br>
            <strong>📊 Analýza:</strong> Vzájemné vztahy a dopady na dodavatelský řetězec
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Vysvětlení zdrojů dat
    st.markdown("""
    <div style='background-color: #FFF3E0; padding: 15px; border-radius: 10px; border-left: 4px solid #FF9800; margin-top: 15px;'>
        <h4 style='color: #F57C00; margin-top: 0;'>🔗 Zdroje dat</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <span class='data-scraped'>🔵 Scraped</span> - Reálná data z CHMI a RSS feedů<br>
            <span class='data-fallback'>🟡 Fallback</span> - Demo data při neúspěšném scrapingu<br>
            <span class='data-source'>🟢 Source</span> - Původní data z databáze
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
    
    # Filtry
    st.markdown("""
    <div style='background-color: #F5F5F5; padding: 15px; border-radius: 10px; margin: 15px 0;'>
        <h4 style='color: #333; margin-top: 0;'>🔍 Filtry</h4>
        <p style='margin: 5px 0; font-size: 0.9em;'>
            <strong>📊 Typ události:</strong> Kategorie rizikových událostí<br>
            <strong>⚠️ Závažnost:</strong> Úroveň rizika od nízké po kritické<br>
            <strong>🔗 Zdroj dat:</strong> Původ dat (reálná vs. demo data)<br>
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
            'chmi_scraped': 'CHMI API (reálná data)',
            'rss_scraped': 'RSS feeds (reálná data)',
            'chmi_fallback': 'CHMI (demo data)',
            'rss_fallback': 'RSS (demo data)',
            'manual': 'Ručně přidané',
            'demo': 'Demo data',
            'unknown': 'Neznámé'
        }
        
        # Získání unikátních hodnot
        event_types = ["Všechny"] + [event_type_translations.get(et, et) for et in set([e.get("event_type", "unknown") for e in events])]
        severities = ["Všechny"] + [severity_translations.get(sev, sev) for sev in set([e.get("severity", "medium") for e in events])]
        sources = ["Všechny"] + [source_translations.get(src, src) for src in set([e.get("source", "unknown") for e in events])]
        
        selected_event_type = st.selectbox("📊 Typ události:", event_types, help="Vyberte typ rizikové události")
        selected_severity = st.selectbox("⚠️ Závažnost:", severities, help="Vyberte úroveň závažnosti")
        selected_source = st.selectbox("🔗 Zdroj dat:", sources, help="Vyberte zdroj dat")
        
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
                if result:
                    st.success("✅ Scraping dokončen!")
                    st.json(result)
                else:
                    st.error("❌ Chyba při scraping")
    else:
        st.warning("⚠️ Nelze načíst data pro filtry")

# Hlavní obsah aplikace
st.markdown("<h1 class='main-header'>⚠️ VW Group Risk Analyst Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Komplexní analýza rizik v dodavatelském řetězci</p>", unsafe_allow_html=True)

# Záložky pro různé části aplikace
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Mapa rizik", "📊 Statistiky", "🏭 Dodavatelé", "ℹ️ O aplikaci"])

with tab1:
    # Mapa rizik
    st.markdown("""
    <div style='background-color: #E3F2FD; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #1976D2; margin-top: 0;'>🗺️ Interaktivní mapa rizik</h3>
        <p style='margin: 5px 0;'>
            <strong>⚠️ Červené body:</strong> Rizikové události (záplavy, protesty, dodavatelské problémy)<br>
            <strong>🏭 Modré body:</strong> Dodavatelé VW Group s hodnocením rizika<br>
            <strong>🎯 Cíl:</strong> Identifikace rizikových oblastí a jejich dopadů na dodavatelský řetězec
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
        
        # Statistiky zobrazených dat
        czech_events = getattr(st.session_state, 'czech_events', 0)
        total_events = getattr(st.session_state, 'total_events', 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Zobrazené události", len(filtered_events))
        with col2:
            st.metric("🇨🇿 Události v ČR", czech_events)
        with col3:
            st.metric("🌍 Celkem událostí", total_events)
        
        # Vytvoření a zobrazení mapy s klíčem pro prevenci reloadingu
        try:
            m = create_risk_map(filtered_events, suppliers)
            map_data = st_folium(
                m, 
                width=None,  # Automatická šířka
                height=700,  # Větší výška
                key=f"map_{st.session_state.map_key}",
                returned_objects=["last_object_clicked"]
            )
        except Exception as e:
            st.error(f"Chyba při vytváření mapy: {str(e)}")
    else:
        st.error("❌ Nelze načíst rizikové události")

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
            total_events = len(events)
            st.metric("📊 Celkem událostí", total_events, help="Celkový počet rizikových událostí")
        
        with col2:
            high_critical_risk = len([e for e in events if e.get("severity") in ["high", "critical"]])
            risk_percentage = (high_critical_risk / total_events * 100) if total_events > 0 else 0
            st.metric("⚠️ Vysoké/Kritické riziko", f"{high_critical_risk} ({risk_percentage:.1f}%)", 
                     delta=f"{risk_percentage:.1f}%", help="Události s vysokým nebo kritickým rizikem")
        
        with col3:
            recent_events = len([e for e in events if pd.to_datetime(e.get("created_at", "")) > (datetime.now() - timedelta(days=7))])
            st.metric("🕒 Posledních 7 dní", recent_events, help="Události z posledního týdne")
        
        with col4:
            czech_events_count = getattr(st.session_state, 'czech_events', 0)
            st.metric("🇨🇿 Události v ČR", czech_events_count, help="Události na území České republiky")
        
        # Trendy v čase
        st.subheader("📈 Trendy v čase")
        col1, col2 = st.columns(2)
        
        with col1:
            # Denní trend událostí
            df_events['date'] = df_events['created_at'].dt.date
            daily_counts = df_events.groupby('date').size().reset_index(name='count')
            if not daily_counts.empty:
                st.line_chart(daily_counts.set_index('date'))
                st.caption("Denní počet událostí")
        
        with col2:
            # Trend podle závažnosti
            severity_trend = df_events.groupby(['date', 'severity_cz']).size().reset_index(name='count')
            if not severity_trend.empty:
                st.line_chart(severity_trend.pivot(index='date', columns='severity_cz', values='count').fillna(0))
                st.caption("Trend podle závažnosti")
        
        # Rozložení dat
        st.subheader("📊 Rozložení dat")
        col1, col2 = st.columns(2)
        
        with col1:
            # Rozložení podle typu události
            event_type_counts = df_events['event_type_cz'].value_counts()
            st.bar_chart(event_type_counts)
            st.caption("Rozložení podle typu události")
        
        with col2:
            # Rozložení podle závažnosti
            severity_counts = df_events['severity_cz'].value_counts()
            st.bar_chart(severity_counts)
            st.caption("Rozložení podle závažnosti")
        
        # Analýza zdrojů dat
        st.subheader("🔗 Analýza zdrojů dat")
        col1, col2 = st.columns(2)
        
        with col1:
            # Rozložení podle zdroje
            source_counts = df_events['source'].value_counts()
            st.bar_chart(source_counts)
            st.caption("Rozložení podle zdroje dat")
        
        with col2:
            # Statistiky zdrojů
            scraped_count = len([e for e in events if 'scraped' in e.get('source', '').lower()])
            fallback_count = len([e for e in events if 'fallback' in e.get('source', '').lower()])
            manual_count = len([e for e in events if e.get('source') == 'manual'])
            
            source_stats = pd.DataFrame({
                'Zdroj': ['Reálná data', 'Demo data', 'Ručně přidané'],
                'Počet': [scraped_count, fallback_count, manual_count]
            })
            st.bar_chart(source_stats.set_index('Zdroj'))
            st.caption("Porovnání zdrojů dat")
        
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
        
        # Souhrnné statistiky
        st.subheader("📋 Souhrnné statistiky")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style='background-color: #F5F5F5; padding: 15px; border-radius: 8px;'>
                <h5 style='margin-top: 0;'>📊 Přehled</h5>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Průměrná závažnost:</strong> {}</li>
                    <li><strong>Nejčastější typ:</strong> {}</li>
                    <li><strong>Nejaktivnější den:</strong> {}</li>
                    <li><strong>Nejvíce rizikových oblastí:</strong> {}</li>
                </ul>
            </div>
            """.format(
                df_events['severity_cz'].mode().iloc[0] if not df_events['severity_cz'].empty else 'N/A',
                df_events['event_type_cz'].mode().iloc[0] if not df_events['event_type_cz'].empty else 'N/A',
                df_events['date'].mode().iloc[0] if not df_events['date'].empty else 'N/A',
                'ČR' if czech_events_count > total_events/2 else 'Celosvětově'
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style='background-color: #E8F5E8; padding: 15px; border-radius: 8px;'>
                <h5 style='margin-top: 0;'>🎯 Doporučení</h5>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Priorita 1:</strong> Sledovat {} události</li>
                    <li><strong>Priorita 2:</strong> Analyzovat {} oblasti</li>
                    <li><strong>Priorita 3:</strong> Monitorovat {} zdroje</li>
                    <li><strong>Priorita 4:</strong> Aktualizovat každých {} hodin</li>
                </ul>
            </div>
            """.format(
                'kritické' if high_critical_risk > total_events/3 else 'vysoké',
                'rizikové' if czech_events_count > total_events/2 else 'všechny',
                'reálné' if scraped_count > fallback_count else 'všechny',
                '6' if recent_events > total_events/7 else '24'
            ), unsafe_allow_html=True)
    
    else:
        st.warning("⚠️ Nelze načíst data pro statistiky")

    with tab3:
        # Dodavatelé
        st.markdown("""
        <div style='background-color: #FFF3E0; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
            <h3 style='color: #F57C00; margin-top: 0;'>🏭 Dodavatelé VW Group - Risk Management</h3>
            <p style='margin: 5px 0;'>
                <strong>🎯 Účel:</strong> Sledování dodavatelů VW Group a jejich rizikových profilů<br>
                <strong>📊 Co znamenají sloupce:</strong><br>
                &nbsp;&nbsp;• <strong>Název:</strong> Jméno dodavatele (např. Bosch, Continental)<br>
                &nbsp;&nbsp;• <strong>Kategorie:</strong> Typ dodavatele (Elektronika, Ocel, Plasty...)<br>
                &nbsp;&nbsp;• <strong>Úroveň rizika:</strong> Jak kritické je riziko (Nízké/Střední/Vysoké)<br>
                &nbsp;&nbsp;• <strong>Datum:</strong> Kdy byl dodavatel přidán do systému<br>
                <strong>⚠️ Praktický význam:</strong> Identifikace nejkritičtějších dodavatelů pro VW Group
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    if suppliers:
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
            total_suppliers = len(suppliers)
            st.metric("🏭 Celkem dodavatelů", total_suppliers, help="Celkový počet dodavatelů VW Group")
        
        with col2:
            high_risk_suppliers = len([s for s in suppliers if s.get("risk_level") == "high"])
            risk_percentage = (high_risk_suppliers / total_suppliers * 100) if total_suppliers > 0 else 0
            st.metric("⚠️ Vysoké riziko", f"{high_risk_suppliers} ({risk_percentage:.1f}%)", 
                     delta=f"{risk_percentage:.1f}%", help="Dodavatelé s vysokým rizikem")
        
        with col3:
            categories_count = len(set([s.get("category", "unknown") for s in suppliers]))
            st.metric("🏷️ Kategorie", categories_count, help="Počet různých kategorií dodavatelů")
        
        with col4:
            czech_suppliers_count = getattr(st.session_state, 'czech_suppliers', 0)
            st.metric("🇨🇿 Dodavatelé v ČR", czech_suppliers_count, help="Dodavatelé na území České republiky")
        
        # Rozložení dodavatelů
        st.subheader("📊 Rozložení dodavatelů")
        col1, col2 = st.columns(2)
        
        with col1:
            # Rozložení podle kategorie
            category_counts = df_suppliers['category_cz'].value_counts()
            st.bar_chart(category_counts)
            st.caption("Rozložení podle kategorie")
        
        with col2:
            # Rozložení podle rizika
            risk_counts = df_suppliers['risk_level_cz'].value_counts()
            st.bar_chart(risk_counts)
            st.caption("Rozložení podle úrovně rizika")
        
        # Analýza rizikových dodavatelů
        st.subheader("⚠️ Analýza rizikových dodavatelů")
        col1, col2 = st.columns(2)
        
        with col1:
            # Nejrizikovější kategorie
            high_risk_by_category = df_suppliers[df_suppliers['risk_level'] == 'high']['category_cz'].value_counts()
            if not high_risk_by_category.empty:
                st.bar_chart(high_risk_by_category)
                st.caption("Nejrizikovější kategorie dodavatelů")
        
        with col2:
            # Statistiky rizik
            risk_stats = df_suppliers['risk_level_cz'].value_counts()
            st.pie_chart(risk_stats)
            st.caption("Rozložení podle úrovně rizika")
        
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
        
        # Souhrnné statistiky dodavatelů
        st.subheader("📋 Souhrnné statistiky dodavatelů")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style='background-color: #F5F5F5; padding: 15px; border-radius: 8px;'>
                <h5 style='margin-top: 0;'>📊 Přehled dodavatelů</h5>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Nejčastější kategorie:</strong> {}</li>
                    <li><strong>Průměrná úroveň rizika:</strong> {}</li>
                    <li><strong>Nejrizikovější kategorie:</strong> {}</li>
                    <li><strong>Geografické rozložení:</strong> {}</li>
                </ul>
            </div>
            """.format(
                df_suppliers['category_cz'].mode().iloc[0] if not df_suppliers['category_cz'].empty else 'N/A',
                df_suppliers['risk_level_cz'].mode().iloc[0] if not df_suppliers['risk_level_cz'].empty else 'N/A',
                high_risk_by_category.index[0] if not high_risk_by_category.empty else 'N/A',
                'ČR' if czech_suppliers_count > total_suppliers/2 else 'Celosvětově'
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style='background-color: #E8F5E8; padding: 15px; border-radius: 8px;'>
                <h5 style='margin-top: 0;'>🎯 Doporučení pro dodavatele</h5>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Priorita 1:</strong> Monitorovat {} dodavatele</li>
                    <li><strong>Priorita 2:</strong> Analyzovat {} kategorie</li>
                    <li><strong>Priorita 3:</strong> Kontaktovat {} dodavatele</li>
                    <li><strong>Priorita 4:</strong> Aktualizovat každých {} hodin</li>
                </ul>
            </div>
            """.format(
                'vysoké riziko' if high_risk_suppliers > total_suppliers/3 else 'střední riziko',
                'rizikové' if high_risk_by_category.sum() > total_suppliers/2 else 'všechny',
                'kritické' if high_risk_suppliers > total_suppliers/4 else 'vysoké riziko',
                '6' if high_risk_suppliers > total_suppliers/5 else '24'
            ), unsafe_allow_html=True)
    
    else:
        st.warning("⚠️ Nelze načíst data dodavatelů")

with tab4:
    st.header("ℹ️ O aplikaci")
    
    st.markdown("""
    <div style='background-color: #E8F5E8; padding: 20px; border-radius: 10px; margin-bottom: 20px;'>
        <h3 style='color: #2E7D32; margin-top: 0;'>🎯 Účel aplikace</h3>
        <p style='margin: 10px 0;'>
            <strong>Risk Analyst Dashboard</strong> je komplexní nástroj pro analýzu rizik v dodavatelském řetězci VW Group. 
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
                <h4 style='color: #7B1FA2; margin-top: 0;'>🔵 Reálná data (Scraped)</h4>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>CHMI API:</strong> Hydrologické výstrahy a záplavy</li>
                    <li><strong>RSS feeds:</strong> Novinky.cz, Seznam Zprávy, HN, iRozhlas</li>
                    <li><strong>Význam:</strong> Aktuální rizikové události v reálném čase</li>
                </ul>
            </div>
            <div>
                <h4 style='color: #7B1FA2; margin-top: 0;'>🟡 Demo data (Fallback)</h4>
                <ul style='margin: 5px 0; padding-left: 20px;'>
                    <li><strong>Simulované události:</strong> Záplavy, protesty, dodavatelské problémy</li>
                    <li><strong>VW Group dodavatelé:</strong> Fiktivní dodavatelé s rizikovým hodnocením</li>
                    <li><strong>Význam:</strong> Ukázka funkcionality při nedostupnosti reálných dat</li>
                </ul>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background-color: #E0F2F1; padding: 20px; border-radius: 10px; margin: 20px 0;'>
        <h3 style='color: #00695C; margin-top: 0;'>🎯 Praktické využití pro VW Group</h3>
        <p style='margin: 10px 0;'>
            <strong>Risk Analyst Dashboard</strong> umožňuje VW Group efektivně monitorovat a analyzovat rizika v dodavatelském řetězci:
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
        <p>© 2025 Risk Analyst Dashboard | VW Group</p>
        <p style='font-size: 0.8em;'>
            Vytvořeno jako ukázka technických dovedností pro pozici Risk Analyst
        </p>
    </div>
    """,
    unsafe_allow_html=True
) 