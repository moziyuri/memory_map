# Architektura projektu MemoryMap

> **Aplikace vytvořená za účelem pohovoru** - Tento projekt demonstruje praktické dovednosti v oblasti full-stack vývoje.

## Přehled

MemoryMap je full-stack aplikace se třemi hlavními komponentami:

1. **Frontend** (Streamlit) - Uživatelské rozhraní postavené na Streamlit frameworku
2. **Backend API** (FastAPI) - REST API poskytující přístup k datům
3. **PostgreSQL databáze** - Úložiště pro vzpomínky s PostGIS rozšířením pro geografická data

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│   Frontend      │◄────►│   Backend API   │◄────►│   PostgreSQL    │
│   (Streamlit)   │      │   (FastAPI)     │      │   + PostGIS     │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
     Streamlit               Render.com               Render.com
```

## Komponenty

### 1. Frontend (Streamlit)

- **Technologie**: Streamlit, Folium, Streamlit-Folium
- **Odpovědnost**: 
  - Zobrazení interaktivní mapy s piny reprezentujícími vzpomínky
  - Zobrazení pop-up oken s obsahem vzpomínek po kliknutí na pin
  - Umožnění přidávání nových vzpomínek přímým kliknutím na mapu
  - Formulář pro zadání detailů vzpomínky
  - Vyhledávání a filtrování vzpomínek
  - Komunikace s Backend API

### 2. Backend API (FastAPI)

- **Technologie**: FastAPI, Pydantic, psycopg2
- **Odpovědnost**:
  - Poskytování REST API endpointů
  - Zpracování a validace dat
  - Extrakce klíčových slov z textu vzpomínek
  - Ukládání geografických dat získaných z kliknutí na mapu
  - Komunikace s databází
  - API dokumentace (Swagger)

### 3. PostgreSQL Databáze

- **Technologie**: PostgreSQL, PostGIS, fuzzystrmatch
- **Odpovědnost**:
  - Ukládání vzpomínek a jejich metadat
  - Ukládání geografických bodů (pinů) pomocí PostGIS
  - Geografické dotazy a operace pomocí PostGIS
  - Fulltextové vyhledávání

## Datový model

### Tabulka `memories`

```sql
CREATE TABLE memories (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
    keywords TEXT[],
    source TEXT,
    date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpointy

### Backend API

| Metoda | Endpoint            | Popis                                     |
|--------|---------------------|-------------------------------------------|
| GET    | /                   | Základní health check                     |
| GET    | /api/memories       | Získání všech vzpomínek včetně souřadnic pro zobrazení pinů |
| GET    | /api/memories/{id}  | Získání konkrétní vzpomínky podle ID      |
| POST   | /api/analyze        | Přidání nové vzpomínky, zpracování souřadnic z kliknutí na mapu a extrakce klíčových slov |
| GET    | /api/debug          | Diagnostika stavu API a připojení k DB    |

## Nasazení

### Frontend (Streamlit Cloud)

- **URL**: https://stanislavhoracekmemorymap.streamlit.app
- **Proces nasazení**: Automatický deployment z GitHub repozitáře

### Backend API (Render.com)

- **URL**: https://memory-map.onrender.com
- **Proces nasazení**: 
  1. Web Service na Render.com
  2. Build Command: `pip install -r backend/requirements.txt && python backend/direct_db_init.py`
  3. Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

### PostgreSQL (Render.com)

- **Typ**: Managed PostgreSQL databáze
- **Konfigurace**:
  - PostGIS rozšíření
  - Automatické zálohování
  - Connection string propojený s Backend API

## Workflow aplikace

1. Uživatel navštíví Streamlit aplikaci
2. Frontend načte vzpomínky z Backend API
3. Vzpomínky jsou zobrazeny jako piny na interaktivní mapě
4. Uživatel může kliknout na pin pro zobrazení obsahu vzpomínky v pop-up okně
5. Při přidání nové vzpomínky:
   - Uživatel klikne na tlačítko "Přidat vzpomínku"
   - Poté klikne na požadované místo na mapě
   - Vyplní formulář s detaily vzpomínky
   - Frontend odešle data včetně souřadnic kliknutí do Backend API
   - Backend extrahuje klíčová slova
   - Backend uloží data do PostgreSQL databáze
   - Backend vrátí aktualizovaný seznam vzpomínek
   - Na mapě se objeví nový pin

## Interaktivní prvky mapy

### Piny

- Piny jsou interaktivní značky na mapě reprezentující jednotlivé vzpomínky
- Každý pin má:
  - Pozici určenou geografickými souřadnicemi (latitude, longitude)
  - Návaznost na konkrétní vzpomínku v databázi
  - Pop-up okno, které se aktivuje po kliknutí

### Pop-up okna

- Pop-up okna se zobrazují po kliknutí na pin
- Obsahují:
  - Text vzpomínky
  - Název místa
  - Datum a zdroj (pokud byly zadány)
  - Automaticky extrahovaná klíčová slova

### Přidávání vzpomínek

- Přímé kliknutí na mapu v režimu přidávání
- Automatická extrakce souřadnic z místa kliknutí
- Reverzní geokódování pro získání názvu místa (pokud je dostupné)

## Monitoring a diagnostika

Pro diagnostiku a monitoring aplikace slouží:

- **API endpoint** `/api/debug` - Poskytuje informace o:
  - Stavu připojení k databázi
  - Verzi PostgreSQL a PostGIS
  - Dostupných tabulkách
  - Počtu uložených vzpomínek
  - Environment proměnných (bezpečně)

- **Swagger dokumentace** na `/docs` - Interaktivní dokumentace API

## Bezpečnost

- Použití CORS policy pro omezení přístupu k API
- PostgreSQL připojení přes connection string s heslem
- Žádné ukládání citlivých údajů do kódu
- Validace vstupních dat pomocí Pydantic modelů

## Účel projektu

Aplikace MemoryMap byla vytvořena jako ukázka technických dovedností pro účely pracovního pohovoru. Demonstruje praktické schopnosti v oblastech:

- Vývoje full-stack webových aplikací
- Práce s geografickými daty a interaktivními mapami
- Návrhu a implementace REST API
- Integrace moderních technologií a frameworků 