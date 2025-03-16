# Nasazení MemoryMap aplikace na Render.com

> **Aplikace vytvořená za účelem pohovoru** - Tento projekt demonstruje praktické dovednosti v oblasti full-stack vývoje.

Tento dokument obsahuje podrobný návod, jak nasadit MemoryMap aplikaci na platformu Render.com.

## Přehled

Pro plně funkční nasazení potřebujeme:
1. PostgreSQL databázi s PostGIS rozšířením
2. Backend API (FastAPI)
3. Frontend (Streamlit Cloud)

## 1. Vytvoření PostgreSQL databáze na Render.com

1. Přihlaste se na [Render.com](https://render.com)
2. V horní navigaci klikněte na "New +" a vyberte "PostgreSQL"
3. Vyplňte formulář:
   - **Name**: `memory-map-db` (nebo jiný vámi zvolený název)
   - **Database**: `memorymap`
   - **User**: Ponechte automaticky generovaného uživatele
   - **Region**: Vyberte region nejblíže vašim uživatelům (např. `Frankfurt (EU Central)`)
   - **PostgreSQL Version**: Vyberte nejnovější (například `14`)
   - **Instance Type**: Pro testování stačí `Free` plán

4. Klikněte na "Create Database"

5. Po vytvoření databáze přejděte do detailu databáze
   - Poznamenejte si "Internal Database URL"
   - Tento connection string budete potřebovat pro nastavení Backend API

6. Aktivujte PostGIS rozšíření
   - V detailu databáze klikněte na "Shell" v horní navigaci
   - Připojte se k databázi příkazem: `psql`
   - Aktivujte rozšíření:
     ```sql
     CREATE EXTENSION postgis;
     CREATE EXTENSION fuzzystrmatch;
     ```
   - Ověřte, že rozšíření byla aktivována:
     ```sql
     \dx
     ```
   - Odpojte se z psql: `\q`

## 2. Vytvoření Backend API služby na Render.com

1. V horní navigaci klikněte na "New +" a vyberte "Web Service"

2. Propojte s GitHub repozitářem
   - Vyberte "Connect account" a autorizujte přístup k vašemu GitHub účtu
   - Vyberte repozitář s MemoryMap aplikací

3. Vyplňte formulář:
   - **Name**: `memory-map` (nebo jiný vámi zvolený název)
   - **Environment**: `Python 3`
   - **Region**: Vyberte stejný region jako pro databázi
   - **Branch**: `main` (nebo jiná větev s produkčním kódem)
   - **Build Command**: 
     ```
     pip install -r backend/requirements.txt && python backend/direct_db_init.py
     ```
   - **Start Command**: 
     ```
     cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: Pro testování stačí `Free` plán

4. Klikněte na "Advanced" pro nastavení pokročilých možností

5. V sekci "Environment Variables" přidejte následující proměnné:
   - Klíč: `DATABASE_URL`
   - Hodnota: Internal Database URL z kroku 1.5 (například `postgres://user:password@host:port/memorymap`)

6. Klikněte na "Create Web Service"

7. Služba se začne vytvářet a nasazovat. Tento proces může trvat několik minut.

8. Po úspěšném nasazení získáte URL vašeho API (například `https://memory-map.onrender.com`)

9. Otestujte API:
   - Navštivte `https://vaše-api-url/docs` pro přístup k Swagger dokumentaci
   - Vyzkoušejte endpoint `/api/debug` pro ověření připojení k databázi

## 3. Nasazení Frontendu na Streamlit Cloud

1. Přihlaste se na [Streamlit Cloud](https://share.streamlit.io/)

2. Klikněte na "New app"

3. Vyplňte formulář:
   - **Repository**: URL vašeho GitHub repozitáře
   - **Branch**: `main` (nebo jiná větev s produkčním kódem)
   - **Main file path**: `frontend/app.py`

4. Klikněte na "Advanced settings"

5. V sekci "Secrets" přidejte následující konfiguraci:
   ```toml
   [api]
   url = "https://vaše-api-url"  # URL z kroku 2.8, například "https://memory-map.onrender.com"
   ```

6. Klikněte na "Deploy!"

7. Aplikace se začne nasazovat. Tento proces může trvat několik minut.

8. Po úspěšném nasazení získáte URL vašeho frontendu (například `https://username-memorymap.streamlit.app`)

## 4. Ověření funkčnosti

1. Otevřete frontend aplikaci ve webovém prohlížeči

2. Zkontrolujte, zda se správně načítá mapa s interaktivními piny

3. Zkuste přidat novou vzpomínku:
   - Klikněte na tlačítko "Přidat vzpomínku" v bočním panelu
   - Klikněte na místo na mapě, kam chcete vzpomínku umístit
   - Vyplňte text vzpomínky a další detaily
   - Odešlete formulář
   - Ověřte, že se nový pin objevil na mapě

4. Zkontrolujte funkcionalitu pop-up oken:
   - Klikněte na libovolný pin na mapě
   - Mělo by se otevřít pop-up okno s detaily vzpomínky

## 5. Monitorování a údržba

### Monitorování backend služby

1. V Render dashboardu přejděte do detailu vaší Web Service
2. V záložce "Logs" můžete sledovat logy aplikace
3. V záložce "Metrics" najdete grafy vytížení

### Monitorování databáze

1. V Render dashboardu přejděte do detailu vaší PostgreSQL databáze
2. V záložce "Metrics" najdete grafy využití

### Aktualizace aplikace

1. Po pushnutí změn do GitHub repozitáře se automaticky spustí nové nasazení
2. Průběh nasazení můžete sledovat v Render dashboardu

### Zálohování databáze

Render.com automaticky vytváří zálohy vaší PostgreSQL databáze:
- Na free plánu se zálohy uchovávají jen 1 den
- Na placených plánech se zálohy uchovávají 7-30 dní

## 6. Limity free plánu na Render.com a jejich dodržování

Pro zajištění, že vaše aplikace zůstane v rámci limitů free plánu, je důležité znát tato omezení a optimalizovat nasazení:

### Web Service (Backend API)

- **Automatické uspání**: Služba se automaticky uspí po 15 minutách neaktivity
  - *Důsledek*: První požadavek po období neaktivity může trvat až 30 sekund
  - *Řešení*: Informujte uživatele o možném delším načítání při prvním přístupu
  
- **Omezený výkon**:
  - CPU: 0.1 vCPU (sdílený)
  - RAM: 512 MB
  - *Optimalizace*: Minimalizujte náročné operace a paměťové nároky
  
- **Limit build minut**: 500 minut měsíčně
  - *Optimalizace*: Minimalizujte počet zbytečných deploymentů
  
- **Omezený diskový prostor**: 1 GB storage
  - *Optimalizace*: Ukládejte pouze nezbytná data, neponechávejte v kódu velké soubory (obrázky, veřejné klíče)

### PostgreSQL database

- **Velikost databáze**: Limit 1 GB
  - *Optimalizace*: 
    - Pravidelně monitorujte velikost databáze
    - Neukládejte velké soubory přímo do databáze
    - Omezte počet a velikost záznamů
  
- **Připojení**: Max 10 současných připojení
  - *Optimalizace*: Správně uzavírejte databázová spojení, používejte connection pooling
  
- **Výkon**: Omezený výpočetní výkon
  - *Optimalizace*: Optimalizujte dotazy, používejte indexy, vyhněte se komplexním JOIN operacím
  
- **Automatické pozastavení databáze**: Po 90 dnech nepoužívání
  - *Důležité*: Pro zachování dat navštěvujte aplikaci alespoň jednou za 3 měsíce

### Praktické kroky pro optimalizaci

1. **Minimalizujte velikost databáze**:
   - Omezte ukládané textové vzpomínky na rozumnou délku (např. max 5000 znaků)
   - Neukládejte obrázky nebo jiná velká binární data do databáze
   - Paginujte velké datové sady v API

2. **Optimalizujte backend kód**:
   - Používejte cache pro často načítaná data
   - Efektivně zpracovávejte požadavky API
   - Minimalizujte závislosti a velikost deployment balíčku

3. **Nastavte monitoring**:
   - Pravidelně kontrolujte velikost databáze pomocí dotazu:
     ```sql
     SELECT pg_size_pretty(pg_database_size('memorymap'));
     ```
   - Sledujte počet záznamů v tabulce vzpomínek

4. **Nastavte stránkování vzpomínek**:
   - Při velkém množství vzpomínek upravte API pro načítání po částech
   - Ve frontendu implementujte lazy-loading pinů na mapě

5. **Zvažte automatické čištění**:
   - Implementujte mechanismus pro automatické mazání starých nebo málo používaných vzpomínek
   - Přidejte možnost komprese textu vzpomínek

## 7. Postup při řešení problémů

### Backend API není dostupné

1. Zkontrolujte logy v Render dashboardu
2. Ověřte, že proměnná prostředí `DATABASE_URL` je správně nastavena
3. Zkontrolujte build command a start command 

### Databáze není dostupná

1. Zkontrolujte status databáze v Render dashboardu
2. Ověřte, že rozšíření PostGIS je aktivováno
3. Zkontrolujte connection string

### Frontend nemůže komunikovat s backendem

1. Ověřte, že v Streamlit secrets je správně nastavena URL backendu
2. Zkontrolujte CORS nastavení v backendu (soubor `main.py`)
3. Zkontrolujte, zda frontend používá správný API endpoint

### Piny nebo pop-up okna nefungují správně

1. Zkontrolujte, zda frontend správně zpracovává geografické souřadnice z API
2. Ověřte, že Folium knihovna je správně nakonfigurovaná
3. Zkontrolujte JavaScript konzoli v prohlížeči pro případné chyby

### Překročení limitů free plánu

1. Zkontrolujte využití zdrojů v Render dashboardu
2. Pokud se blížíte k limitům, implementujte doporučené optimalizace
3. V krajním případě můžete vytvořit novou instanci služby a migrovat data

## 8. Přechod na placené plány

Pro produkční nasazení doporučujeme přejít na placené plány, které nabízejí:

1. **Pro PostgreSQL**:
   - Větší úložiště
   - Delší historie záloh
   - Lepší výkon

2. **Pro Web Service**:
   - Garantovaná dostupnost
   - Více výpočetních zdrojů
   - Žádné uspávání služby (na free plánu se služba uspí po 15 minutách neaktivity)

## 9. Další kroky

- Přidejte vlastní doménu k vašim službám
- Nastavte SSL certifikáty (Render.com poskytuje automaticky)
- Implementujte autentizaci uživatelů
- Nastavte monitorovací alerty
- Rozšiřte funkce pro piny a pop-up okna (např. různé barvy podle kategorií vzpomínek)

## Příloha: Užitečné příkazy pro PostgreSQL

```sql
-- Vytvoření PostGIS rozšíření
CREATE EXTENSION postgis;
CREATE EXTENSION fuzzystrmatch;

-- Kontrola nainstalovaných rozšíření
\dx

-- Kontrola tabulek
\dt

-- Získání informací o PostGIS verzi
SELECT PostGIS_version();

-- Kontrola počtu záznamů v tabulce memories
SELECT COUNT(*) FROM memories;

-- Kontrola uložených souřadnic pinů
SELECT id, location, ST_AsText(coordinates) FROM memories;

-- Kontrola velikosti databáze
SELECT pg_size_pretty(pg_database_size('memorymap'));

-- Kontrola velikosti tabulky memories
SELECT pg_size_pretty(pg_total_relation_size('memories'));

-- Oprava případných problémů s geografickými daty
UPDATE memories SET coordinates = ST_SetSRID(ST_MakePoint(
    ST_X(coordinates::geometry),
    ST_Y(coordinates::geometry)
), 4326)::geography;
```

## O projektu

MemoryMap je aplikace vytvořená za účelem demonstrace technických dovedností při pracovním pohovoru. Projekt ukazuje schopnost vytvořit full-stack aplikaci s interaktivní mapou, geografickými daty a moderním uživatelským rozhraním. 