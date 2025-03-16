# MemoryMap - Interaktivní Mapa Vzpomínek

Tento projekt byl vytvořen jako součást přípravy na technický pohovor. Demonstruje praktické dovednosti v oblasti full-stack vývoje, práce s mapovými podklady a zpracování přirozeného jazyka.

## 🌐 Demo Aplikace

- **Frontend**: [https://stanislavhoracekmemorymap.streamlit.app](https://stanislavhoracekmemorymap.streamlit.app)
- **Backend API**: [https://memorymap-api.onrender.com](https://memorymap-api.onrender.com)
- **API Dokumentace**: [https://memorymap-api.onrender.com/docs](https://memorymap-api.onrender.com/docs)

> **Poznámka**: První načtení může trvat až 30 sekund, protože služby běží na free tier hostingu.

## 🚀 Deployment

Aplikace je nasazena na cloudových službách:

### Backend (Render)
- Technologie: FastAPI
- Databáze: PostgreSQL
- Endpoint: https://memorymap-api.onrender.com
- Dokumentace API: https://memorymap-api.onrender.com/docs

### Frontend (Streamlit Cloud)
- Technologie: Streamlit
- URL: https://stanislavhoracekmemorymap.streamlit.app
- Hosting: Streamlit Cloud (Community)

## 💻 Lokální vývoj

1. Naklonujte repozitář:
   ```bash
   git clone https://github.com/moziyuri/memory_map.git
   cd memory_map
   ```

2. Nainstalujte závislosti:
   ```bash
   pip install -r requirements.txt
   ```

3. Nastavte prostředí:
   - Vytvořte soubor `.env` s připojením k databázi:
     ```
     DATABASE_URL=postgresql://username:password@localhost:5432/memorymap
     ```

4. Spusťte aplikaci:
   ```bash
   # V PowerShellu
   ./start.ps1
   ```

## O Projektu

MemoryMap je webová aplikace, která umožňuje uživatelům:
- Ukládat vzpomínky spojené s konkrétními místy na mapě
- Nahrávat hlasové záznamy, které jsou automaticky převedeny na text
- Vizualizovat vzpomínky na interaktivní mapě
- Vyhledávat v uložených vzpomínkách podle místa nebo obsahu

## Technologie

### Backend
- FastAPI (Python)
- PostgreSQL s PostGIS pro geografická data
- Whisper AI pro převod řeči na text

### Frontend
- Streamlit pro uživatelské rozhraní
- Folium pro interaktivní mapy
- Streamlit-Folium pro integraci map

## Struktura Projektu

```
/memorymap
├── frontend/      # Streamlit aplikace
├── backend/       # FastAPI server
├── database/      # SQL skripty pro inicializaci databáze
└── requirements.txt  # Python závislosti
```

## Autor

Vytvořeno jako ukázka technických dovedností pro účely pohovoru.

## Poznámka

Tento projekt slouží jako demonstrace schopností v oblasti full-stack vývoje, práce s geografickými daty a integrace AI modelů. Byl vytvořen s důrazem na čistý kód, dobré programovací praktiky a moderní technologie.

## Project Structure

```
/memorymap
├── frontend/      # Streamlit frontend application
├── backend/       # FastAPI backend service
├── database/      # Database initialization scripts
└── requirements.txt  # Python dependencies
```

## Backend Deployment (Render)

1. Create a new Web Service on Render.com
2. Connect your GitHub repository
3. Configure the following settings:
   - Root Directory: `backend/`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port 10000`
   - Environment Variables:
     - `DATABASE_URL`: Your PostgreSQL connection string

## Frontend Deployment (Local/Streamlit)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the Streamlit application:
   ```bash
   cd frontend
   streamlit run app.py
   ```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DATABASE_URL=postgresql://username:password@host:port/database
```

## API Documentation

Once the backend is running, you can access the API documentation at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Development

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up the database using scripts in the database/ directory
4. Run the backend:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```
5. Run the frontend:
   ```bash
   cd frontend
   streamlit run app.py
   ```

## O aplikaci

MemoryMap AI je aplikace pro ukládání a vizualizaci vzpomínek na mapě. Umožňuje vám:

- Přidávat vzpomínky s textem a lokalizací
- Automaticky analyzovat klíčová slova pomocí AI
- Zobrazovat vzpomínky na interaktivní mapě
- Procházet seznam uložených vzpomínek

## Nové funkce

### Mapové vrstvy

Aplikace nyní podporuje různé mapové vrstvy, které můžete přepínat:

- **Základní mapa** - Standardní mapa z Mapy.cz
- **Historická mapa 19. století** - Historická mapa českých zemí z 19. století
- **Císařské otisky** - Historické katastrální mapy z období Rakouska-Uherska
- **Historické mapy ČÚZK** - Další historické mapy z Českého úřadu zeměměřického a katastrálního

Vrstvy můžete zapínat a vypínat pomocí ovladače vrstev v pravém horním rohu mapy.

### Georeferencování historických názvů míst

Nová funkce umožňuje vyhledávat historické názvy míst a získat jejich současné souřadnice:

1. V postranním panelu najdete sekci "Georeferencování"
2. Zadejte název historického místa (např. "Sudety", "Königgrätz", "Theresienstadt")
3. Vyberte historické období
4. Klikněte na tlačítko "Georeferencovat"
5. Aplikace se pokusí najít odpovídající místo a zobrazit jeho souřadnice

Tato funkce využívá databázi historických názvů míst a OpenStreetMap data pro co nejpřesnější výsledky.

## Technické detaily

### Struktura databáze

Aplikace nyní používá tři hlavní tabulky:

1. **memories** - Ukládá vzpomínky s geografickou lokalizací a klíčovými slovy
2. **place_names** - Obsahuje historické názvy míst s lokalizací a časovým obdobím
3. **osm_data** - Alternativní zdroj dat z OpenStreetMap pro georeferencování

### PostgreSQL rozšíření

Pro plnou funkčnost aplikace jsou vyžadována tyto PostgreSQL rozšíření:

- **PostGIS** - Pro práci s geografickými daty
- **fuzzystrmatch** - Pro hledání podobných názvů pomocí Levenshteinovy vzdálenosti
- **hstore** - Pro ukládání klíč-hodnota párů u OSM dat

### API Endpointy

Aplikace nyní nabízí tyto API endpointy:

- `GET /api/memories` - Získání všech vzpomínek
- `POST /api/analyze` - Přidání nové vzpomínky a analýza klíčových slov pomocí AI
- `POST /georef` - Georeferencování historického názvu místa

Pro více informací o API endpointech navštivte dokumentaci na `http://localhost:8000/docs`.

## Jak aplikaci spustit

### Prerekvizity

Pro spuštění aplikace budete potřebovat:

- Python 3.7 nebo novější
- PostgreSQL databáze s PostGIS rozšířením
- Nainstalované závislosti ze souboru `requirements.txt`

### Nastavení databáze

1. Nainstalujte PostgreSQL a PostGIS rozšíření
2. Vytvořte databázi s názvem `memorymap`:

```bash
# Spusťte následující příkaz pro inicializaci databáze
cd memorymap/backend
psql -U postgres -f init_db.sql
```

### Spuštění backendu

1. Přejděte do adresáře backendu:

```bash
cd memorymap/backend
```

2. Spusťte backend server:

```bash
# V prostředí Windows PowerShell
uvicorn main:app --host localhost --port 8000

# NEBO použijte tento příkaz pro automatické restartování při změnách
uvicorn main:app --host localhost --port 8000 --reload
```

3. Backend API bude dostupné na adrese `http://localhost:8000`
4. Dokumentace API je dostupná na adrese `http://localhost:8000/docs`

### Spuštění frontendu

1. Přejděte do adresáře frontendu:

```bash
cd memorymap/frontend
```

2. Pro spuštění Streamlit aplikace bez uvítací obrazovky:

```bash
# V prostředí Windows PowerShell
python run_silent.py

# NEBO použijte dávkový soubor
.\start_silent.bat
```

3. Alternativně můžete spustit Streamlit přímo:

```bash
streamlit run app.py --server.port 8501 --server.headless=true
```

4. Frontend aplikace bude dostupná na adrese `http://localhost:8501`

## Vkládání dat do aplikace

Data do aplikace můžete vkládat dvěma způsoby:

### Přes webové rozhraní

1. Otevřete webovou aplikaci na adrese `http://localhost:8501`
2. Vyplňte formulář "Přidat novou vzpomínku" vlevo:
   - Zadejte text vzpomínky
   - Zadejte název místa (např. "Praha, Karlův most")
   - Zadejte nebo upravte zeměpisné souřadnice (šířka a délka)
3. Klikněte na tlačítko "Přidat vzpomínku"
4. Vzpomínka bude automaticky analyzována a přidána na mapu

### Přes API (pro pokročilé uživatele)

1. Připravte JSON data ve formátu:

```json
{
  "text": "Vaše vzpomínka zde",
  "location": "Název místa",
  "latitude": 49.8175,
  "longitude": 15.4730,
  "source": "Volitelný zdroj",
  "date": "Volitelné datum"
}
```

2. Odešlete POST požadavek na API endpoint:

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Vaše vzpomínka zde",
    "location": "Název místa",
    "latitude": 49.8175,
    "longitude": 15.4730
  }'
```

## Jak aplikaci sdílet

Pro sdílení aplikace s ostatními uživateli máte několik možností:

### 1. Lokální síť

Pro zpřístupnění aplikace v rámci lokální sítě:

1. Spusťte backend s parametrem `--host 0.0.0.0`:

```bash
cd memorymap/backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

2. Spusťte frontend s parametrem `--server.address 0.0.0.0`:

```bash
cd memorymap/frontend
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

3. Aplikace bude dostupná na adrese `http://VAŠE_IP_ADRESA:8501`
4. Upravte v souboru `app.py` konstantu `API_URL` na hodnotu `http://VAŠE_IP_ADRESA:8000`

### 2. Nasazení na server

Pro nasazení na veřejně dostupný server:

1. Nahrajte aplikaci na server (např. VPS, AWS, Azure)
2. Nastavte databázi PostgreSQL s PostGIS
3. Nakonfigurujte reverse proxy (NGINX nebo Apache) pro zpřístupnění aplikace
4. Spusťte backend a frontend aplikace s příslušnými parametry
5. Nastavte firewall pro povolení portů 8000 a 8501

### 3. Kontejnerizace pomocí Docker

Pro snadné nasazení můžete vytvořit Docker kompozici:

1. Vytvořte Dockerfile pro backend a frontend
2. Vytvořte docker-compose.yml pro orchestraci všech služeb
3. Nasaďte aplikaci pomocí příkazu `docker-compose up -d`

## Řešení problémů

### Backend není dostupný

1. Zkontrolujte, zda běží backend server pomocí příkazu:
   ```bash
   Get-Process -Name uvicorn*
   ```
2. Ujistěte se, že databáze PostgreSQL běží a je správně nakonfigurovaná
3. Zkontrolujte logy backendu pro případné chyby

### Frontend není dostupný

1. Zkontrolujte, zda běží Streamlit proces:
   ```bash
   Get-Process -Name streamlit*
   ```
2. Zkuste spustit aplikaci s detailními logy:
   ```bash
   streamlit run app.py --server.port 8501 --log_level=debug
   ```

### Problém s připojením k databázi

1. Zkontrolujte v souboru `main.py` správnost přihlašovacích údajů k databázi
2. Ujistěte se, že PostgreSQL server běží
3. Ověřte, že databáze `memorymap` existuje a má nainstalované PostGIS rozšíření 