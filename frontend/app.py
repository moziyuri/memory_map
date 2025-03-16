"""
MemoryMap - Interaktivní Mapa Vzpomínek

Streamlit aplikace pro vizualizaci a správu geograficky umístěných vzpomínek.
Součást projektu vytvořeného pro demonstraci technických dovedností při přípravě
na pohovor.

Funkce:
- Interaktivní mapa pro zobrazení vzpomínek
- Nahrávání hlasových záznamů
- Vyhledávání ve vzpomínkách
- Vizualizace okolních míst

Autor: Vytvořeno jako ukázka dovedností pro pohovor.
"""
# Update: Vylepšení podpory interaktivních pinů a popup oken - 2023

import streamlit as st  # Knihovna pro tvorbu webových aplikací
import folium  # Knihovna pro práci s mapami
import requests  # Knihovna pro HTTP požadavky
from streamlit_folium import folium_static, st_folium  # Pro zobrazení folium map ve Streamlitu
from datetime import datetime  # Pro práci s datem a časem
import time  # Pro práci s časem
import json  # Pro práci s JSON daty
import os  # Pro práci s proměnnými prostředí

# Konfigurace backendu
BACKEND_URL = os.getenv('BACKEND_URL', 'https://memory-map.onrender.com')

# Nastavení stránky - základní konfigurace Streamlit aplikace
st.set_page_config(
    page_title="MemoryMap - Interaktivní Mapa Vzpomínek",  # Titulek stránky v prohlížeči
    page_icon="🗺️",  # Ikona stránky v prohlížeči
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
        color: #1E88E5;
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #0D47A1;
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
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return None

# Helper funkce pro vytvoření mapy se vzpomínkami
def create_map(memories, center_lat=DEFAULT_LAT, center_lon=DEFAULT_LON):
    """Vytvoření mapy s interaktivními piny vzpomínek"""
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)
    
    # Přidání základní mapové vrstvy Mapy.cz
    folium.TileLayer(
        tiles='https://mapserver.mapy.cz/base-m/{z}-{x}-{y}',
        attr='Mapy.cz',
        name='Základní mapa',
        overlay=False
    ).add_to(m)
    
    # Přidání historické mapové vrstvy
    folium.TileLayer(
        tiles='https://mapserver.mapy.cz/19century-m/{z}-{x}-{y}',
        attr='Mapy.cz - 19. století',
        name='Historická mapa',
        overlay=True
    ).add_to(m)
    
    # Přidání ovladače vrstev
    folium.LayerControl().add_to(m)
    
    if not memories:
        return m
    
    # Logujeme počet vzpomínek pro diagnostiku v konzoli (ne na UI)
    print(f"Funkce create_map: Zpracovávám {len(memories)} vzpomínek")
    
    # Zkusíme vypsat přehled klíčů první vzpomínky do konzole, ne na UI
    if len(memories) > 0:
        print(f"Klíče v první vzpomínce: {list(memories[0].keys())}")
    
    for i, memory in enumerate(memories):
        try:
            # Kontrola klíčových atributů
            if not all(key in memory for key in ["latitude", "longitude", "location"]):
                # Pokud chybí klíčové atributy, zkusíme alternativní formát
                if "coordinates" in memory:
                    # Pokud máme souřadnice ve formátu "coordinates", zkusíme je rozdělit
                    coords_str = memory.get("coordinates", "")
                    # Typické formáty: POINT(15.123 49.456) nebo geografický objekt
                    if isinstance(coords_str, str) and "POINT" in coords_str:
                        # Extrahujeme souřadnice z POINT(lon lat)
                        coords = coords_str.replace("POINT(", "").replace(")", "").split()
                        if len(coords) >= 2:
                            memory["longitude"] = float(coords[0])
                            memory["latitude"] = float(coords[1])
                    elif isinstance(coords_str, dict) and "coordinates" in coords_str:
                        # GeoJSON formát
                        memory["longitude"] = coords_str["coordinates"][0]
                        memory["latitude"] = coords_str["coordinates"][1]
                else:
                    print(f"Vzpomínka {i+1} nemá potřebné souřadnice: {memory}")
                    continue
            
            # Získáme souřadnice - upravujeme pro flexibilnější zpracování
            lat = float(memory.get("latitude", 0))
            lon = float(memory.get("longitude", 0))
            
            # Kontrola, že souřadnice jsou v rozumném rozsahu
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                print(f"Vzpomínka {i+1} má neplatné souřadnice: lat={lat}, lon={lon}")
                continue
            
            # Bezpečné získání dat s fallbacky pro chybějící
            location = memory.get("location", "Neznámé místo")
            text = memory.get("text", "Bez textu")
            keywords = memory.get("keywords", [])
            if not isinstance(keywords, list):
                keywords = []
            
            # Vylepšené pop-up okno s lepším formátováním a ošetřením chybějících hodnot
            popup_content = f"""
            <div style='width: 300px; padding: 10px; font-family: Arial, sans-serif;'>
                <h3 style='color: #1E88E5; margin-top: 0;'>{location}</h3>
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>
                    {text}
                </div>
                <div style='margin-top: 10px;'>
                    <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Klíčová slova:</strong> 
                       <span style='background-color: #E3F2FD; padding: 2px 5px; border-radius: 3px;'>{', '.join(keywords)}</span>
                    </p>
                    <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Datum:</strong> {memory.get('date', 'Neuvedeno')}</p>
                    <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Vytvořeno:</strong> {memory.get('created_at', 'Neznámé datum')}</p>
                </div>
            </div>
            """
            
            # Použití výraznějšího pinu (FontAwesome ikona map-pin místo bookmark)
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=location,
                icon=folium.Icon(icon="map-pin", prefix="fa", color="blue")
            ).add_to(m)
            
        except Exception as e:
            print(f"Chyba při zpracování vzpomínky {i+1}: {str(e)}")
    
    # Přidání click handleru pro přidání nové vzpomínky s jasnějším popisem
    m.add_child(folium.ClickForMarker(popup="Klikněte zde pro přidání nové vzpomínky"))
    
    return m

