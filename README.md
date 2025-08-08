# VW Group Risk Analyst Dashboard

> **Aplikace vytvořená za účelem pohovoru na pozici Risk Analyst** - Projekt demonstruje praktické dovednosti v oblasti full-stack vývoje, web scraping, GIS analýzy a supply chain risk management.

Interaktivní dashboard pro analýzu rizikových událostí v dodavatelském řetězci VW Group s využitím reálných dat z CHMI API, OpenMeteo API a RSS feeds.

## 🌟 Funkce

- **Interaktivní mapa rizik** zobrazující rizikové události a dodavatele VW Group (s clusteringem značek pro přehlednost)
- **Web scraping** reálných dat z CHMI (počasí), OpenMeteo API (meteorologická data) a RSS feeds (zprávy) s přísnou lokalizací (žádné generické body uprostřed ČR)
- **Filtry** podle typu události, závažnosti, zdroje dat a časového období
- **Analýza dodavatelů** s rizikovým hodnocením a kategorizací
- **Statistiky a trendy** rizikových událostí v čase
- **Geografické omezení** na území České republiky
- **Responzivní design** pro používání na počítači i mobilních zařízeních
- **Pokročilé GIS funkce** včetně analýzy vzdálenosti od řek a simulace záplav (PostGIS funkce, metriky v km)

### Co je nově důležité

- **Přísná lokalizace událostí**: RSS/CHMI událost se uloží jen pokud má validní českou lokalitu (z titulku/description, případně geokódování CZ; jinak se neuloží).
- **CHMI extrakce**: flood event vznikne pouze při zjištěných stavech SPA/bdělost/pohotovost/ohrožení; "Normální stav" nic nevytváří.
- **Geokódování CZ**: při nejasné lokalitě se použije geokódování (CZ), případně centroid konkrétní řeky z DB.
- **Clustering**: značky událostí i dodavatelů jsou clusterované (lepší čitelnost).
- **DB funkce**: `analyze_flood_risk_from_rivers(lat, lon)` (2 parametry) a `calculate_river_distance(lat, lon)`; přidané **constrainty** zajišťují správnost lat/lon.
- **Údržba dat**: endpoint `POST /api/maintenance/clear-irrelevant-rss` smaže zjevně irelevantní RSS (právo/krimi apod.).

## 🔗 Odkazy

