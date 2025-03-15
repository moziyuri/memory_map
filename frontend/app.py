import streamlit as st  # Knihovna pro tvorbu webových aplikací
import folium  # Knihovna pro práci s mapami
import requests  # Knihovna pro HTTP požadavky
from streamlit_folium import folium_static  # Pro zobrazení folium map ve Streamlitu
from datetime import datetime  # Pro práci s datem a časem
import time  # Pro práci s časem
import json  # Pro práci s JSON daty

# Nastavení stránky - základní konfigurace Streamlit aplikace
st.set_page_config(
    page_title="MemoryMap AI",  # Titulek stránky v prohlížeči
    page_icon="🗺️",  # Ikona stránky v prohlížeči
    layout="wide",  # Široké rozložení stránky
    initial_sidebar_state="expanded"  # Postranní panel bude na začátku rozbalený
)

# Konstanty aplikace
API_URL = "http://localhost:8000"  # Adresa backend API
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
</style>
""", unsafe_allow_html=True)

# Helper funkce pro vytvoření mapy se vzpomínkami
def create_map(memories, center_lat=DEFAULT_LAT, center_lon=DEFAULT_LON):
    """Vytvoření mapy s markery vzpomínek"""
    # Inicializace mapy se středem a úrovní přiblížení
    m = folium.Map(location=[center_lat, center_lon], zoom_start=7)
    
    # Přidání základní mapové vrstvy Mapy.cz
    folium.TileLayer(
        tiles='https://mapserver.mapy.cz/base-m/{z}-{x}-{y}',
        attr='Mapy.cz',
        name='Základní mapa',
        overlay=False
    ).add_to(m)
    
    # Přidání historické mapové vrstvy z 19. století
    folium.TileLayer(
        tiles='https://mapserver.mapy.cz/19century-m/{z}-{x}-{y}',
        attr='Mapy.cz - 19. století',
        name='Historická mapa 19. století',
        overlay=True
    ).add_to(m)
    
    # Přidání vrstvy císařských otisků
    folium.TileLayer(
        tiles='https://ags.cuzk.cz/archiv-wmts/tile/1.0.0/3857/{z}/{y}/{x}',
        attr='ČÚZK - Archivy',
        name='Císařské otisky',
        overlay=True
    ).add_to(m)
    
    # Přidání další historické vrstvy ČÚZK
    folium.TileLayer(
        tiles='https://ags.cuzk.cz/archiv-wmts/tile/1.0.0/3857/{z}/{y}/{x}',
        attr='ČÚZK - Archivy',
        name='Historické mapy ČÚZK',
        overlay=True
    ).add_to(m)
    
    # Přidání ovladače vrstev
    folium.LayerControl().add_to(m)
    
    # Když nejsou žádné vzpomínky, vrátíme prázdnou mapu
    if not memories:
        return m
    
    # Přidáme každou vzpomínku jako marker na mapě
    for memory in memories:
        # Vytvoření HTML obsahu pro popup markeru
        popup_content = f"""
        <div style='width: 300px'>
            <h4>{memory['location']}</h4>
            <p>{memory['text']}</p>
            <p><small><b>Klíčová slova:</b> {', '.join(memory['keywords'])}</small></p>
            <p><small><b>Vytvořeno:</b> {memory.get('created_at', 'Neznámé datum')}</small></p>
        </div>
        """
        
        # Přidání markeru na mapu
        folium.Marker(
            [memory["latitude"], memory["longitude"]],  # Pozice markeru
            popup=folium.Popup(popup_content, max_width=300),  # Obsah popup okna
            tooltip=memory["location"],  # Text, který se zobrazí při najetí myší
            icon=folium.Icon(icon="bookmark", prefix="fa", color="blue")  # Ikona markeru
        ).add_to(m)
    
    return m

# Funkce pro georeferencování názvu místa
def georeference_placename(place_name, historical_period="1950"):
    """Georeferencování historického názvu místa pomocí API"""
    try:
        response = requests.post(
            f"{API_URL}/georef", 
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
        response = requests.get(f"{API_URL}/api/memories", timeout=5)
        if response.status_code == 200:
            # Pokud byl požadavek úspěšný, vrátíme data
            return response.json()
        else:
            # Pokud nastal problém, zobrazíme chybovou zprávu
            st.error(f"Chyba při načítání vzpomínek (Status: {response.status_code})")
            return []
    except requests.exceptions.ConnectionError:
        # Pokud se nelze připojit k API
        st.error(f"Nepodařilo se připojit k API na adrese {API_URL}. Zkontrolujte, zda backend běží.")
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
            f"{API_URL}/api/analyze",
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
        return False, f"Nepodařilo se připojit k API na adrese {API_URL}. Zkontrolujte, zda backend běží."
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
        response = requests.get(f"{API_URL}", timeout=2)
        if response.status_code == 200:
            st.success("✅ API je dostupné")
        else:
            st.warning(f"⚠️ API vrací status kód: {response.status_code}")
    except:
        st.error("❌ API není dostupné")

# Hlavní obsah aplikace
st.markdown("<h1 class='main-header'>MemoryMap AI</h1>", unsafe_allow_html=True)
st.markdown("<p class='subheader'>Vizualizujte své vzpomínky na mapě</p>", unsafe_allow_html=True)

# Rozdělení obrazovky na dva sloupce
col1, col2 = st.columns([1, 2])

# Levý sloupec - formulář pro přidání vzpomínky
with col1:
    st.markdown("### Přidat novou vzpomínku")
    
    # Vytvoření formuláře
    with st.form("memory_form", clear_on_submit=True):
        # Pole pro text vzpomínky
        text = st.text_area("Text vzpomínky", placeholder="Popište svou vzpomínku...", height=150)
        # Pole pro název místa
        location = st.text_input("Název místa", placeholder="Např. Praha, Brno, ...")
        
        # Pole pro souřadnice - rozděleno do dvou sloupců
        lat_col, lon_col = st.columns(2)
        with lat_col:
            lat = st.number_input("Zeměpisná šířka", value=DEFAULT_LAT, format="%.6f")
        with lon_col:
            lon = st.number_input("Zeměpisná délka", value=DEFAULT_LON, format="%.6f")
        
        # Tlačítko pro odeslání formuláře
        submit_button = st.form_submit_button("Přidat vzpomínku", use_container_width=True)
        
        # Zpracování formuláře po odeslání
        if submit_button:
            if not text or not location:
                # Kontrola, zda jsou vyplněna povinná pole
                st.error("Vyplňte prosím text vzpomínky a název místa.")
            else:
                # Odeslání dat na backend
                with st.spinner("Přidávám vzpomínku a analyzuji klíčová slova..."):
                    success, message = add_memory(text, location, lat, lon)
                    if success:
                        # Zobrazení úspěšné zprávy
                        st.markdown(f"<div class='success-msg'>{message}</div>", unsafe_allow_html=True)
                        time.sleep(1)  # Krátké zpoždění pro lepší UX
                        st.experimental_rerun()  # Znovu načteme stránku pro aktualizaci dat
                    else:
                        # Zobrazení chybové zprávy
                        st.markdown(f"<div class='error-msg'>{message}</div>", unsafe_allow_html=True)

# Pravý sloupec - mapa a seznam vzpomínek
with col2:
    st.markdown("### Mapa vzpomínek")
    
    # Nastavení typu mapového podkladu
    map_type = st.radio(
        "Vyberte typ mapového podkladu:",
        ("Moderní", "Historický", "Všechny vrstvy"),
        horizontal=True
    )
    
    # Načtení vzpomínek z API
    with st.spinner("Načítám vzpomínky..."):
        memories = get_memories()
    
    # Vytvoření a zobrazení mapy
    if memories:
        # Pokud jsou nějaké vzpomínky, vytvoříme mapu s markery
        memory_map = create_map(memories)
        folium_static(memory_map, width=800, height=500)
        
        # Výpis seznamu vzpomínek
        st.markdown(f"### Seznam vzpomínek ({len(memories)})")
        for idx, memory in enumerate(memories):
            # Každá vzpomínka je v rozbalovacím panelu
            with st.expander(f"{memory['location']} - {', '.join(memory['keywords'][:3])}"):
                st.write(memory['text'])
                st.caption(f"Souřadnice: {memory['latitude']}, {memory['longitude']}")
    else:
        # Pokud nejsou žádné vzpomínky, zobrazíme prázdnou mapu a informaci
        placeholder_map = create_map([])
        folium_static(placeholder_map, width=800, height=500)
        st.info("Zatím zde nejsou žádné vzpomínky. Přidejte svou první vzpomínku pomocí formuláře vlevo.")

# Patička aplikace
st.markdown("---")
st.markdown(
    "<div style='text-align: center;'>"
    "MemoryMap AI © 2023 | Vytvořeno pomocí Streamlit"
    "</div>",
    unsafe_allow_html=True
) 