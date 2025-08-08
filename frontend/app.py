"""
Risk Analyst Dashboard
=====================

Moderní dashboard pro analýzu rizik v dodavatelském řetězci.
Zaměřeno na monitoring záplav, dopravních problémů a jejich dopad na dodavatele.
"""

import streamlit as st
import folium
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
BACKEND_URL = os.getenv('BACKEND_URL', 'https://risk-analyst-backend.onrender.com')

def is_in_czech_republic(lat, lon):
    """Kontrola, zda bod leží v České republice"""
    return (CZECH_BOUNDS['min_lat'] <= lat <= CZECH_BOUNDS['max_lat'] and
            CZECH_BOUNDS['min_lon'] <= lon <= CZECH_BOUNDS['max_lon'])

def test_backend_connection():
    """Test připojení k backendu"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=10)
        return response.status_code == 200
    except:
        return False

def get_risk_events():
    """Získání rizikových událostí z API"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/risks", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.sidebar.error(f"❌ Chyba při načítání událostí: {response.status_code}")
            return []
    except Exception as e:
        st.sidebar.error(f"❌ Chyba připojení k API: {str(e)}")
        return []

def get_suppliers():
    """Získání dodavatelů z API"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/suppliers", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.sidebar.error(f"❌ Chyba při načítání dodavatelů: {response.status_code}")
            return []
    except Exception as e:
        st.sidebar.error(f"❌ Chyba připojení k API: {str(e)}")
        return []

def get_advanced_analysis():
    """Získání pokročilé analýzy"""
    try:
        # Simulace záplav
        flood_response = requests.get(f"{BACKEND_URL}/api/analysis/river-flood-simulation", timeout=10)
        flood_data = flood_response.json() if flood_response.status_code == 200 else None
        
        # Geografická analýza
        geo_response = requests.get(f"{BACKEND_URL}/api/analysis/geographic-risk-assessment", timeout=10)
        geo_data = geo_response.json() if geo_response.status_code == 200 else None
        
        return flood_data, geo_data
    except Exception as e:
        st.sidebar.error(f"❌ Chyba při pokročilé analýze: {str(e)}")
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
    
    # Přidání dodavatelů (modré značky)
    for supplier in suppliers:
        if supplier.get('location') and is_in_czech_republic(supplier['location']['coordinates'][1], supplier['location']['coordinates'][0]):
            lat = supplier['location']['coordinates'][1]
            lon = supplier['location']['coordinates'][0]
            
            # Barva podle úrovně rizika
            risk_colors = {'low': 'green', 'medium': 'orange', 'high': 'red', 'critical': 'darkred'}
            color = risk_colors.get(supplier.get('risk_level', 'medium'), 'blue')
            
            popup_content = f"""
            <div style='width: 250px;'>
                <h4>🏭 {supplier['name']}</h4>
                <p><strong>Kategorie:</strong> {supplier.get('category', 'Neznámé')}</p>
                <p><strong>Úroveň rizika:</strong> {supplier.get('risk_level', 'Neznámé')}</p>
                <p><strong>Přidáno:</strong> {supplier.get('created_at', 'Neznámé')}</p>
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color=color, icon='industry', prefix='fa'),
                tooltip=f"🏭 {supplier['name']}"
            ).add_to(m)
    
    # Přidání rizikových událostí (červené značky)
    for event in events:
        if event.get('location') and is_in_czech_republic(event['location']['coordinates'][1], event['location']['coordinates'][0]):
            lat = event['location']['coordinates'][1]
            lon = event['location']['coordinates'][0]
            
            # Barva podle závažnosti
            severity_colors = {'low': 'lightred', 'medium': 'red', 'high': 'darkred', 'critical': 'black'}
            color = severity_colors.get(event.get('severity', 'medium'), 'red')
            
            popup_content = f"""
            <div style='width: 250px;'>
                <h4>⚠️ {event['title']}</h4>
                <p><strong>Typ:</strong> {event.get('event_type', 'Neznámé')}</p>
                <p><strong>Závažnost:</strong> {event.get('severity', 'Neznámé')}</p>
                <p><strong>Zdroj:</strong> {event.get('source', 'Neznámé')}</p>
                <p><strong>Datum:</strong> {event.get('created_at', 'Neznámé')}</p>
                <p><strong>Popis:</strong> {event.get('description', 'Bez popisu')}</p>
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color=color, icon='exclamation-triangle', prefix='fa'),
                tooltip=f"⚠️ {event['title'][:30]}..."
            ).add_to(m)
    
    # Přidání výsledků pokročilé analýzy
    if flood_data and flood_data.get('flood_analysis'):
        for analysis in flood_data['flood_analysis'][:3]:  # Pouze top 3
            if analysis.get('supplier_location'):
                lat = analysis['supplier_location']['lat']
                lon = analysis['supplier_location']['lon']
                
                popup_content = f"""
                <div style='width: 250px;'>
                    <h4>🌊 Simulace záplav</h4>
                    <p><strong>Dodavatel:</strong> {analysis.get('supplier_name', 'Neznámé')}</p>
                    <p><strong>Pravděpodobnost:</strong> {analysis.get('flood_probability', 0):.1%}</p>
                    <p><strong>Nejbližší řeka:</strong> {analysis.get('nearest_river_name', 'Neznámá')}</p>
                    <p><strong>Vzdálenost:</strong> {analysis.get('river_distance_km', 0):.1f} km</p>
                    <p><strong>Úroveň rizika:</strong> {analysis.get('impact_level', 'Neznámé')}</p>
                </div>
                """
                
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=folium.Icon(color='red', icon='tint', prefix='fa'),
                    tooltip=f"🌊 {analysis.get('supplier_name', 'Simulace záplav')}"
                ).add_to(m)
    
    if geo_data and geo_data.get('combined_risk_assessment'):
        for analysis in geo_data['combined_risk_assessment'][:3]:  # Pouze top 3
            if analysis.get('location'):
                lat = analysis['location']['lat']
                lon = analysis['location']['lon']
                
                # Barva podle risk score
                risk_score = analysis.get('risk_score', 0)
                if risk_score > 70:
                    color = 'darkred'
                elif risk_score > 40:
                    color = 'red'
                elif risk_score > 20:
                    color = 'orange'
                else:
                    color = 'green'
                
                popup_content = f"""
                <div style='width: 250px;'>
                    <h4>🗺️ Geografická analýza</h4>
                    <p><strong>Risk Score:</strong> {risk_score:.1f}%</p>
                    <p><strong>Vzdálenost od řeky:</strong> {analysis.get('river_distance_km', 0):.1f} km</p>
                    <p><strong>Nadmořská výška:</strong> {analysis.get('elevation_m', 0):.0f} m</p>
                    <p><strong>Historické události:</strong> {analysis.get('historical_events', 0)}</p>
                    <p><strong>Doporučení:</strong> {analysis.get('recommendation', 'Neznámé')}</p>
                </div>
                """
                
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_content, max_width=300),
                    icon=folium.Icon(color=color, icon='map-marker', prefix='fa'),
                    tooltip=f"🗺️ Risk Score: {risk_score:.1f}%"
                ).add_to(m)
    
    # Přidání ovládání vrstev
    folium.LayerControl().add_to(m)
    
    return m

def get_consistent_statistics(events, suppliers):
    """Získání konzistentních statistik pouze pro data v ČR"""
    czech_events = [e for e in events if e.get('location') and 
                    is_in_czech_republic(e['location']['coordinates'][1], e['location']['coordinates'][0])]
    
    czech_suppliers = [s for s in suppliers if s.get('location') and 
                       is_in_czech_republic(s['location']['coordinates'][1], s['location']['coordinates'][0])]
    
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
    
    # Typ události
    event_types = ["Všechny", "flood", "supply_chain"]
    selected_event_type = st.sidebar.selectbox("📊 Typ události:", event_types)
    
    # Závažnost
    severity_levels = ["Všechny", "low", "medium", "high", "critical"]
    selected_severity = st.sidebar.selectbox("⚠️ Závažnost:", severity_levels)
    
    # Časové období
    time_periods = ["Všechny", "Dnes", "Poslední týden", "Poslední měsíc"]
    selected_period = st.sidebar.selectbox("📅 Časové období:", time_periods)
    
    # Načtení dat
    events = get_risk_events()
    suppliers = get_suppliers()
    
    # Filtrování dat
    filtered_events = events
    if selected_event_type != "Všechny":
        filtered_events = [e for e in events if e.get('event_type') == selected_event_type]
    
    if selected_severity != "Všechny":
        filtered_events = [e for e in filtered_events if e.get('severity') == selected_severity]
    
    # Filtrování pouze pro ČR
    czech_events = [e for e in filtered_events if e.get('location') and 
                    is_in_czech_republic(e['location']['coordinates'][1], e['location']['coordinates'][0])]
    
    czech_suppliers = [s for s in suppliers if s.get('location') and 
                       is_in_czech_republic(s['location']['coordinates'][1], s['location']['coordinates'][0])]
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🗺️ Mapa rizik", "📰 Scraping", "🏭 Dodavatelé", "🔬 Pokročilá analýza", "ℹ️ O aplikaci"])
    
    # Tab 1: Mapa rizik
    with tab1:
        st.header("🗺️ Mapa rizik")
        
        # Statistiky
        stats = get_consistent_statistics(czech_events, czech_suppliers)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Události v ČR", stats['czech_events'])
        with col2:
            st.metric("🏭 Dodavatelé v ČR", stats['czech_suppliers'])
        with col3:
            st.metric("⚠️ Vysoké riziko", f"{stats['high_risk_suppliers']} ({stats['high_risk_percentage']:.1f}%)")
        with col4:
            st.metric("🌍 Celkem bodů na mapě", len(czech_events) + len(czech_suppliers))
        
        # Mapa
        if czech_events or czech_suppliers:
            risk_map = create_risk_map(czech_events, czech_suppliers)
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
                response = requests.post(f"{BACKEND_URL}/api/scrape", timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Scraping dokončen!")
                    
                    # Zobrazení výsledků
                    if 'chmi_events' in result:
                        st.info(f"🌤️ CHMI (počasí): {len(result['chmi_events'])} nových událostí")
                    
                    if 'rss_events' in result:
                        st.info(f"📰 RSS (média): {len(result['rss_events'])} nových událostí")
                    
                    st.rerun()
                else:
                    st.error(f"❌ Chyba při scrapingu: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Chyba: {str(e)}")
        
        # Zobrazení nejnovějších událostí
        if czech_events:
            st.subheader("📋 Nejnovější události")
            
            # Vytvoření DataFrame
            events_data = []
            for event in czech_events[:10]:  # Pouze posledních 10
                events_data.append({
                    'Název': event.get('title', 'Bez názvu'),
                    'Typ': event.get('event_type', 'Neznámé'),
                    'Závažnost': event.get('severity', 'Neznámé'),
                    'Zdroj': event.get('source', 'Neznámé'),
                    'Datum': event.get('created_at', 'Neznámé')
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
        
        if czech_suppliers:
            # Klíčové metriky
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🏭 Celkem dodavatelů", stats['czech_suppliers'])
            with col2:
                st.metric("⚠️ Vysoké riziko", f"{stats['high_risk_suppliers']} ({stats['high_risk_percentage']:.1f}%)")
            with col3:
                st.metric("🇨🇿 V ČR", stats['czech_suppliers'])
            
            # Tabulka dodavatelů
            st.subheader("📋 Seznam dodavatelů")
            
            suppliers_data = []
            for supplier in czech_suppliers:
                suppliers_data.append({
                    'Název dodavatele': supplier.get('name', 'Bez názvu'),
                    'Kategorie': supplier.get('category', 'Neznámé'),
                    'Úroveň rizika': supplier.get('risk_level', 'Neznámé'),
                    'Datum přidání': supplier.get('created_at', 'Neznámé')
                })
            
            if suppliers_data:
                df_suppliers = pd.DataFrame(suppliers_data)
                st.dataframe(df_suppliers, use_container_width=True)
            else:
                st.info("📝 Žádní dodavatelé k zobrazení.")
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
        
        # Získání dat pro pokročilou analýzu
        flood_data, geo_data = get_advanced_analysis()
        
        # Simulace záplav
        st.subheader("🌊 Simulace záplav")
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
        
        if flood_data and flood_data.get('flood_analysis'):
            # Zobrazení top 3 výsledků
            st.markdown("**📊 Top 3 nejohroženější dodavatelé:**")
            
            for i, analysis in enumerate(flood_data['flood_analysis'][:3], 1):
                with st.expander(f"#{i} {analysis.get('supplier_name', 'Neznámý dodavatel')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Pravděpodobnost záplav", f"{analysis.get('flood_probability', 0):.1%}")
                        st.metric("Nejbližší řeka", analysis.get('nearest_river_name', 'Neznámá'))
                    with col2:
                        st.metric("Vzdálenost od řeky", f"{analysis.get('river_distance_km', 0):.1f} km")
                        st.metric("Úroveň rizika", analysis.get('impact_level', 'Neznámé'))
        else:
            st.warning("⚠️ Data pro simulaci záplav nejsou dostupná.")
        
        # Geografická analýza
        st.subheader("🗺️ Geografická analýza")
        st.markdown("""
        <div style='background-color: #E8F5E8; padding: 15px; border-radius: 10px; margin-bottom: 20px;'>
            <h4 style='color: #4CAF50; margin-top: 0;'>💡 Jak funguje geografická analýza</h4>
            <p style='margin: 5px 0; font-size: 0.9em;'>
                <strong>🎯 Cíl:</strong> Komplexní posouzení rizik pro libovolnou lokaci<br>
                <strong>📊 Metodika:</strong> Kombinace analýzy řek + terénu + historických událostí<br>
                <strong>⚠️ Výstup:</strong> Celkový risk score a doporučení pro lokaci<br>
                <strong>💡 Praktický význam:</strong> Výběr bezpečných lokalit pro nové dodavatele<br>
                <strong>🗺️ Vizualizace:</strong> Výsledky se zobrazí na mapě s barevným kódováním (🗺️)
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
        
        if geo_data and geo_data.get('combined_risk_assessment'):
            # Zobrazení top 3 výsledků
            st.markdown("**📊 Top 3 nejrizikovější lokace:**")
            
            for i, analysis in enumerate(geo_data['combined_risk_assessment'][:3], 1):
                with st.expander(f"#{i} Risk Score: {analysis.get('risk_score', 0):.1f}%"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Risk Score", f"{analysis.get('risk_score', 0):.1f}%")
                        st.metric("Vzdálenost od řeky", f"{analysis.get('river_distance_km', 0):.1f} km")
                    with col2:
                        st.metric("Nadmořská výška", f"{analysis.get('elevation_m', 0):.0f} m")
                        st.metric("Historické události", analysis.get('historical_events', 0))
                    
                    st.info(f"💡 **Doporučení:** {analysis.get('recommendation', 'Neznámé')}")
        else:
            st.warning("⚠️ Data pro geografickou analýzu nejsou dostupná.")
    
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
        • **Deployment:** Render.com
        • **Mapy:** Folium (OpenStreetMap, Satelitní)
        
        ### 📈 Vývoj
        
        Aplikace je neustále vyvíjena a vylepšována na základě zpětné vazby a nových požadavků.
        """)
        
        st.markdown("---")
        st.markdown("© 2025 Risk Analyst Dashboard")

if __name__ == "__main__":
    main()
    