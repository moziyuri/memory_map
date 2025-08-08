"""
Risk Analyst Dashboard
=====================

Moderní dashboard pro analýzu rizik v dodavatelském řetězci.
Zaměřeno na monitoring záplav, dopravních problémů a jejich dopad na dodavatele.
"""

import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
import os

# Konfigurace stránky
st.set_page_config(
    page_title="Risk Analyst Dashboard",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# České hranice pro filtrování dat
CZECH_BOUNDS = {
    'min_lat': 48.5, 'max_lat': 51.1,
    'min_lon': 12.0, 'max_lon': 18.9
}

# Environment variables
BACKEND_URL = os.getenv('BACKEND_URL', 'https://risk-analyst.onrender.com')

# Konzistentní zobrazení hodnot
EVENT_TYPE_LABEL = {
    'flood': 'Povodně',
    'supply_chain': 'Dodavatelský řetězec',
    'weather': 'Počasí'
}

SEVERITY_LABEL = {
    'low': 'Nízká',
    'medium': 'Střední',
    'high': 'Vysoká',
    'critical': 'Kritická'
}

SOURCE_LABEL = {
    'rss': 'Zpravodajství (RSS)',
    'chmi_api': 'ČHMÚ',
    'openmeteo': 'OpenMeteo',
}

def format_dt(value: str) -> str:
    try:
        # Podpora ISO formátu i bez 'T'
        v = value
        if isinstance(v, str):
            if 'T' in v:
                return datetime.fromisoformat(v.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            return v
        return str(v)
    except Exception:
        return str(value)

def is_in_czech_republic(lat, lon):
    """Kontrola, zda bod leží v České republice"""
    return (CZECH_BOUNDS['min_lat'] <= lat <= CZECH_BOUNDS['max_lat'] and
            CZECH_BOUNDS['min_lon'] <= lon <= CZECH_BOUNDS['max_lon'])

def sanitize_coords(lat, lon):
    """Heuristika: pokud bod neleží v ČR, ale prohození dává smysl, prohodíme (častá chyba lat/lon)."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except Exception:
        return lat, lon
    if is_in_czech_republic(lat_f, lon_f):
        return lat_f, lon_f
    # Swap check
    if is_in_czech_republic(lon_f, lat_f):
        return lon_f, lat_f
    return lat_f, lon_f

def test_backend_connection():
    """Test připojení k backendu"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        return response.status_code == 200
    except:
        return False

@st.cache_data(ttl=120)
def get_risk_events():
    """Získání rizikových událostí z API (s cachingem)"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/risks", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_suppliers():
    """Získání dodavatelů z API (s cachingem)"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/suppliers", timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception:
        return []

def get_advanced_analysis(lat: float, lon: float, supplier_id: int | None):
    """Získání pokročilé analýzy pro zadanou lokaci / dodavatele"""
    try:
        flood_data = None
        geo_data = None
        # Simulace záplav (preferujeme vybraného dodavatele)
        if supplier_id:
            resp = requests.get(
                f"{BACKEND_URL}/api/analysis/river-flood-simulation",
                params={"supplier_id": supplier_id, "flood_level_m": 2.0},
                timeout=25,
            )
            if resp.status_code == 200:
                flood_data = resp.json()
        else:
            # Bez dodavatele provedeme lehčí geografickou analýzu pouze podle souřadnic
            resp = requests.get(
                f"{BACKEND_URL}/api/analysis/geographic-risk-assessment",
                params={"lat": lat, "lon": lon, "radius_km": 50},
                timeout=25,
            )
            if resp.status_code == 200:
                geo_data = resp.json()
        return flood_data, geo_data
    except Exception:
        return None, None

def create_risk_map(events, suppliers, flood_data=None, geo_data=None):
    """Vytvoření interaktivní mapy rizik"""
    
    # Centrum mapy na Českou republiku
    center_lat, center_lon = 49.8175, 15.4730
    zoom_start = 8
    
    # Vytvoření mapy
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_start,
        tiles='OpenStreetMap'
    )
    
    # Přidání satelitní vrstvy
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satelitní mapa',
        overlay=False
    ).add_to(m)
    
    # Přidání OpenStreetMap vrstvy
    folium.TileLayer(
        tiles='OpenStreetMap',
        name='OpenStreetMap',
        overlay=False
    ).add_to(m)
    
    # Přidání dodavatelů (modré značky) s clusteringem
    supplier_group = folium.FeatureGroup(name="🏭 Dodavatelé", show=True)
    supplier_cluster = MarkerCluster(name="🏭 Dodavatelé - cluster", show=True)
    
    for supplier in suppliers:
        if supplier.get('latitude') and supplier.get('longitude'):
            lat, lon = sanitize_coords(supplier['latitude'], supplier['longitude'])
            if not is_in_czech_republic(lat, lon):
                continue
            
            # Barva podle úrovně rizika
            risk_colors = {'low': 'green', 'medium': 'orange', 'high': 'red', 'critical': 'darkred'}
            color = risk_colors.get(supplier.get('risk_level', 'medium'), 'blue')
            
            popup_content = f"""
            <div style='width: 250px;'>
                <h4>🏭 {supplier['name']}</h4>
                <p><strong>Kategorie:</strong> {supplier.get('category', 'Neznámé')}</p>
                <p><strong>Úroveň rizika:</strong> {supplier.get('risk_level', 'Neznámé')}</p>
                <p><strong>Přidáno:</strong> {format_dt(supplier.get('created_at', 'Neznámé'))}</p>
                <p><strong>Souřadnice:</strong> {lat:.4f}, {lon:.4f}</p>
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color=color, icon='industry', prefix='fa'),
                tooltip=f"🏭 {supplier['name']} ({supplier.get('risk_level', 'N/A')})"
            ).add_to(supplier_cluster)
    
    supplier_cluster.add_to(supplier_group)
    supplier_group.add_to(m)
    
    # Přidání rizikových událostí (červené značky) s clusteringem
    event_group = folium.FeatureGroup(name="⚠️ Rizikové události", show=True)
    event_cluster = MarkerCluster(name="⚠️ Události - cluster", show=True)
    
    for event in events:
        if event.get('latitude') and event.get('longitude'):
            lat, lon = sanitize_coords(event['latitude'], event['longitude'])
            if not is_in_czech_republic(lat, lon):
                continue
            
            # Barva podle závažnosti
            severity_colors = {'low': 'green', 'medium': 'orange', 'high': 'red', 'critical': 'darkred'}
            color = severity_colors.get(event.get('severity', 'medium'), 'orange')
            
            # Vylepšený popup s odkazem na zdroj
            source_link = ""
            if event.get('url'):
                source_link = f"<p><strong>Zdroj:</strong> <a href='{event['url']}' target='_blank'>Otevřít zdroj</a></p>"
            
            popup_content = f"""
            <div style='width: 250px;'>
                <h4>⚠️ {event['title']}</h4>
                <p><strong>Typ:</strong> {EVENT_TYPE_LABEL.get(event.get('event_type'), event.get('event_type','Neznámé'))}</p>
                <p><strong>Závažnost:</strong> {SEVERITY_LABEL.get(event.get('severity'), event.get('severity','Neznámé'))}</p>
                <p><strong>Datum:</strong> {format_dt(event.get('created_at', 'Neznámé'))}</p>
                <p><strong>Popis:</strong> {event.get('description', 'Bez popisu')}</p>
                <p><strong>Zdroj dat:</strong> {SOURCE_LABEL.get(event.get('source'), event.get('source','Neznámé'))}</p>
                <p><strong>Souřadnice:</strong> {lat:.4f}, {lon:.4f}</p>
                {source_link}
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color=color, icon='exclamation-triangle', prefix='fa'),
                tooltip=f"⚠️ {event['title'][:30]}..."
            ).add_to(event_cluster)
    
    event_cluster.add_to(event_group)
    event_group.add_to(m)
    
    # Přidání legendy
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 120px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px">
    <p><strong>🗺️ Legenda</strong></p>
    <p>🏭 <b>Dodavatelé:</b></p>
    <p>&nbsp;&nbsp;🟢 Nízké riziko</p>
    <p>&nbsp;&nbsp;🟠 Střední riziko</p>
    <p>&nbsp;&nbsp;🔴 Vysoké riziko</p>
    <p>&nbsp;&nbsp;⚫ Kritické riziko</p>
    <p>⚠️ <b>Události:</b></p>
    <p>&nbsp;&nbsp;🔴 Červené značky</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Přidání ovládání vrstev
    folium.LayerControl().add_to(m)
    
    # Pokus o přizpůsobení výřezu mapy na zobrazené objekty
    try:
        bounds = []
        for e in events:
            if e.get('latitude') and e.get('longitude'):
                lat, lon = sanitize_coords(e['latitude'], e['longitude'])
                if is_in_czech_republic(lat, lon):
                    bounds.append([lat, lon])
        for s in suppliers:
            if s.get('latitude') and s.get('longitude'):
                lat, lon = sanitize_coords(s['latitude'], s['longitude'])
                if is_in_czech_republic(lat, lon):
                    bounds.append([lat, lon])
        if bounds:
            m.fit_bounds(bounds, padding=(20, 20))
    except Exception:
        pass
    return m

