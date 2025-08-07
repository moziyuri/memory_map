# VW Group Risk Analyst Dashboard

> **Aplikace vytvořená za účelem pohovoru na pozici Risk Analyst** - Projekt demonstruje praktické dovednosti v oblasti full-stack vývoje, web scraping, GIS analýzy a supply chain risk management.

Interaktivní dashboard pro analýzu rizikových událostí v dodavatelském řetězci VW Group s využitím reálných dat z CHMI API a RSS feeds.

![Risk Analyst Dashboard Preview](https://i.imgur.com/example.png)

## 🌟 Funkce

- **Interaktivní mapa rizik** zobrazující rizikové události a dodavatele VW Group
- **Web scraping** reálných dat z CHMI (počasí) a RSS feeds (zprávy)
- **Filtry** podle typu události, závažnosti, zdroje dat a časového období
- **Analýza dodavatelů** s rizikovým hodnocením a kategorizací
- **Statistiky a trendy** rizikových událostí v čase
- **Geografické omezení** na území České republiky
- **Responzivní design** pro používání na počítači i mobilních zařízeních

## 🔗 Odkazy

- **Frontend**: [https://stanislavhoracekmemorymap.streamlit.app](https://stanislavhoracekmemorymap.streamlit.app)
- **Backend API**: [https://risk-analyst.onrender.com](https://risk-analyst.onrender.com)
- **API dokumentace**: [https://risk-analyst.onrender.com/docs](https://risk-analyst.onrender.com/docs)

## 📖 O aplikaci

VW Group Risk Analyst Dashboard je interaktivní aplikace pro analýzu rizik v dodavatelském řetězci, která vznikla jako ukázka dovedností pro účely pohovoru na pozici Risk Analyst. Projekt demonstruje schopnosti v těchto oblastech:

### Účel a vznik
Aplikace byla vytvořena specificky pro demonstraci technických dovedností v kontextu pracovního pohovoru na pozici Risk Analyst ve VW Group. Cílem bylo vytvořit funkční dashboard, který ukáže schopnosti práce s:
- Web scraping reálných dat
- GIS analýzou a geografickými daty
- Supply chain risk management
- Moderními technologiemi a frameworks

### Koncept
Základní myšlenkou je monitoring rizikových událostí, které mohou ovlivnit dodavatelský řetězec VW Group. Aplikace:
- Sbírá reálná data z CHMI API (počasí) a RSS feeds (zprávy)
- Analyzuje rizika v okolí dodavatelů VW Group
- Poskytuje přehledné statistiky a trendy
- Umožňuje filtrování a analýzu podle různých kritérií

### Technologická ukázka
Aplikace demonstruje zkušenosti s:
- Web scraping a práci s externími API
- GIS analýzou a geografickými daty
- Supply chain risk management
- Vývojem interaktivních mapových rozhraní
- Návrhem a implementací REST API
- Nasazením aplikací na cloud platformy

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
│   ├── init_risk_db.py    # Inicializační skript pro databázi
│   ├── test_risk_db.py    # Test připojení k databázi
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
- **CHMI API** - Meteorologická data a varování (počasí, povodně)
- **RSS feeds** - Zprávy z českých médií (Novinky.cz, Seznam Zprávy, HN.cz, iRozhlas)

### Demo data
- **Dodavatelé VW Group** - Fiktivní dodavatelé s rizikovým hodnocením
- **Rizikové události** - Historické události pro demonstraci funkcí

## 🚀 Rychlý start

### Lokální spuštění

1. **Klonování repozitáře**
   ```bash
   git clone https://github.com/username/risk-analyst-dashboard.git
   cd risk-analyst-dashboard
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
- Parsování RSS feeds z českých médií
- Analýza obsahu pro rizikové klíčová slova

### GIS Analýza
- Geografické omezení na ČR
- Výpočet rizik v okolí dodavatelů
- Vizualizace na interaktivní mapě

### Supply Chain Risk Management
- Monitoring dodavatelů VW Group
- Kategorizace podle typu dodavatele
- Rizikové hodnocení a scoring

## 🤝 Přispívání

Projekt byl vytvořen jako ukázka dovedností pro pohovor. Pro jakékoliv dotazy kontaktujte autora.

## 📄 Licence

Tento projekt je vytvořen pro demonstrační účely.

---

**Vytvořeno pro VW Group Risk Analyst pozici - 2025** 
