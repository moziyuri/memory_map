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
BACKEND_URL = os.getenv('BACKEND_URL', 'https://risk-analyst.onrender.com')

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
    supplier_group = folium.FeatureGroup(name="🏭 Dodavatelé", show=True)
    
    for supplier in suppliers:
        if supplier.get('latitude') and supplier.get('longitude') and is_in_czech_republic(supplier['latitude'], supplier['longitude']):
            lat = supplier['latitude']
            lon = supplier['longitude']
            
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
                tooltip=f"🏭 {supplier['name']} ({supplier.get('risk_level', 'N/A')})"
            ).add_to(supplier_group)
    
    supplier_group.add_to(m)
    
    # Přidání rizikových událostí (červené značky)
    event_group = folium.FeatureGroup(name="⚠️ Rizikové události", show=True)
    
    for event in events:
        if event.get('latitude') and event.get('longitude') and is_in_czech_republic(event['latitude'], event['longitude']):
            lat = event['latitude']
            lon = event['longitude']
            
            # Barva podle závažnosti
            severity_colors = {'low': 'lightred', 'medium': 'red', 'high': 'darkred', 'critical': 'black'}
            color = severity_colors.get(event.get('severity', 'medium'), 'red')
            
            # Vylepšený popup s odkazem na zdroj
            source_link = ""
            if event.get('url'):
                source_link = f"<p><strong>Zdroj:</strong> <a href='{event['url']}' target='_blank'>Otevřít zdroj</a></p>"
            
            popup_content = f"""
            <div style='width: 250px;'>
                <h4>⚠️ {event['title']}</h4>
                <p><strong>Typ:</strong> {event.get('event_type', 'Neznámé')}</p>
                <p><strong>Závažnost:</strong> {event.get('severity', 'Neznámé')}</p>
                <p><strong>Datum:</strong> {event.get('created_at', 'Neznámé')}</p>
                <p><strong>Popis:</strong> {event.get('description', 'Bez popisu')}</p>
                {source_link}
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                icon=folium.Icon(color=color, icon='exclamation-triangle', prefix='fa'),
                tooltip=f"⚠️ {event['title'][:30]}..."
            ).add_to(event_group)
    
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
    
    # Typ události
    event_types = ["Všechny", "flood", "supply_chain"]
    selected_event_type = st.sidebar.selectbox("📊 Typ události:", event_types)
    
    # Závažnost
    severity_levels = ["Všechny", "low", "medium", "high", "critical"]
    selected_severity = st.sidebar.selectbox("⚠️ Závažnost:", severity_levels)
    
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
    czech_events = [e for e in filtered_events if e.get('latitude') and e.get('longitude') and 
                    is_in_czech_republic(e['latitude'], e['longitude'])]
    
    czech_suppliers = [s for s in suppliers if s.get('latitude') and s.get('longitude') and 
                       is_in_czech_republic(s['latitude'], s['longitude'])]
    
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
            st.info(f"📊 Zobrazeno: {len(czech_events)} událostí + {len(czech_suppliers)} dodavatelů")
        
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
        
        if flood_data and flood_data.get('flood_analysis'):
            # Zobrazení top 3 výsledků
            st.markdown("**📊 Top 3 nejohroženější dodavatelé:**")
            
            for i, analysis in enumerate(flood_data['flood_analysis'][:3], 1):
                # Opravené získání názvu dodavatele
                supplier_info = analysis.get('supplier', {})
                supplier_name = supplier_info.get('name', 'Neznámý dodavatel') if supplier_info else 'Neznámý dodavatel'
                
                with st.expander(f"#{i} {supplier_name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        # Opravené získání dat o záplavách
                        flood_risk = analysis.get('flood_risk', {})
                        probability = flood_risk.get('probability', 0)
                        nearest_river = flood_risk.get('nearest_river_name', 'Neznámá')
                        river_distance = flood_risk.get('river_distance_km', 0)
                        impact_level = flood_risk.get('impact_level', 'Neznámé')
                        
                        st.metric("Pravděpodobnost záplav", f"{probability:.1%}")
                        st.metric("Nejbližší řeka", nearest_river)
                    with col2:
                        st.metric("Vzdálenost od řeky", f"{river_distance:.1f} km")
                        st.metric("Úroveň rizika", impact_level)
        else:
            st.warning("⚠️ Data pro simulaci záplav nejsou dostupná.")
        
        # Geografická analýza
        st.subheader("🗺️ Geografická analýza")
        
        if geo_data and geo_data.get('combined_risk_assessment'):
            # Zobrazení top 3 výsledků
            st.markdown("**📊 Top 3 nejrizikovější lokace:**")
            
            for i, analysis in enumerate(geo_data['combined_risk_assessment'][:3], 1):
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