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
  - Web scraping reálných dat z CHMI API, OpenMeteo API a RSS feeds
  - Zpracování a validace dat
  - Analýza rizikových klíčových slov
  - Ukládání geografických dat rizikových událostí
  - Komunikace s databází
  - API dokumentace (Swagger)
  - Robustní error handling a transaction management

### 3. PostgreSQL Databáze

- **Technologie**: PostgreSQL, PostGIS, fuzzystrmatch
- **Odpovědnost**:
  - Ukládání rizikových událostí a jejich metadat
  - Ukládání dodavatelů VW Group s rizikovým hodnocením
  - Ukládání geografických bodů pomocí PostGIS
  - Geografické dotazy a operace pomocí PostGIS
  - Výpočet rizik v okolí dodavatelů
  - Pokročilé GIS funkce pro analýzu vzdálenosti od řek

## Datový model

### Tabulka `risk_events`

```sql
CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location GEOGRAPHY(POINT, 4326),  -- Geografická pozice
    event_type VARCHAR(50), -- 'flood', 'protest', 'supply_chain', 'geopolitical'
    severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    source VARCHAR(100), -- 'chmi_api', 'rss', 'manual', 'copernicus', 'openmeteo'
    url TEXT, -- Zdroj dat
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabulka `vw_suppliers`

```sql
CREATE TABLE vw_suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    location GEOGRAPHY(POINT, 4326),  -- Geografická pozice
    category VARCHAR(100), -- 'electronics', 'tires', 'steering', 'brakes'
    risk_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tabulka `rivers`

```sql
CREATE TABLE rivers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    geometry GEOMETRY(POLYGON, 4326),
    river_type VARCHAR(50),
    flow_direction VARCHAR(10),
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
| GET    | /api/test-scraping-improved| Test vylepšeného scrapingu                |

## Zdroje dat

### Reálná data (Web Scraping)

#### CHMI API
- **Endpoint**: `https://hydro.chmi.cz/hpps/`
- **Typ dat**: Meteorologická data a varování
- **Frekvence**: Real-time
- **Status**: Funkční s fallback na OpenMeteo API

#### OpenMeteo API
- **Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Typ dat**: Meteorologická data (teplota, vítr, srážky)
- **Frekvence**: Real-time
- **Status**: Primární zdroj meteorologických dat
- **Výhody**: Bez API klíče, spolehlivé, přesné

#### RSS Feeds
- **Zdroje**: Novinky.cz, Seznam Zprávy, HN.cz, iRozhlas
- **Typ dat**: Zprávy a události
- **Frekvence**: Real-time
- **Status**: Funkční s vylepšenými filtry

### Demo data

#### Dodavatelé VW Group
- **Počet**: 10 ukázkových dodavatelů
- **Kategorie**: Electronics, Tires, Steering, Brakes, Body Parts
- **Rizikové úrovně**: Low, Medium, High, Critical
- **Geografické umístění**: Různé lokace v ČR

## Pokročilé funkce

### GIS Analýza
- **Výpočet vzdálenosti od řek**: Analýza blízkosti hlavních řek ČR
- **Simulace záplav**: Hodnocení rizika záplav na základě vzdálenosti od řek
- **Geografické indexy**: Optimalizace prostorových dotazů
- **PostGIS funkce**: Pokročilé geografické operace

### Error Handling
- **Robustní database initialization**: Lepší error handling při inicializaci
- **Transaction management**: Spolehlivé commit/rollback operace
- **Connection timeout**: Lepší handling připojení k databázi
- **Fallback mechanismy**: Alternativní zdroje dat při selhání

### Testing Suite
- **test_weather_api.py**: Test různých weather APIs
- **test_improved_scraping.py**: Test vylepšeného scrapingu
- **test_current_state.py**: Komplexní test současného stavu
- **test_backend.py**: Test backend funkcí

## Deployment

### Backend (Render.com)
- **Platforma**: Render.com
- **Runtime**: Python 3
- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL + PostGIS
- **URL**: https://risk-analyst.onrender.com

### Frontend (Streamlit Cloud)
- **Platforma**: Streamlit Cloud
- **Framework**: Streamlit
- **URL**: https://memory-map-feature-risk-analyst-frontend-app.onrender.com

### CORS Configuration
- **Frontend URL**: Povoleno v CORS nastavení
- **Wildcard**: Povoleno pro development
- **Security**: Bezpečná komunikace mezi frontend a backend

## Monitoring a Logging

### Backend Logging
- **Structured logging**: Detailní logy všech operací
- **Error tracking**: Sledování chyb a výjimek
- **Performance monitoring**: Monitoring výkonu API
- **Database connection**: Sledování připojení k databázi

### Health Checks
- **API health**: `/` endpoint pro kontrolu dostupnosti
- **Database health**: Kontrola připojení k databázi
- **Scraping health**: Test funkcionality web scrapingu
- **CORS health**: Kontrola komunikace s frontend

## Security

### API Security
- **CORS**: Konfigurované pro bezpečnou komunikaci
- **Input validation**: Pydantic modely pro validaci dat
- **SQL injection protection**: Parametrizované dotazy
- **Error handling**: Bezpečné error messages

### Data Security
- **Environment variables**: Citlivé údaje v environment proměnných
- **Database credentials**: Bezpečné uložení přihlašovacích údajů
- **SSL connections**: Šifrovaná komunikace s databází
- **Input sanitization**: Očištění vstupních dat 