- **Frontend**: [https://risk-analyst-sh.streamlit.app/](https://risk-analyst-sh.streamlit.app/)
- **Backend API**: [https://risk-analyst.onrender.com](https://risk-analyst.onrender.com)
- **API dokumentace**: [https://risk-analyst.onrender.com/docs](https://risk-analyst.onrender.com/docs)
- **GitHub Repository**: [https://github.com/moziyuri/memory_map/tree/feature/risk-analyst](https://github.com/moziyuri/memory_map/tree/feature/risk-analyst)

## 📖 O aplikaci

VW Group Risk Analyst Dashboard je interaktivní aplikace pro analýzu rizik v dodavatelském řetězci, která vznikla jako ukázka dovedností pro účely pohovoru na pozici Risk Analyst. Projekt demonstruje schopnosti v těchto oblastech:

### Účel a vznik
Aplikace byla vytvořena specificky pro demonstraci technických dovedností v kontextu pracovního pohovoru na pozici Risk Analyst ve VW Group. Cílem bylo vytvořit funkční dashboard, který ukáže schopnosti práce s:
- Web scraping reálných dat
- GIS analýzou a geografickými daty
- Supply chain risk management
- Moderními technologiemi a frameworks
- Robustní error handling a deployment

### Koncept
Základní myšlenkou je monitoring rizikových událostí, které mohou ovlivnit dodavatelský řetězec VW Group. Aplikace:
- Sbírá reálná data z CHMI API (počasí), OpenMeteo API (meteorologická data) a RSS feeds (zprávy)
- Analyzuje rizika v okolí dodavatelů VW Group
- Poskytuje přehledné statistiky a trendy
- Umožňuje filtrování a analýzu podle různých kritérií
- Implementuje pokročilé GIS funkce pro analýzu rizik

### Technologická ukázka
Aplikace demonstruje zkušenosti s:
- Web scraping a práci s externími API
- GIS analýzou a geografickými daty
- Supply chain risk management
- Vývojem interaktivních mapových rozhraní
- Návrhem a implementací REST API
- Nasazením aplikací na cloud platformy
- Robustní error handling a transaction management

## 🏗️ Architektura

Risk Analyst Dashboard je full-stack aplikace se třemi hlavními komponentami:

1. **Frontend** (Streamlit) - Uživatelské rozhraní postavené na Streamlit frameworku
2. **Backend API** (FastAPI) - REST API poskytující přístup k datům a web scraping
3. **PostgreSQL databáze** - Úložiště pro rizikové události a dodavatele s PostGIS rozšířením

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│   Frontend      │◄────►│   Backend API   │◄────►│   PostgreSQL    │
│   (Streamlit)   │      │   (FastAPI)     │      │   + PostGIS     │
│                 │      │   + Web Scraping│      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
     Streamlit               Render.com               Render.com
```

*Podrobnější popis architektury najdete v [ARCHITECTURE.md](ARCHITECTURE.md)*

## 🧰 Technologie

### Frontend
- **Streamlit** - Framework pro rychlé vytváření datových aplikací
- **Folium** - Knihovna pro vytváření interaktivních map s podporou pop-up oken a pinů
- **Streamlit-Folium** - Integrace Folium map do Streamlit aplikací
- **Pandas** - Analýza a zpracování dat
- **Python** - Programovací jazyk

### Backend
- **FastAPI** - Moderní, rychlý webový framework pro tvorbu API
- **Pydantic** - Validace dat a nastavení pomocí anotací typu Python
- **PostgreSQL** - Relační databáze
- **PostGIS** - Prostorové rozšíření pro PostgreSQL
- **psycopg2** - PostgreSQL adaptér pro Python
- **Requests** - HTTP knihovna pro web scraping
- **xml.etree.ElementTree** - Parsování RSS feeds
- **uvicorn** - ASGI server pro Python

## 🧱 Struktura projektu

```
risk-analyst-dashboard/
├── frontend/              # Streamlit aplikace
│   ├── app.py             # Hlavní soubor aplikace
│   └── requirements.txt   # Závislosti pro frontend
│
├── backend/               # FastAPI backend
│   ├── main.py            # Hlavní soubor API s web scraping
│   ├── init_risk_db.py    # Inicializační skript pro databázi (vylepšený)
│   ├── reset_risk_db.py   # Reset skript pro databázi (vylepšený)
│   ├── test_risk_db.py    # Test připojení k databázi
│   ├── test_weather_api.py # Test různých weather APIs
│   ├── test_improved_scraping.py # Test vylepšeného scrapingu
│   └── requirements.txt   # Závislosti pro backend
│
├── database/              # SQL skripty
│   ├── init.sql           # Základní inicializace databáze
│   └── memories_data.sql  # Demo data
│
├── README.md              # Tento soubor
├── RISK_ANALYST_PROJECT.md # Detailní plán projektu
├── ARCHITECTURE.md        # Detailní popis architektury
├── DEPLOYMENT.md          # Instrukce pro nasazení
└── USER_GUIDE.md          # Uživatelská příručka
```

## 📊 Zdroje dat

### Reálná data
- **CHMI** - Meteorologická/hydrologická data a varování; flood událost pouze při stavech SPA/bdělost/pohotovost/ohrožení a s ověřenou lokalizací.
- **OpenMeteo API** - Spolehlivá meteorologická data (primární zdroj pro počasí)
- **RSS feeds** - Zprávy z českých médií; události vznikají jen s validní českou lokalitou (jinak se zahodí)

### Demo data
- **Dodavatelé VW Group** - Fiktivní dodavatelé s rizikovým hodnocením
- **Rizikové události** - Historické události pro demonstraci funkcí

## 🚀 Rychlý start

### Lokální spuštění

1. **Klonování repozitáře**
   ```bash
   git clone https://github.com/moziyuri/memory_map.git
   cd memory_map
   git checkout feature/risk-analyst
   ```

2. **Instalace závislostí**
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend
   cd ../frontend
   pip install -r requirements.txt
   ```

3. **Spuštění aplikace**
   ```bash
   # Backend (v adresáři backend)
   python main.py
   
   # Frontend (v adresáři frontend)
   streamlit run app.py
   ```

### Nasazení na cloud

Aplikace je nasazena na:
- **Backend**: Render.com (FastAPI + PostgreSQL)
- **Frontend**: Streamlit Cloud

## 📈 Funkce pro Risk Analyst

### Web Scraping
- Automatické sbírání dat z CHMI API
- Integrace OpenMeteo API jako spolehlivý zdroj meteorologických dat
- Parsování RSS feeds z českých médií
- Analýza obsahu pro rizikové klíčová slova
- Robustní error handling a fallback mechanismy

### GIS Analýza
- Geografické omezení na ČR (volitelný filtr ve UI)
- Výpočet rizik v okolí dodavatelů
- Analýza vzdálenosti od řek (`calculate_river_distance`) a simulace záplav (`analyze_flood_risk_from_rivers(lat, lon)`) – 2‑parametrická DB funkce
- Vizualizace na interaktivní mapě

### Supply Chain Risk Management
- Monitoring dodavatelů VW Group
- Kategorizace podle typu dodavatele
- Rizikové hodnocení a scoring
- Pokročilé GIS funkce pro analýzu rizik

### Deployment a Error Handling
- Robustní database initialization s lepším error handlingem
- Transaction management pro spolehlivé nasazení
- Comprehensive testing suite
- Improved CORS configuration pro frontend-backend komunikaci

## 🤝 Přispívání

Projekt byl vytvořen jako ukázka dovedností pro pohovor. Pro jakékoliv dotazy kontaktujte autora.

## 📄 Licence

Tento projekt je vytvořen pro demonstrační účely.

---

**Vytvořeno pro VW Group Risk Analyst pozici - 2025** 
