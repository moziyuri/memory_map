# MemoryMap

> **Aplikace vytvořená za účelem pohovoru** - Projekt demonstruje praktické dovednosti v oblasti full-stack vývoje, práce s mapovými podklady a zpracování geografických dat.

Aplikace pro ukládání a vizualizaci vzpomínek spojených s konkrétními geografickými místy na mapě.

![MemoryMap Preview](https://i.imgur.com/example.png)

## 🌟 Funkce

- **Interaktivní mapa** zobrazující vzpomínky ve formě pinů na mapě
- **Přidávání vzpomínek přímo kliknutím na mapu** s textem, místem, datem a zdrojem
- **Pop-up okna** pro rychlé zobrazení obsahu vzpomínek přímo na mapě
- **Automatická extrakce klíčových slov** z textu vzpomínek
- **Vyhledávání a filtrování** vzpomínek podle textu, klíčových slov, místa a data
- **Responzivní design** pro používání na počítači i mobilních zařízeních

## 🔗 Odkazy

- **Frontend**: [https://stanislavhoracekmemorymap.streamlit.app](https://stanislavhoracekmemorymap.streamlit.app)
- **Backend API**: [https://memory-map.onrender.com](https://memory-map.onrender.com)
- **API dokumentace**: [https://memory-map.onrender.com/docs](https://memory-map.onrender.com/docs)
- **API diagnostika**: [https://memory-map.onrender.com/api/debug](https://memory-map.onrender.com/api/debug)

## 📖 O aplikaci

MemoryMap je interaktivní aplikace pro mapování vzpomínek, která vznikla jako ukázka dovedností pro účely pohovoru. Projekt demonstruje schopnosti v těchto oblastech:

### Účel a vznik
Aplikace byla vytvořena specificky pro demonstraci technických dovedností v kontextu pracovního pohovoru. Cílem bylo vytvořit funkční a esteticky přívětivou aplikaci, která ukáže schopnosti práce s moderními technologiemi a frameworks.

### Koncept
Základní myšlenkou je možnost ukládat vzpomínky a příběhy spojené s konkrétními místy na mapě. Uživatelé mohou:
- Procházet mapu a zobrazovat existující vzpomínky kliknutím na pin
- Přidávat nové vzpomínky jednoduchým kliknutím na místo na mapě
- Vyhledávat vzpomínky podle obsahu, místa nebo automaticky extrahovaných klíčových slov

### Technologická ukázka
Aplikace demonstruje zkušenosti s:
- Tvorbou moderních full-stack aplikací
- Vývojem interaktivních mapových rozhraní
- Práci s geografickými daty a PostgreSQL/PostGIS
- Návrhem a implementací REST API
- Nasazením aplikací na cloud platformy

## 🏗️ Architektura

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

*Podrobnější popis architektury najdete v [ARCHITECTURE.md](ARCHITECTURE.md)*

## 🧰 Technologie

### Frontend
- **Streamlit** - Framework pro rychlé vytváření datových aplikací
- **Folium** - Knihovna pro vytváření interaktivních map s podporou pop-up oken a pinů
- **Streamlit-Folium** - Integrace Folium map do Streamlit aplikací
- **Python** - Programovací jazyk

### Backend
- **FastAPI** - Moderní, rychlý (vysoce výkonný) webový framework pro tvorbu API
- **Pydantic** - Validace dat a nastavení pomocí anotací typu Python
- **PostgreSQL** - Relační databáze
- **PostGIS** - Prostorové rozšíření pro PostgreSQL
- **psycopg2** - PostgreSQL adaptér pro Python
- **uvicorn** - ASGI server pro Python

## 🧱 Struktura projektu

```
memorymap/
├── frontend/              # Streamlit aplikace
│   ├── app.py             # Hlavní soubor aplikace
│   ├── utils.py           # Pomocné funkce
│   └── requirements.txt   # Závislosti pro frontend
│
├── backend/               # FastAPI backend
│   ├── main.py            # Hlavní soubor API
│   ├── database.py        # Konfigurace databáze
│   ├── models.py          # Pydantic modely
│   ├── direct_db_init.py  # Inicializační skript pro databázi
│   └── requirements.txt   # Závislosti pro backend
│
├── README.md              # Tento soubor
├── ARCHITECTURE.md        # Detailní popis architektury
└── USER_GUIDE.md          # Uživatelská příručka
```

## 🚀 Nasazení

### Frontend (Streamlit Cloud)

1. Automatický deployment z GitHub repozitáře
2. Nastavení v `.streamlit/secrets.toml`:
   ```toml
   [api]
   url = "https://memory-map.onrender.com"
   ```

### Backend API (Render.com)

1. Vytvoření Web Service na Render.com
2. Build Command:
   ```
   pip install -r backend/requirements.txt && python backend/direct_db_init.py
   ```
3. Start Command:
   ```
   cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. Environment Variables:
   ```
   DATABASE_URL=postgres://[username]:[password]@[host]:[port]/[database]
   ```

### PostgreSQL (Render.com)

1. Vytvoření PostgreSQL databáze na Render.com
2. Aktivace PostGIS rozšíření:
   ```sql
   CREATE EXTENSION postgis;
   CREATE EXTENSION fuzzystrmatch;
   ```
3. Inicializace databázové struktury pomocí `direct_db_init.py`

### Limity Free plánu a optimalizace

> ⚠️ **Důležité**: Render.com Free plán má následující limity:
> - Web Service: 512 MB RAM, uspání po 15 minutách neaktivity
> - PostgreSQL: 1 GB prostoru, max 10 současných připojení
>
> Pro detailní informace o omezeních a praktické tipy k optimalizaci viz sekce [Limity free plánu](DEPLOYMENT.md#6-limity-free-plánu-na-rendercom-a-jejich-dodržování) v dokumentu DEPLOYMENT.md.

## 📦 API Endpointy

| Metoda | Endpoint            | Popis                                     |
|--------|---------------------|-------------------------------------------|
| GET    | /                   | Základní health check                     |
| GET    | /api/memories       | Získání všech vzpomínek                   |
| GET    | /api/memories/{id}  | Získání konkrétní vzpomínky podle ID      |
| POST   | /api/analyze        | Přidání nové vzpomínky a extrakce klíčových slov |
| GET    | /api/debug          | Diagnostika stavu API a připojení k DB    |

## 📝 Použití

Detailní návod na používání aplikace najdete v [uživatelské příručce](USER_GUIDE.md).

### Rychlý start:

1. Otevřete [aplikaci](https://stanislavhoracekmemorymap.streamlit.app)
2. Prozkoumejte mapu s existujícími vzpomínkami kliknutím na piny
3. Přidejte vlastní vzpomínku kliknutím na požadované místo na mapě
4. Vyhledávejte a filtrujte vzpomínky dle potřeby

## 🧪 Lokální vývoj

### Prerekvizity

- Python 3.9+
- PostgreSQL s PostGIS rozšířením

### Nastavení projektu

1. Klonování repozitáře:
   ```bash
   git clone https://github.com/stanislavhoracek/memorymap.git
   cd memorymap
   ```

2. Instalace závislostí pro backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Instalace závislostí pro frontend:
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

4. Konfigurace databáze:
   - Vytvořte PostgreSQL databázi
   - Aktivujte PostGIS rozšíření
   - Nastavte proměnnou prostředí `DATABASE_URL`

5. Inicializace databáze:
   ```bash
   cd backend
   python direct_db_init.py
   ```

6. Spuštění backend API:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

7. Spuštění frontend aplikace:
   ```bash
   cd frontend
   streamlit run app.py
   ```

## 🤝 Přispívání

Příspěvky jsou vítány! Pokud chcete přispět k projektu:

1. Forkněte repozitář
2. Vytvořte novou větev (`git checkout -b feature/amazing-feature`)
3. Commitněte vaše změny (`git commit -m 'Add some amazing feature'`)
4. Pushněte do větve (`git push origin feature/amazing-feature`)
5. Vytvořte Pull Request

## 📄 Licence

Distribuováno pod MIT licencí. Viz `LICENSE` pro více informací.

## 📞 Kontakt

Stanislav Horáček - [stanislav.horacek@email.cz](mailto:stanislav.horacek@email.cz)

Odkaz na projekt: [https://github.com/stanislavhoracek/memorymap](https://github.com/stanislavhoracek/memorymap) 