# Funkce pro georeferencování názvu místa
def georeference_placename(place_name, historical_period="1950"):
    """Georeferencování historického názvu místa pomocí API"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/georef", 
            json={"place_name": place_name, "historical_period": historical_period},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Chyba při georeferencování: {response.text}")
            return None
    except Exception as e:
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return None

# Funkce pro získání všech vzpomínek z API
def get_memories():
    """Získání všech vzpomínek z API"""
    try:
        # Odeslání GET požadavku na backend API
        print(f"Pokouším se o připojení k: {BACKEND_URL}/api/memories")
        response = requests.get(f"{BACKEND_URL}/api/memories", timeout=10)
        print(f"Status odpovědi: {response.status_code}")
        
        if response.status_code == 200:
            # Pokud byl požadavek úspěšný, vrátíme data
            data = response.json()
            print(f"Získáno {len(data)} záznamů")
            if len(data) > 0:
                print(f"První záznam obsahuje klíče: {list(data[0].keys())}")
            return data
        else:
            # Pokud nastal problém, zobrazíme chybovou zprávu
            st.error(f"Chyba při načítání vzpomínek (Status: {response.status_code})")
            try:
                st.error(f"Detaily chyby: {response.text}")
            except:
                pass
            return []
    except requests.exceptions.ConnectionError:
        # Pokud se nelze připojit k API
        st.error(f"Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží.")
        return []
    except Exception as e:
        # Zachycení všech ostatních chyb
        st.error(f"Chyba při komunikaci s API: {str(e)}")
        return []

# Funkce pro přidání nové vzpomínky přes API
def add_memory(text, location, lat, lon, source=None, date=None):
    """Přidání nové vzpomínky přes API"""
    try:
        # Příprava dat pro odeslání
        data = {
            "text": text,
            "location": location,
            "latitude": lat,
            "longitude": lon
        }
        
        # Přidání volitelných polí, pokud jsou vyplněna
        if source:
            data["source"] = source
        if date:
            data["date"] = date
        
        # Odeslání POST požadavku na backend API
        response = requests.post(
            f"{BACKEND_URL}/api/analyze",
            json=data,
            timeout=10
        )
        
        # Kontrola odpovědi
        if response.status_code == 200:
            return True, "✅ Vzpomínka byla úspěšně přidána! Nový pin byl přidán na mapu."
        else:
            return False, f"❌ Chyba při přidávání vzpomínky: {response.text}"
    except requests.exceptions.ConnectionError:
        # Pokud se nelze připojit k API
        return False, f"❌ Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží."
    except Exception as e:
        # Zachycení všech ostatních chyb
        return False, f"❌ Chyba při komunikaci s API: {str(e)}"

# Sidebar - informace o aplikaci v postranním panelu
with st.sidebar:
    # Stylizované logo pomocí emoji a textu - nahrazujeme externí obrázek
    st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <div style='font-size: 50px;'>🗺️ 📍 📝</div>
        <div style='background: linear-gradient(90deg, #3498db, #2c3e50); 
                   -webkit-background-clip: text; 
                   -webkit-text-fill-color: transparent; 
                   font-size: 28px; 
                   font-weight: bold;
                   margin-top: 10px;'>
            MemoryMap
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.info(
        "Aplikace pro ukládání a vizualizaci vzpomínek a historických údajů na interaktivní mapě. "
        "Ukázka technických dovedností v oblasti vývoje geografických aplikací."
    )
    
    # Aktualizace sekce o použití aplikace
    st.subheader("📋 Návod k použití")
    st.markdown("""
    **Přidání nové vzpomínky:**
    1. Klikněte na libovolné místo na mapě
    2. Vyplňte text vzpomínky a doplňující údaje
    3. Klikněte na tlačítko "Uložit vzpomínku"

    **Zobrazení existující vzpomínky:**
    - Klikněte na modrý pin na mapě
    - Detaily se zobrazí v pop-up okně
    """)
    
    # Kontrola připojení k API - vylepšení zobrazení
    st.subheader("🔌 Stav připojení")
    try:
        response = requests.get(f"{BACKEND_URL}", timeout=2)
        if response.status_code == 200:
            st.success("✅ Backend API je dostupné")
        else:
            st.warning(f"⚠️ Backend API odpovídá s kódem: {response.status_code}")
    except:
        st.error("❌ Backend API není dostupné")
    
    # Přidám odkaz na dokumentaci
    st.subheader("📚 Dokumentace")
    st.markdown("[GitHub repozitář](https://github.com/moziyuri/memory_map)")
    st.markdown("[Architektura systému](https://github.com/moziyuri/memory_map/blob/master/ARCHITECTURE.md)")

# Hlavní obsah aplikace - aktualizuji nadpisy a titulky
st.markdown("<h1 class='main-header'>🗺️ MemoryMap</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Interaktivní mapa pro ukládání a sdílení vzpomínek</p>", unsafe_allow_html=True)

# Záložky pro různé části aplikace - změním zobrazení na výraznější
tab1, tab2 = st.tabs(["📍 Mapa vzpomínek", "ℹ️ O aplikaci"])

with tab1:
    # Mapa
    st.markdown('<div class="tooltip">📍 Mapa vzpomínek<span class="tooltiptext">Klikněte na mapu pro přidání nové vzpomínky nebo na pin pro zobrazení detailu</span></div>', unsafe_allow_html=True)
    
    # Poznámka o AI-generovaných vzpomínkách
    st.caption("💡 Poznámka: Vzpomínky zobrazené na mapě byly vygenerovány pomocí umělé inteligence pro demonstrační účely.")
    
    # Získání vzpomínek
    memories = get_memories()
    
    # Kompaktnější diagnostická sekce
    with st.expander("📊 Diagnostika API", expanded=False):
        st.subheader("Stav načítání dat")
        
        # Kontrolujeme, zda máme nějaké vzpomínky
        if memories:
            st.success(f"✅ Načteno {len(memories)} vzpomínek z databáze")
            # Detaily první vzpomínky zobrazíme pouze pokud existují vzpomínky
            if len(memories) > 0:
                st.write("Detaily první vzpomínky:")
                st.json(memories[0])
        else:
            st.error("❌ Databáze neobsahuje žádné vzpomínky nebo se nepodařilo připojit k API")
            
            # Pouze pokud nejsou načteny vzpomínky, pokusíme se o přímý přístup k API
            st.subheader("Přímý test API přístupu")
            try:
                direct_url = f"{BACKEND_URL}/api/memories"
                st.write(f"Odesílám požadavek na: {direct_url}")
                
                direct_response = requests.get(direct_url, timeout=10)
                st.write(f"Status kód: {direct_response.status_code}")
                
                if direct_response.status_code == 200:
                    data = direct_response.json()
                    st.write(f"Odpověď API obsahuje {len(data)} záznamů")
                    st.json(data[:3] if len(data) > 3 else data)  # Zobrazíme nejvýše 3 záznamy
                else:
                    st.error(f"Chyba při přímém přístupu k API: {direct_response.text}")
            except Exception as e:
                st.error(f"Chyba při přímém přístupu k API: {str(e)}")
    
    # Informační zpráva pro uživatele
    st.info("👉 Pro přidání nové vzpomínky klikněte na požadované místo na mapě. Pro zobrazení existující vzpomínky klikněte na modrý pin.")
    
    # Vytvoření a zobrazení mapy - přesouváme mimo diagnostickou sekci a zjednodušujeme
    try:
        # Vytvoření mapy
        m = create_map(memories)
        
        # Zobrazení mapy v aplikaci
        map_data = st_folium(m, width=1200, height=600)
        
        # Zpracování kliknutí na mapu
        if map_data and map_data.get("last_clicked"):
            lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
            
            # Získání přibližného názvu místa pomocí reverzního geokódování
            try:
                import reverse_geocoder as rg
                location_info = rg.search((lat, lon))
                if location_info and len(location_info) > 0:
                    suggested_location = f"{location_info[0]['name']}, {location_info[0]['admin1']}"
                else:
                    suggested_location = f"Místo na souřadnicích [{lat:.5f}, {lon:.5f}]"
            except Exception as e:
                # Pokud selže reverzní geokódování, použijeme jen souřadnice
                suggested_location = f"Místo na souřadnicích [{lat:.5f}, {lon:.5f}]"
            
            # Formulář pro přidání nové vzpomínky
            st.subheader("📝 Přidat novou vzpomínku")
            
            # Vytvoření jednoduchého formuláře
            with st.form("memory_form"):
                # Text vzpomínky
                text = st.text_area("Text vzpomínky*", height=150, 
                                   help="Popište vaši vzpomínku nebo historickou událost")
                
                # Název místa - předvyplněný z reverzního geokódování
                location = st.text_input("Název místa*", 
                                       value=suggested_location,
                                       help="Název místa, ke kterému se vzpomínka váže")
                
                # Rozšířené informace - volitelné
                col1, col2 = st.columns(2)
                with col1:
                    source = st.text_input("Zdroj (volitelné)", 
                                          help="Odkud informace pochází (kniha, archiv, osobní zkušenost)")
                with col2:
                    date = st.text_input("Datum (volitelné)", 
                                        help="Datum vzpomínky nebo události (libovolný formát)")
                
                # Informace o souřadnicích - pouze pro informaci
                st.write(f"Souřadnice: {lat:.5f}, {lon:.5f}")
                
                # Tlačítko pro odeslání
                submit = st.form_submit_button("Uložit vzpomínku")
                
                # Zpracování odeslání formuláře
                if submit:
                    if text and location:
                        # Odeslání dat na backend
                        with st.spinner("Ukládám vzpomínku a analyzuji klíčová slova..."):
                            success, message = add_memory(text, location, lat, lon, source, date)
                            if success:
                                st.success(message)
                                st.balloons()  # Přidáme efekt balonků pro oslavu úspěchu
                                time.sleep(1)  # Krátká pauza, aby uživatel viděl úspěšnou zprávu
                                st.experimental_rerun()  # Obnovíme stránku pro zobrazení nového pinu
                            else:
                                st.error(message)
                    else:
                        st.warning("⚠️ Vyplňte prosím text vzpomínky a název místa")
    except Exception as e:
        st.error(f"Chyba při vytváření nebo zobrazení mapy: {str(e)}")
        st.write("Detaily chyby:")
        st.exception(e)

with tab2:
    st.header("🧠 O aplikaci MemoryMap")
    
    # Zvýrazněná informace o účelu aplikace
    st.info("**MemoryMap** je interaktivní projekt pro ukládání geograficky umístěných vzpomínek a historických faktů. Byl vytvořen jako ukázka technických dovedností pro účely pracovního pohovoru, demonstrující praktické zkušenosti s vývojem full-stack aplikací a zpracováním geografických dat.")
    
    # Aktualizovaná struktura aplikace - více detailů
    st.subheader("🔍 Architektura projektu")
    st.markdown("""
    ```
    MemoryMap/
    ├── Frontend (Streamlit)
    │   └── Interaktivní mapa s piny a formulářem pro přidávání vzpomínek
    ├── Backend (FastAPI)
    │   ├── REST API pro správu vzpomínek
    │   ├── PostgreSQL + PostGIS databáze
    │   └── Analýza textu a extrakce klíčových slov
    └── Infrastruktura
        ├── Nasazení na Streamlit Cloud (frontend)
        └── Nasazení na Render.com (backend)
    ```
    """)
    
    # Aktualizované technologie
    st.subheader("⚙️ Použité technologie")
    # Nejprve přidám informaci o hlavním programovacím jazyce
    st.markdown("**Programovací jazyk:** Python 3.9+ (full-stack)")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Frontend:**")
        st.markdown("- Streamlit")
        st.markdown("- Folium (interaktivní mapy)")
        st.markdown("- Reverse Geocoding")
    
    with col2:
        st.markdown("**Backend:**")
        st.markdown("- FastAPI")
        st.markdown("- Pydantic")
        st.markdown("- RESTful API")
    
    with col3:
        st.markdown("**Databáze:**")
        st.markdown("- PostgreSQL")
        st.markdown("- PostGIS rozšíření")
        st.markdown("- psycopg2")
    
    # Aktualizovaná funkcionalita
    st.subheader("✨ Hlavní funkce")
    st.markdown("""
    - **Interaktivní mapa** s piny reprezentujícími uložené vzpomínky
    - **Pop-up okna** s detaily vzpomínek a klíčovými slovy
    - **Intuitivní přidávání vzpomínek** kliknutím na mapě
    - **Automatická geolokace** podle kliknutí na mapě
    - **Extrakce klíčových slov** z textu vzpomínek
    - **Multivrstvá mapa** s moderním i historickým zobrazením
    """)
    
    # Aktualizovaný cíl projektu
    st.subheader("🎯 Cíl projektu")
    st.markdown("""
    Tento projekt demonstruje komplexní full-stack aplikaci s důrazem na:
    1. **Moderní architekturu** - oddělení frontend a backend logiky
    2. **Geografické funkce** - práce s mapami a prostorovými daty
    3. **RESTful API design** - čistá implementace API endpointů
    4. **Cloud deployment** - nasazení v produkčním prostředí
    5. **Uživatelskou přívětivost** - intuitivní rozhraní pro interakci s mapou
    """)
    
    # Aktualizované kontaktní údaje
    st.subheader("📬 Kontakt")
    st.markdown("**Autor:** Stanislav Horáček")
    st.markdown("**GitHub:** [github.com/moziyuri/memory_map](https://github.com/moziyuri/memory_map)")
    st.markdown("**Platforma:** Demo aplikace pro technické pohovory")

# Aktualizuji patičku aplikace s pevně nastaveným rokem 2025
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 10px;'>
        <p>© 2025 MemoryMap | Interaktivní mapa vzpomínek</p>
        <p style='font-size: 0.8em;'>
            <a href='https://github.com/moziyuri/memory_map' target='_blank'>GitHub</a> | 
            <a href='https://github.com/moziyuri/memory_map/blob/master/README.md' target='_blank'>README</a> | 
            <a href='https://github.com/moziyuri/memory_map/blob/master/USER_GUIDE.md' target='_blank'>Uživatelská příručka</a> | 
            <a href='https://github.com/moziyuri/memory_map/blob/master/ARCHITECTURE.md' target='_blank'>Architektura</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True
) 