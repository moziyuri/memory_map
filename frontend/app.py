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

import streamlit as st  # Knihovna pro tvorbu webových aplikací
import folium  # Knihovna pro práci s mapami
import requests  # Knihovna pro HTTP požadavky
from streamlit_folium import folium_static, st_folium  # Pro zobrazení folium map ve Streamlitu
from datetime import datetime  # Pro práci s datem a časem
import time  # Pro práci s časem
import json  # Pro práci s JSON daty
import os  # Pro práci s proměnnými prostředí

# Konfigurace backendu
BACKEND_URL = os.getenv('BACKEND_URL', 'https://memorymap-api.onrender.com')

# Nastavení stránky - základní konfigurace Streamlit aplikace
st.set_page_config(
    page_title="MemoryMap",  # Titulek stránky v prohlížeči
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
    """Vytvoření mapy s markery vzpomínek"""
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
        popup_content = f"""
        <div style='width: 300px'>
            <h4>{memory['location']}</h4>
            <p>{memory['text']}</p>
            <p><small><b>Klíčová slova:</b> {', '.join(memory['keywords'])}</small></p>
            <p><small><b>Vytvořeno:</b> {memory.get('created_at', 'Neznámé datum')}</small></p>
            <a href="#" onclick="showMemoryDetail('{memory['id']}')">Zobrazit detail</a>
        </div>
        """
        
        folium.Marker(
            [memory["latitude"], memory["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=memory["location"],
            icon=folium.Icon(icon="bookmark", prefix="fa", color="blue")
        ).add_to(m)
    
    # Přidání click handleru pro přidání nové vzpomínky
    m.add_child(folium.ClickForMarker(popup="Klikněte pro přidání vzpomínky"))
    
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
def add_memory(text, location, lat, lon):
    """Přidání nové vzpomínky přes API"""
    try:
        # Příprava dat pro odeslání
        data = {
            "text": text,
            "location": location,
            "latitude": lat,
            "longitude": lon
        }
        
        # Odeslání POST požadavku na backend API
        response = requests.post(
            f"{BACKEND_URL}/api/analyze",
            json=data,
            timeout=10
        )
        
        # Kontrola odpovědi
        if response.status_code == 200:
            return True, "Vzpomínka byla úspěšně přidána!"
        else:
            return False, f"Chyba při přidávání vzpomínky: {response.text}"
    except requests.exceptions.ConnectionError:
        # Pokud se nelze připojit k API
        return False, f"Nepodařilo se připojit k API na adrese {BACKEND_URL}. Zkontrolujte, zda backend běží."
    except Exception as e:
        # Zachycení všech ostatních chyb
        return False, f"Chyba při komunikaci s API: {str(e)}"

# Sidebar - informace o aplikaci v postranním panelu
with st.sidebar:
    # Logo aplikace
    st.image("https://via.placeholder.com/150x150.png?text=MemoryMap", width=150)
    st.title("O aplikaci")
    st.info(
        "MemoryMap je aplikace pro ukládání a vizualizaci vašich vzpomínek "
        "na mapě. Přidejte vzpomínku, vyberte umístění a nechte AI "
        "analyzovat klíčová slova."
    )
    
    # Georeferencování historických názvů
    st.subheader("Georeferencování")
    with st.form("georef_form"):
        place_name = st.text_input("Název historického místa")
        historical_period = st.selectbox(
            "Historické období",
            options=["1850", "1900", "1950", "2000"],
            index=2
        )
        georef_submit = st.form_submit_button("Georeferencovat")
        
        if georef_submit and place_name:
            with st.spinner("Hledám historické místo..."):
                result = georeference_placename(place_name, historical_period)
                if result and "error" not in result:
                    st.success(f"Nalezeno místo: {result['name']}")
                    st.write(f"Geometrie: {result['geometry']}")
                elif result and "error" in result:
                    st.error(result["error"])
                else:
                    st.error("Nepodařilo se georeferencovat místo.")
    
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
st.markdown("<h1 class='main-header'>MemoryMap</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Vizualizujte své vzpomínky na mapě</p>", unsafe_allow_html=True)

# Záložky pro různé části aplikace
tab1, tab2 = st.tabs(["Mapa vzpomínek", "O aplikaci"])

with tab1:
    # Mapa
    st.markdown('<div class="tooltip">🗺️ Interaktivní mapa<span class="tooltiptext">Klikněte na mapu pro přidání nové vzpomínky nebo na pin pro zobrazení detailu</span></div>', unsafe_allow_html=True)
    
    # Načtení vzpomínek
    memories = get_memories()
    
    # Vytvoření a zobrazení mapy
    m = create_map(memories)
    map_data = st_folium(m, width=1200, height=600)
    
    # Pokud uživatel klikl na mapu
    if map_data and map_data.get("last_clicked"):
        lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
        
        # Formulář pro přidání vzpomínky
        with st.form("memory_form"):
            st.markdown('<div class="tooltip">📝 Nová vzpomínka<span class="tooltiptext">Zapište svou vzpomínku spojenou s tímto místem</span></div>', unsafe_allow_html=True)
            text = st.text_area("Text vzpomínky")
            location = st.text_input("Název místa")
            
            if st.form_submit_button("Uložit vzpomínku"):
                if text and location:
                    success, message = add_memory(text, location, lat, lon)
                    if success:
                        st.success(message)
                        st.experimental_rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Vyplňte prosím všechna pole")

with tab2:
    st.header("O aplikaci MemoryMap")
    
    # Struktura aplikace
    st.markdown("""
    ### Struktura aplikace
    
    ```
    MemoryMap/
    ├── Frontend (Streamlit)
    │   └── Interaktivní mapa s možností přidávání vzpomínek
    │   ├── Backend (FastAPI)
    │   │   ├── REST API pro správu vzpomínek
    │   │   └── Analýza textu a extrakce klíčových slov
    │   └── Database (PostgreSQL + PostGIS)
    │       └── Geografická databáze vzpomínek
    ```
    
    ### O projektu
    
    MemoryMap je interaktivní aplikace pro ukládání a vizualizaci osobních vzpomínek na mapě. 
    Projekt vznikl jako ukázka technických dovedností při přípravě na pohovor.
    
    ### Hlavní funkce
    
    - 🗺️ Interaktivní mapa pro zobrazení vzpomínek
    - 📝 Jednoduché přidávání vzpomínek kliknutím na mapu
    - 🔍 Automatická analýza textu a extrakce klíčových slov
    - 🌍 Podpora historických mapových podkladů
    """)

# Patička aplikace
st.markdown("---")
st.markdown(
    "<div style='text-align: center;'>"
    "MemoryMap AI © 2023 | Vytvořeno pomocí Streamlit"
    "</div>",
    unsafe_allow_html=True
) 