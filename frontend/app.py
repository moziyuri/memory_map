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

# Konstanty aplikace
DEFAULT_LAT = 49.8  # Výchozí zeměpisná šířka (zhruba střed ČR)
DEFAULT_LON = 15.5  # Výchozí zeměpisná délka (zhruba střed ČR)

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
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
</style>
""", unsafe_allow_html=True)

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
    """Vytvoření mapy s rizikovými událostmi a dodavateli"""
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)
    
    # Přidání základní mapové vrstvy
    folium.TileLayer(
        tiles='https://mapserver.mapy.cz/base-m/{z}-{x}-{y}',
        attr='Mapy.cz',
        name='Základní mapa',
        overlay=False
    ).add_to(m)
    
    # Přidání satelitní vrstvy
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite',
        name='Satelitní mapa',
        overlay=False
    ).add_to(m)
    
    # Přidání ovladače vrstev
    folium.LayerControl().add_to(m)
    
    # Barvy pro různé typy událostí
    event_colors = {
        'flood': 'blue',
        'protest': 'red',
        'supply_chain': 'orange',
        'geopolitical': 'purple',
        'manual': 'gray'
    }
    
    # Ikony pro různé závažnosti
    severity_icons = {
        'critical': 'exclamation-triangle',
        'high': 'exclamation-circle',
        'medium': 'info-circle',
        'low': 'check-circle'
    }
    
    # Přidání rizikových událostí
    if events:
        for event in events:
            try:
                lat = float(event.get("latitude", 0))
                lon = float(event.get("longitude", 0))
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                
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
                
                # Popup obsah
                popup_content = f"""
                <div style='width: 300px; padding: 10px; font-family: Arial, sans-serif;'>
                    <h3 style='color: {color}; margin-top: 0;'>{title}</h3>
                    <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>
                        {description}
                    </div>
                    <div style='margin-top: 10px;'>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Typ:</strong> 
                           <span style='background-color: #E3F2FD; padding: 2px 5px; border-radius: 3px;'>{event_type}</span>
                        </p>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Závažnost:</strong> 
                           <span class='risk-{severity}'>{severity}</span>
                        </p>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Zdroj:</strong> {source}</p>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Datum:</strong> {created_at}</p>
                    </div>
                </div>
                """
                
                # Přidání markeru
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f"{title} ({severity})",
                    icon=folium.Icon(icon=icon_name, prefix="fa", color=color)
                ).add_to(m)
                
            except Exception as e:
                print(f"Chyba při zpracování události: {str(e)}")
    
    # Přidání dodavatelů
    if suppliers:
        for supplier in suppliers:
            try:
                lat = float(supplier.get("latitude", 0))
                lon = float(supplier.get("longitude", 0))
                
                # Kontrola, že souřadnice jsou v rozumném rozsahu
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    continue
                
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
                
                # Popup obsah pro dodavatele
                popup_content = f"""
                <div style='width: 300px; padding: 10px; font-family: Arial, sans-serif;'>
                    <h3 style='color: {color}; margin-top: 0;'>🏭 {name}</h3>
                    <div style='margin-top: 10px;'>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Kategorie:</strong> 
                           <span style='background-color: #E3F2FD; padding: 2px 5px; border-radius: 3px;'>{category}</span>
                        </p>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Úroveň rizika:</strong> 
                           <span class='risk-{risk_level}'>{risk_level}</span>
                        </p>
                        <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Datum:</strong> {created_at}</p>
                    </div>
                </div>
                """
                
                # Přidání markeru dodavatele (jiný styl)
                folium.Marker(
                    [lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    tooltip=f"🏭 {name} ({risk_level})",
                    icon=folium.Icon(icon="industry", prefix="fa", color=color)
                ).add_to(m)
                
            except Exception as e:
                print(f"Chyba při zpracování dodavatele: {str(e)}")
    
    return m

# Funkce pro filtrování událostí
def filter_events(events, event_type=None, severity=None, source=None, date_from=None, date_to=None):
    """Filtrování událostí podle zadaných kritérií"""
    filtered_events = events.copy()
    
    if event_type and event_type != "Všechny":
        filtered_events = [e for e in filtered_events if e.get("event_type") == event_type]
    
    if severity and severity != "Všechny":
        filtered_events = [e for e in filtered_events if e.get("severity") == severity]
    
    if source and source != "Všechny":
        filtered_events = [e for e in filtered_events if e.get("source") == source]
    
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
    
    st.info(
        "Dashboard pro analýzu rizik v dodavatelském řetězci VW Group. "
        "Zobrazuje rizikové události, dodavatele a jejich vzájemné vztahy."
    )
    
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
    st.subheader("🔍 Filtry")
    
    # Získání unikátních hodnot pro filtry
    events = get_risk_events()
    suppliers = get_suppliers()
    
    if events:
        event_types = ["Všechny"] + list(set([e.get("event_type", "unknown") for e in events]))
        severities = ["Všechny"] + list(set([e.get("severity", "medium") for e in events]))
        sources = ["Všechny"] + list(set([e.get("source", "unknown") for e in events]))
        
        selected_event_type = st.selectbox("Typ události:", event_types)
        selected_severity = st.selectbox("Závažnost:", severities)
        selected_source = st.selectbox("Zdroj:", sources)
        
        # Datové filtry
        st.subheader("📅 Časové období")
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input("Od:", value=datetime.now().date() - timedelta(days=7))
        with col2:
            date_to = st.date_input("Do:", value=datetime.now().date())
        
        # Tlačítko pro spuštění scraping
        st.subheader("🔄 Aktualizace dat")
        if st.button("Spustit scraping", type="primary"):
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
st.markdown("<h1 class='main-header'>⚠️ VW Group Risk Analyst</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Analýza rizik v dodavatelském řetězci</p>", unsafe_allow_html=True)

# Záložky pro různé části aplikace
tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Mapa rizik", "📊 Statistiky", "🏭 Dodavatelé", "ℹ️ O aplikaci"])

with tab1:
    # Mapa rizik
    st.markdown('<div class="tooltip">🗺️ Mapa rizikových událostí<span class="tooltiptext">Interaktivní mapa zobrazující rizikové události a dodavatele</span></div>', unsafe_allow_html=True)
    
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
        
        st.info(f"📊 Zobrazeno {len(filtered_events)} z {len(events)} událostí")
        
        # Vytvoření a zobrazení mapy
        try:
            m = create_risk_map(filtered_events, suppliers)
            map_data = st_folium(m, width=1200, height=600)
        except Exception as e:
            st.error(f"Chyba při vytváření mapy: {str(e)}")
    else:
        st.error("❌ Nelze načíst rizikové události")

with tab2:
    # Statistiky
    st.header("📊 Statistiky rizik")
    
    if events:
        # Převod na DataFrame pro analýzu
        df_events = pd.DataFrame(events)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Celkem událostí", len(events))
        
        with col2:
            high_risk = len([e for e in events if e.get("severity") in ["high", "critical"]])
            st.metric("Vysoké riziko", high_risk)
        
        with col3:
            flood_events = len([e for e in events if e.get("event_type") == "flood"])
            st.metric("Záplavy", flood_events)
        
        with col4:
            supply_chain = len([e for e in events if e.get("event_type") == "supply_chain"])
            st.metric("Dodavatelský řetězec", supply_chain)
        
        # Grafy
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Rozložení podle typu události")
            event_type_counts = df_events['event_type'].value_counts()
            st.bar_chart(event_type_counts)
        
        with col2:
            st.subheader("Rozložení podle závažnosti")
            severity_counts = df_events['severity'].value_counts()
            st.bar_chart(severity_counts)
        
        # Tabulka s nejnovějšími událostmi
        st.subheader("Nejnovější události")
        if not df_events.empty:
            # Seřazení podle data vytvoření
            df_events['created_at'] = pd.to_datetime(df_events['created_at'])
            latest_events = df_events.sort_values('created_at', ascending=False).head(10)
            
            # Zobrazení pouze relevantních sloupců
            display_columns = ['title', 'event_type', 'severity', 'source', 'created_at']
            st.dataframe(latest_events[display_columns], use_container_width=True)
    else:
        st.warning("⚠️ Nelze načíst data pro statistiky")

with tab3:
    # Dodavatelé
    st.header("🏭 Dodavatelé")
    
    if suppliers:
        # Převod na DataFrame
        df_suppliers = pd.DataFrame(suppliers)
        
        # Metriky dodavatelů
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Celkem dodavatelů", len(suppliers))
        
        with col2:
            high_risk_suppliers = len([s for s in suppliers if s.get("risk_level") == "high"])
            st.metric("Vysoké riziko", high_risk_suppliers)
        
        with col3:
            categories = set([s.get("category", "unknown") for s in suppliers])
            st.metric("Kategorie", len(categories))
        
        # Tabulka dodavatelů
        st.subheader("Seznam dodavatelů")
        if not df_suppliers.empty:
            display_columns = ['name', 'category', 'risk_level', 'created_at']
            st.dataframe(df_suppliers[display_columns], use_container_width=True)
    else:
        st.warning("⚠️ Nelze načíst data dodavatelů")

with tab4:
    st.header("ℹ️ O aplikaci")
    
    st.info("**Risk Analyst Dashboard** je interaktivní aplikace pro analýzu rizik v dodavatelském řetězci VW Group. Byla vytvořena jako ukázka technických dovedností pro pozici Risk Analyst.")
    
    st.subheader("🔍 Funkce")
    st.markdown("""
    - **Interaktivní mapa** s rizikovými událostmi a dodavateli
    - **Filtry** podle typu události, závažnosti, zdroje a času
    - **Statistiky** a analýza rizik
    - **Automatický scraping** z RSS feedů a CHMI API
    - **Vizualizace** vztahů mezi událostmi a dodavateli
    """)
    
    st.subheader("⚙️ Technologie")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Frontend:**")
        st.markdown("- Streamlit")
        st.markdown("- Folium (mapy)")
        st.markdown("- Pandas (analýza)")
    
    with col2:
        st.markdown("**Backend:**")
        st.markdown("- FastAPI")
        st.markdown("- PostgreSQL + PostGIS")
        st.markdown("- Web scraping")
    
    st.subheader("📊 Zdroje dat")
    st.markdown("""
    - **RSS feeds:** Novinky.cz, Seznam Zprávy, Hospodářské noviny, iRozhlas
    - **CHMI API:** Hydrologické výstrahy a záplavy
    - **Demo data:** Simulované rizikové události a dodavatelé
    """)

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