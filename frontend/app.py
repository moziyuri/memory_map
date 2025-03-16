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
    
    for memory in memories:
        # Vylepšené pop-up okno s lepším formátováním
        popup_content = f"""
        <div style='width: 300px; padding: 10px; font-family: Arial, sans-serif;'>
            <h3 style='color: #1E88E5; margin-top: 0;'>{memory['location']}</h3>
            <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 10px;'>
                {memory['text']}
            </div>
            <div style='margin-top: 10px;'>
                <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Klíčová slova:</strong> 
                   <span style='background-color: #E3F2FD; padding: 2px 5px; border-radius: 3px;'>{', '.join(memory['keywords'])}</span>
                </p>
                <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Datum:</strong> {memory.get('date', 'Neuvedeno')}</p>
                <p style='margin: 5px 0;'><strong style='color: #0D47A1;'>Vytvořeno:</strong> {memory.get('created_at', 'Neznámé datum')}</p>
            </div>
        </div>
        """
        
        # Použití výraznějšího pinu (FontAwesome ikona map-pin místo bookmark)
        folium.Marker(
            [memory["latitude"], memory["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=memory["location"],
            icon=folium.Icon(icon="map-pin", prefix="fa", color="blue")
        ).add_to(m)
    
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
        response = requests.get(f"{BACKEND_URL}/api/memories", timeout=5)
        if response.status_code == 200:
            # Pokud byl požadavek úspěšný, vrátíme data
            return response.json()
        else:
            # Pokud nastal problém, zobrazíme chybovou zprávu
            st.error(f"Chyba při načítání vzpomínek (Status: {response.status_code})")
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
    # Logo aplikace
    st.image("https://via.placeholder.com/150x150.png?text=MemoryMap", width=150)
    st.title("O aplikaci")
    st.info(
        "MemoryMap je aplikace pro ukládání a vizualizaci vašich vzpomínek "
        "na mapě. Přidejte vzpomínku kliknutím na mapu a nechte AI "
        "analyzovat klíčová slova."
    )
    
    # Přidána sekce o pinech na mapě a pop-up oknech
    st.subheader("Jak používat aplikaci")
    st.markdown("""
    **Přidání vzpomínky:**
    1. Klikněte na mapu v místě, ke kterému se váže vaše vzpomínka
    2. Vyplňte text vzpomínky a název místa
    3. Uložte vzpomínku

    **Zobrazení vzpomínky:**
    Klikněte na modrý pin pro zobrazení detailu vzpomínky v popup okně
    """)
    
    # Kontrola připojení k API
    st.subheader("Status API")
    try:
        response = requests.get(f"{BACKEND_URL}", timeout=2)
        if response.status_code == 200:
            st.success("✅ API je dostupné")
        else:
            st.warning(f"⚠️ API vrací status kód: {response.status_code}")
    except:
        st.error("❌ API není dostupné")

# Hlavní obsah aplikace
st.markdown("<h1 class='main-header'>🗺️ MemoryMap - AKTUALIZOVÁNO</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Interaktivní mapa s piny pro ukládání vašich vzpomínek</p>", unsafe_allow_html=True)

# Záložky pro různé části aplikace
tab1, tab2 = st.tabs(["Mapa vzpomínek", "O aplikaci"])

with tab1:
    # Mapa
    st.markdown('<div class="tooltip">🗺️ Interaktivní mapa<span class="tooltiptext">Klikněte na mapu pro přidání nové vzpomínky nebo na pin pro zobrazení detailu</span></div>', unsafe_allow_html=True)
    
    # Načtení vzpomínek
    memories = get_memories()
    
    # Informativní zpráva pro uživatele
    st.info("👉 Pro přidání nové vzpomínky klikněte na požadované místo na mapě. Pro zobrazení existující vzpomínky klikněte na modrý pin.")
    
    # Vytvoření a zobrazení mapy
    m = create_map(memories)
    map_data = st_folium(m, width=1200, height=600)
    
    # Pokud uživatel klikl na mapu
    if map_data and map_data.get("last_clicked"):
        lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
        
        # Získání přibližného názvu místa pomocí reverzního geokódování
        try:
            import reverse_geocoder as rg
            location_info = rg.search((lat, lon))
            if location_info and len(location_info) > 0:
                suggested_location = f"{location_info[0]['name']}, {location_info[0]['admin1']}"
            else:
                suggested_location = ""
        except:
            suggested_location = ""
        
        # Zobrazení souřadnic místa (ale uživatel je nemusí zadávat ručně)
        st.success(f"📍 Vybráno místo: {suggested_location or 'Neidentifikováno'} (souřadnice: {lat:.6f}, {lon:.6f})")
        
        # Vylepšený formulář pro přidání vzpomínky
        with st.form("memory_form"):
            st.subheader("📝 Přidání nové vzpomínky")
            text = st.text_area("Text vzpomínky", height=150, help="Popište svou vzpomínku nebo příběh spojený s tímto místem")
            
            # Pokud máme návrh názvu místa, předvyplníme ho, jinak necháme prázdné
            location = st.text_input("Název místa", value=suggested_location, 
                                    help="Zadejte název místa, ke kterému se vzpomínka váže")
            
            # Přidáme další volitelná pole
            col1, col2 = st.columns(2)
            with col1:
                source = st.text_input("Zdroj vzpomínky (volitelné)", 
                                    help="Např. 'Osobní zážitek', 'Vyprávění babičky', 'Historická kniha'")
            with col2:
                date = st.text_input("Datum vzpomínky (volitelné)", 
                                   help="Datum, ke kterému se vzpomínka váže, např. 'Léto 1989'")
            
            # Přidáme tlačítka
            col1, col2 = st.columns([1, 3])
            with col1:
                submit = st.form_submit_button("💾 Uložit vzpomínku", use_container_width=True)
            with col2:
                st.markdown("<div style='height: 34px;'></div>", unsafe_allow_html=True)  # Prázdný prostor pro zarovnání
            
            if submit:
                if text and location:
                    # Připravíme data pro odeslání včetně volitelných polí
                    data = {
                        "text": text,
                        "location": location,
                        "latitude": lat,
                        "longitude": lon
                    }
                    
                    # Přidáme volitelná pole, pokud byla vyplněna
                    if source:
                        data["source"] = source
                    if date:
                        data["date"] = date
                    
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
    else:
        # Pokud uživatel ještě neklikl na mapu, zobrazíme instrukce
        if not memories:
            st.info("Na mapě zatím nejsou žádné vzpomínky. Klikněte na mapu pro přidání první vzpomínky.")

with tab2:
    st.header("O aplikaci MemoryMap")
    
    # Zvýrazněná informace o účelu aplikace
    st.info("**MemoryMap** byla vytvořena za účelem demonstrace technických dovedností při pracovním pohovoru. Projekt ukazuje praktické zkušenosti s vývojem full-stack aplikací, zpracováním geografických dat a propojením moderních technologií.")
    
    # Struktura aplikace
    st.subheader("Struktura aplikace")
    st.markdown("""
    ```
    MemoryMap/
    ├── Frontend (Streamlit)
    │   └── Interaktivní mapa s piny a pop-up okny pro zobrazení a přidávání vzpomínek
    │   ├── Backend (FastAPI)
    │   │   ├── REST API pro správu vzpomínek
    │   │   └── Analýza textu a extrakce klíčových slov
    │   └── Database (PostgreSQL + PostGIS)
    │       └── Geografická databáze vzpomínek
    ```
    """)
    
    # Technologie
    st.subheader("Použité technologie")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Frontend:**")
        st.markdown("- Streamlit")
        st.markdown("- Folium (interaktivní mapy)")
        st.markdown("- Streamlit-Folium")
    
    with col2:
        st.markdown("**Backend:**")
        st.markdown("- FastAPI")
        st.markdown("- PostgreSQL + PostGIS")
        st.markdown("- Pydantic, psycopg2")
    
    # Funkcionalita
    st.subheader("Hlavní funkce")
    st.markdown("""
    - **Interaktivní mapa** s piny reprezentujícími uložené vzpomínky
    - **Pop-up okna** pro rychlé zobrazení obsahu vzpomínek
    - **Přidávání vzpomínek** přímo kliknutím na mapu
    - **Automatická extrakce klíčových slov** z textu vzpomínek
    - **Vyhledávání a filtrování** vzpomínek podle různých kritérií
    """)
    
    # Kontakt
    st.subheader("Kontakt")
    st.markdown("**Autor:** Stanislav Horáček")
    st.markdown("**Email:** stanislav.horacek@email.cz")
    st.markdown("**GitHub:** [github.com/stanislavhoracek/memorymap](https://github.com/stanislavhoracek/memorymap)")

# Patička aplikace
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 10px;'>
        <p>© 2023 MemoryMap | Aplikace vytvořená za účelem pohovoru</p>
        <p style='font-size: 0.8em;'>
            <a href='https://github.com/stanislavhoracek/memorymap' target='_blank'>GitHub</a> | 
            <a href='https://github.com/stanislavhoracek/memorymap/blob/main/README.md' target='_blank'>README</a> | 
            <a href='https://github.com/stanislavhoracek/memorymap/blob/main/USER_GUIDE.md' target='_blank'>Uživatelská příručka</a> | 
            <a href='https://github.com/stanislavhoracek/memorymap/blob/main/ARCHITECTURE.md' target='_blank'>Architektura</a>
        </p>
    </div>
    """,
    unsafe_allow_html=True
) 