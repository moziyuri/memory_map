# Architektura projektu VW Group Risk Analyst Dashboard

> **Aplikace vytvořená za účelem pohovoru na pozici Risk Analyst** - Tento projekt demonstruje praktické dovednosti v oblasti full-stack vývoje, web scraping, GIS analýzy a supply chain risk management.

## Přehled

VW Group Risk Analyst Dashboard je full-stack aplikace se třemi hlavními komponentami:

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

## Komponenty

### 1. Frontend (Streamlit)

- **Technologie**: Streamlit, Folium, Streamlit-Folium, Pandas
- **Odpovědnost**: 
  - Zobrazení interaktivní mapy s rizikovými událostmi a dodavateli VW Group
  - Filtry podle typu události, závažnosti, zdroje dat a časového období
  - Statistiky a trendy rizikových událostí
  - Analýza dodavatelů s rizikovým hodnocením
  - Geografické omezení na území České republiky
  - Komunikace s Backend API

### 2. Backend API (FastAPI)

- **Technologie**: FastAPI, Pydantic, psycopg2, Requests, xml.etree.ElementTree
- **Odpovědnost**:
  - Poskytování REST API endpointů
  - Web scraping reálných dat z CHMI API a RSS feeds
  - Zpracování a validace dat
  - Analýza rizikových klíčových slov
  - Ukládání geografických dat rizikových událostí
  - Komunikace s databází
  - API dokumentace (Swagger)

### 3. PostgreSQL Databáze

- **Technologie**: PostgreSQL, PostGIS, fuzzystrmatch
- **Odpovědnost**:
  - Ukládání rizikových událostí a jejich metadat
  - Ukládání dodavatelů VW Group s rizikovým hodnocením
  - Ukládání geografických bodů pomocí PostGIS
  - Geografické dotazy a operace pomocí PostGIS
  - Výpočet rizik v okolí dodavatelů

## Datový model

### Tabulka `risk_events`

```sql
CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source VARCHAR(50) NOT NULL,
    location GEOGRAPHY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabulka `vw_suppliers`

```sql
CREATE TABLE vw_suppliers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    location GEOGRAPHY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpointy

### Backend API

| Metoda | Endpoint                    | Popis                                     |
|--------|----------------------------|-------------------------------------------|
| GET    | /                          | Základní health check                     |
| GET    | /api/risks                 | Získání všech rizikových událostí         |
| GET    | /api/suppliers             | Získání všech dodavatelů VW Group         |
| GET    | /api/analysis/risk-map     | Získání dat pro mapu rizik                |
| GET    | /api/scrape/chmi           | Spuštění web scraping z CHMI API          |
| GET    | /api/scrape/rss            | Spuštění web scraping z RSS feeds         |
| GET    | /api/scrape/run-all        | Spuštění všech web scrapers               |
| GET    | /api/test-chmi             | Test CHMI API endpointů                   |
| GET    | /api/test-openmeteo        | Test OpenMeteo API                        |
| GET    | /docs                      | API dokumentace (Swagger)                 |

## Zdroje dat

### Reálná data (Web Scraping)

#### CHMI API
- **Endpointy**: 
  - `https://hydro.chmi.cz/hpps/` (funkční)
  - `https://hydro.chmi.cz/hpps/index.php` (funkční)
  - `https://hydro.chmi.cz/hpps/hpps_act.php` (nefunkční)
  - `https://hydro.chmi.cz/hpps/hpps_act_quick.php` (nefunkční)
- **Typ dat**: Meteorologická varování, povodňové informace
- **Frekvence**: Při volání `/api/scrape/chmi`
- **Fallback**: OpenMeteo API při neúspěchu CHMI

#### OpenMeteo API
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Typ dat**: Meteorologická data (teplota, vítr, srážky)
- **Výhody**: Bezplatné, bez API key, spolehlivé
- **Frekvence**: Při volání `/api/scrape/chmi` jako fallback

#### RSS Feeds
- **Zdroje**:
  - `https://www.novinky.cz/rss`
  - `https://www.seznamzpravy.cz/rss`
  - `https://hn.cz/rss/2`
  - `https://www.irozhlas.cz/rss/irozhlas`
- **Typ dat**: Zprávy z českých médií
- **Frekvence**: Při volání `/api/scrape/rss`

### Demo data
- **Dodavatelé VW Group**: Fiktivní dodavatelé s rizikovým hodnocením
- **Rizikové události**: Historické události pro demonstraci funkcí

## Nasazení

### Frontend (Streamlit Cloud)

- **URL**: https://stanislavhoracekmemorymap.streamlit.app
- **Proces nasazení**: Automatický deployment z GitHub repozitáře

### Backend API (Render.com)

- **URL**: https://risk-analyst.onrender.com
- **Proces nasazení**: 
  1. Web Service na Render.com
  2. Build Command: `pip install -r requirements.txt && python init_risk_db.py`
  3. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  4. Environment Variables:
     - `RISK_DATABASE_URL`: PostgreSQL connection string
     - `DATABASE_URL`: PostgreSQL connection string

### PostgreSQL (Render.com)

- **Databáze**: `risk_analyst`
- **Rozšíření**: PostGIS pro geografické operace
- **Inicializace**: Automaticky při build procesu pomocí `init_risk_db.py`

## Bezpečnost a optimalizace

### Render.com Free plán limity
- **Web Service**: 512 MB RAM, uspání po 15 minutách neaktivity
- **PostgreSQL**: 1 GB prostoru, max 10 současných připojení

### Optimalizace
- Geografické omezení na ČR pro snížení datového objemu
- Cachování dat v session state
- Efektivní dotazy s PostGIS indexy
- Minimalizace API volání

## Monitoring a logování

### Backend logování
- Detailní print statements pro debugging
- Error handling s traceback
- API response logging

### Frontend monitoring
- Session state pro cachování
- Error handling pro API volání
- User feedback pro všechny operace 