def get_consistent_statistics(events, suppliers):
    """Získání konzistentních statistik pouze pro data v ČR"""
    czech_events = [e for e in events if e.get('latitude') and e.get('longitude') and 
                    is_in_czech_republic(e['latitude'], e['longitude'])]
    
    czech_suppliers = [s for s in suppliers if s.get('latitude') and s.get('longitude') and 
                       is_in_czech_republic(s['latitude'], s['longitude'])]
    
    return {
        'total_events': len(czech_events),
        'czech_events': len(czech_events),
        'total_suppliers': len(czech_suppliers),
        'czech_suppliers': len(czech_suppliers),
        'high_risk_suppliers': len([s for s in czech_suppliers if s.get('risk_level') in ['high', 'critical']]),
        'high_risk_percentage': len([s for s in czech_suppliers if s.get('risk_level') in ['high', 'critical']]) / len(czech_suppliers) * 100 if czech_suppliers else 0
    }

# Hlavní aplikace
def main():
    # Header
    st.title("⚠️ Risk Analyst Dashboard")
    st.markdown("**Moderní monitoring rizik v dodavatelském řetězci**")
    
    # Sidebar
    st.sidebar.header("🔧 Ovládání")
    
    # Test připojení
    if test_backend_connection():
        st.sidebar.success("✅ Backend připojen")
    else:
        st.sidebar.error("❌ Backend nedostupný")
        st.error("⚠️ Aplikace nemůže načíst data. Zkontrolujte připojení k backendu.")
        return
    
    # Filtry
    st.sidebar.subheader("🔍 Filtry")
    show_only_cz = st.sidebar.toggle("Filtrovat pouze na ČR", value=False)
    
    # Typ události
    event_types = ["Všechny", "flood", "supply_chain"]
    selected_event_type_label = st.sidebar.selectbox(
        "📊 Typ události:", ["Všechny", "Povodně", "Dodavatelský řetězec"]
    )
    selected_event_type = {
        "Všechny": "Všechny",
        "Povodně": "flood",
        "Dodavatelský řetězec": "supply_chain",
    }[selected_event_type_label]
    
    # Závažnost
    severity_levels = ["Všechny", "Nízká", "Střední", "Vysoká", "Kritická"]
    selected_severity_label = st.sidebar.selectbox("⚠️ Závažnost:", severity_levels)
    severity_reverse = {
        "Všechny": "Všechny",
        "Nízká": "low",
        "Střední": "medium",
        "Vysoká": "high",
        "Kritická": "critical",
    }
    selected_severity = severity_reverse[selected_severity_label]
    
    # Načtení dat
    events = get_risk_events()
    suppliers = get_suppliers()
    # Rychlé info do sidebaru pro diagnostiku
    st.sidebar.caption(f"Načteno z API: události={len(events)}, dodavatelé={len(suppliers)}")
    
    # Filtrování dat (typ/závažnost)
    filtered_events = events
    if selected_event_type != "Všechny":
        filtered_events = [e for e in events if e.get('event_type') == selected_event_type]
    
    if selected_severity != "Všechny":
        filtered_events = [e for e in filtered_events if e.get('severity') == selected_severity]
    
    # Volitelné filtrování pouze pro ČR (default: vypnuto => zobrazíme vše)
    if show_only_cz:
        display_events = [e for e in filtered_events if e.get('latitude') and e.get('longitude') and 
                          is_in_czech_republic(e['latitude'], e['longitude'])]
        display_suppliers = [s for s in suppliers if s.get('latitude') and s.get('longitude') and 
                             is_in_czech_republic(s['latitude'], s['longitude'])]
    else:
        display_events = filtered_events
        display_suppliers = suppliers
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Mapa rizik", "📰 Scraping", "🏭 Dodavatelé", "🔬 Pokročilá analýza", "ℹ️ O aplikaci"])
    
    # Tab 1: Mapa rizik
    with tab1:
        st.header("🗺️ Mapa rizik")
        
        # Statistiky vzhledem k zobrazeným datům
        stats = get_consistent_statistics(display_events if show_only_cz else display_events, 
                                          display_suppliers if show_only_cz else display_suppliers)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Události (zobrazené)", len(display_events))
        with col2:
            st.metric("🏭 Dodavatelé (zobrazení)", len(display_suppliers))
        with col3:
            st.metric("⚠️ Vysoké riziko", f"{stats['high_risk_suppliers']} ({stats['high_risk_percentage']:.1f}%)")
        with col4:
            st.metric("🌍 Celkem bodů na mapě", len(display_events) + len(display_suppliers))
            st.info(f"📊 Zobrazeno: {len(display_events)} událostí + {len(display_suppliers)} dodavatelů")
        
        # Mapa
        if display_events or display_suppliers:
            risk_map = create_risk_map(display_events, display_suppliers)
            folium_static(risk_map, width=1200, height=600)
        else:
            st.info("📝 Na mapě nejsou zobrazena žádná data v České republice.")
    
    # Tab 2: Scraping
    with tab2:
        st.header("📰 Automatický scraping")
        
        st.info("""
        **Jak funguje scraping:**
        
        🔍 **CHMI API (počasí):** Monitoruje meteorologické výstrahy a extrémní počasí
        📰 **RSS feeds (česká média):** Sleduje zprávy o záplavách a dopravních problémech
        
        **Výsledek:** Automatické vytvoření rizikových událostí v databázi
        """)
        
        # Tlačítko pro spuštění scrapingu
        if st.button("🔄 Spustit scraping", type="primary"):
            try:
                with st.spinner("🔍 Probíhá scraping..."):
                    response = requests.get(f"{BACKEND_URL}/api/scrape/run-all", timeout=60)
                    
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Scraping dokončen!")
                    
                    # Zobrazení výsledků s lepším error handlingem
                    if 'results' in result:
                        results = result['results']
                        
                        # CHMI výsledky
                        if 'chmi' in results and results['chmi']:
                            chmi_result = results['chmi']
                            if chmi_result.get('status') == 'success':
                                st.info(f"🌤️ CHMI (počasí): {chmi_result.get('saved_count', 0)} nových událostí")
                            else:
                                st.warning(f"⚠️ CHMI: {chmi_result.get('error', 'Neznámá chyba')}")
                        
                        # RSS výsledky
                        if 'rss' in results and results['rss']:
                            rss_result = results['rss']
                            if rss_result.get('status') == 'success':
                                st.info(f"📰 RSS (média): {rss_result.get('saved_count', 0)} nových událostí")
                            else:
                                st.warning(f"⚠️ RSS: {rss_result.get('error', 'Neznámá chyba')}")
                        
                        # Testovací data
                        if 'test_data_created' in results and results['test_data_created'] > 0:
                            st.info(f"📝 Vytvořena testovací data: {results['test_data_created']} událostí")
                        
                        # Celkový součet
                        total_saved = results.get('total_events_saved', 0)
                        if total_saved > 0:
                            st.success(f"✅ Celkem uloženo: {total_saved} událostí")
                        else:
                            st.warning("⚠️ Nebyly nalezeny žádné nové události")
                    
                    # Tlačítko pro obnovení zobrazení
                    if st.button("🔄 Obnovit zobrazení"):
                        st.rerun()
                        
                else:
                    st.error(f"❌ Chyba při scrapingu: {response.status_code}")
                    st.error(f"Odpověď: {response.text[:200]}")
            except Exception as e:
                st.error(f"❌ Chyba: {str(e)}")
        
        # Zobrazení nejnovějších událostí
        if display_events:
            st.subheader("📋 Nejnovější události")
            
            # Vytvoření DataFrame
            events_data = []
            for event in display_events[:10]:  # Pouze posledních 10
                events_data.append({
                    'Název': event.get('title', 'Bez názvu'),
                    'Typ': EVENT_TYPE_LABEL.get(event.get('event_type'), event.get('event_type','Neznámé')),
                    'Závažnost': SEVERITY_LABEL.get(event.get('severity'), event.get('severity','Neznámé')),
                    'Zdroj': SOURCE_LABEL.get(event.get('source'), event.get('source','Neznámé')),
                    'Datum': format_dt(event.get('created_at', 'Neznámé'))
                })
            
            if events_data:
                df_events = pd.DataFrame(events_data)
                st.dataframe(df_events, use_container_width=True)
            else:
                st.info("📝 Žádné události k zobrazení.")
        else:
            st.info("📝 Žádné události k zobrazení.")
    
    # Tab 3: Dodavatelé
    with tab3:
        st.header("🏭 Dodavatelé")
        
        if display_suppliers:
            # Klíčové metriky
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏭 Zobrazení dodavatelé", len(display_suppliers))
            with col2:
                st.metric("⚠️ Vysoké riziko", f"{stats['high_risk_suppliers']} ({stats['high_risk_percentage']:.1f}%)")
            with col3:
                st.metric("🇨🇿 Filtrování ČR", "Zapnuto" if show_only_cz else "Vypnuto")
            
            # Tabulka dodavatelů
            st.subheader("📋 Seznam dodavatelů")
            
            suppliers_data = []
            for supplier in display_suppliers:
                suppliers_data.append({
                    'Název dodavatele': supplier.get('name', 'Bez názvu'),
                    'Kategorie': supplier.get('category', 'Neznámé'),
                    'Úroveň rizika': supplier.get('risk_level', 'Neznámé'),
                    'Latitude': supplier.get('latitude'),
                    'Longitude': supplier.get('longitude'),
                    'Datum přidání': format_dt(supplier.get('created_at', 'Neznámé'))
                })
            
            if suppliers_data:
                df_suppliers = pd.DataFrame(suppliers_data)
                st.dataframe(df_suppliers, use_container_width=True)
            else:
                st.info("📝 Žádní dodavatelé k zobrazení.")
        else:
            # Debug: pokud API vrátilo nějaké dodavatele, ale žádný neprošel CZ filtrem, nabídneme zobrazení všech
            if suppliers:
                st.warning("⚠️ Žádní dodavatelé v rámci hranic ČR po aplikaci filtru.")
                if st.toggle("Zobrazit dodavatele bez filtru ČR"):
                    suppliers_data = []
                    for supplier in suppliers:
                        suppliers_data.append({
                            'Název dodavatele': supplier.get('name', 'Bez názvu'),
                            'Kategorie': supplier.get('category', 'Neznámé'),
                            'Úroveň rizika': supplier.get('risk_level', 'Neznámé'),
                            'Latitude': supplier.get('latitude'),
                            'Longitude': supplier.get('longitude'),
                            'Datum přidání': format_dt(supplier.get('created_at', 'Neznámé'))
                        })
                    if suppliers_data:
                        df_suppliers = pd.DataFrame(suppliers_data)
                        st.dataframe(df_suppliers, use_container_width=True)
            else:
                st.info("📝 Žádní dodavatelé k zobrazení.")
    
    # Tab 4: Pokročilá analýza
    with tab4:
        st.header("🔬 Pokročilá analýza")
        
        st.info("""
        **Dostupné analytické nástroje:**
        
        🌊 **Simulace záplav:** Analýza rizika záplav pro dodavatele na základě vzdálenosti od řek
        🗺️ **Geografická analýza:** Komplexní posouzení rizik pro libovolnou lokaci
        """)
        
        # Ovládání pro analýzu: volba dodavatele / souřadnic
        st.subheader("🎯 Parametry analýzy")
        colp1, colp2 = st.columns(2)
        with colp1:
            supplier_names = [s.get('name') for s in suppliers]
            selected_supplier = st.selectbox("Vyberte dodavatele (volitelné)", ["— žádný —"] + supplier_names)
            supplier_id = None
            if selected_supplier != "— žádný —":
                for s in suppliers:
                    if s.get('name') == selected_supplier:
                        supplier_id = s.get('id')
                        lat_default, lon_default = s.get('latitude'), s.get('longitude')
                        break
            else:
                lat_default, lon_default = 50.0755, 14.4378  # Praha
        with colp2:
            lat = st.number_input("Latitude", value=float(lat_default), format="%.6f")
            lon = st.number_input("Longitude", value=float(lon_default), format="%.6f")

        run_analysis = st.button("🔬 Spustit analýzu", type="primary")
        flood_data = geo_data = None
        if run_analysis:
            flood_data, geo_data = get_advanced_analysis(lat, lon, supplier_id)
        
        # Simulace záplav
        st.subheader("🌊 Simulace záplav")

        if flood_data and flood_data.get('flood_analysis'):
            # Hromadná analýza (seznam)
            st.markdown("**📊 Top 3 nejohroženější dodavatelé:**")
            items = flood_data.get('flood_analysis') or []
            for i, analysis in enumerate(items[:3], 1):
                supplier_info = analysis.get('supplier', {}) or {}
                supplier_name = supplier_info.get('name', 'Neznámý dodavatel')
                with st.expander(f"#{i} {supplier_name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        flood_risk = analysis.get('flood_risk', {}) or {}
                        probability = flood_risk.get('probability', 0)
                        nearest_river = flood_risk.get('nearest_river_name', 'Neznámá')
                        river_distance = flood_risk.get('river_distance_km', 0)
                        impact_level = flood_risk.get('impact_level', 'Neznámé')
                        st.metric("Pravděpodobnost záplav", f"{probability:.0%}")
                        st.metric("Nejbližší řeka", nearest_river)
                    with col2:
                        st.metric("Vzdálenost od řeky", f"{river_distance:.1f} km")
                        st.metric("Úroveň rizika", impact_level)
        elif flood_data and flood_data.get('supplier'):
            # Detail pro jednoho dodavatele
            supplier_info = flood_data.get('supplier') or {}
            supplier_name = supplier_info.get('name', 'Neznámý dodavatel')
            flood_risk = flood_data.get('flood_simulation', {}) or {}
            st.markdown(f"**📌 {supplier_name}**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Pravděpodobnost záplav", f"{flood_risk.get('probability', 0):.0%}")
                st.metric("Nejbližší řeka", flood_risk.get('nearest_river_name', 'Neznámá'))
            with col2:
                st.metric("Vzdálenost od řeky", f"{flood_risk.get('river_distance_km', 0):.1f} km")
                st.metric("Úroveň rizika", flood_risk.get('impact_level', 'Neznámé'))
        else:
            st.info("ℹ️ Pro simulaci zvolte konkrétního dodavatele nebo zkuste analyzovat podle souřadnic v sekci Geografická analýza.")
        
        # Geografická analýza
        st.subheader("🗺️ Geografická analýza")
        
        if geo_data and geo_data.get('combined_risk_assessment') is not None:
            # Umožníme jak list, tak dict
            assess = geo_data.get('combined_risk_assessment')
            items = []
            if isinstance(assess, list):
                items = assess[:3]
            elif isinstance(assess, dict):
                # pokud má klíč 'items'
                if isinstance(assess.get('items'), list):
                    items = assess['items'][:3]
                else:
                    items = [assess]
            st.markdown("**📊 Top výsledky geografické analýzy:**")
            for i, analysis in enumerate(items, 1):
                risk_score = analysis.get('risk_score', 0)
                with st.expander(f"#{i} Risk Score: {risk_score:.1f}%"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Risk Score", f"{risk_score:.1f}%")
                        st.metric("Vzdálenost od řeky", f"{analysis.get('river_distance_km', 0):.1f} km")
                    with col2:
                        st.metric("Nadmořská výška", f"{analysis.get('elevation_m', 0):.0f} m")
                        st.metric("Historické události", analysis.get('historical_events', 0))
                    st.info(f"💡 **Doporučení:** {analysis.get('recommendation', 'Neznámé')}")
        else:
            st.info("ℹ️ Zadejte souřadnice (lat/lon) a spusťte analýzu pro zobrazení výsledků.")
    
    # Tab 5: O aplikaci
    with tab5:
        st.header("ℹ️ O aplikaci")
        
        st.markdown("""
        ## 🎯 Účel aplikace
        
        **Risk Analyst Dashboard** je moderní nástroj pro monitoring a analýzu rizik v dodavatelském řetězci.
        
        ### 🚀 Klíčové funkce
        
        • **🗺️ Interaktivní mapa rizik** - Vizualizace událostí a dodavatelů v ČR
        • **📰 Automatický scraping** - Monitoring CHMI a RSS feedů
        • **🏭 Správa dodavatelů** - Přehled dodavatelů s hodnocením rizik
        • **🔬 Pokročilá analýza** - Simulace záplav a geografická analýza
        • **📊 Real-time monitoring** - Aktuální data z různých zdrojů
        
        ### 💼 Praktické využití
        
        • **Identifikace rizikových oblastí** - Monitoring záplav a dopravních problémů
        • **Hodnocení dodavatelů** - Analýza rizik podle lokace a kategorie
        • **Preventivní opatření** - Včasné varování před možnými problémy
        • **Strategické plánování** - Výběr bezpečných lokalit pro nové dodavatele
        
        ### 🔍 Filtry a jejich význam
        
        **📊 Typ události:** Kategorie rizikových událostí (záplavy, dodavatelský řetězec)
        **⚠️ Závažnost:** Úroveň rizika od nízké po kritické
        **📅 Časové období:** Filtrování podle data události
        
        ### 🛠️ Technologie
        
        • **Frontend:** Streamlit (Python)
        • **Backend:** FastAPI (Python)
        • **Databáze:** PostgreSQL s PostGIS
        • **Deployment:** Render.com (backend) + Streamlit Cloud (frontend)
        • **Mapy:** Folium (OpenStreetMap, Satelitní)
        
        ### 📈 Vývoj
        
        Aplikace je neustále vyvíjena a vylepšována na základě zpětné vazby a nových požadavků.
        """)
        
        st.markdown("---")
        st.markdown("© 2025 Risk Analyst Dashboard · Backend: risk-analyst.onrender.com · Frontend: aktuální stránka")

if __name__ == "__main__":
    main() 