# Nasazení VW Group Risk Analyst Dashboard

> **Aplikace vytvořená za účelem pohovoru na pozici Risk Analyst** - Tento projekt demonstruje praktické dovednosti v oblasti full-stack vývoje, web scraping, GIS analýzy a supply chain risk management.

Tento dokument obsahuje podrobný návod, jak nasadit VW Group Risk Analyst Dashboard na platformu Render.com.

## Přehled

Pro plně funkční nasazení potřebujeme:
1. PostgreSQL databázi s PostGIS rozšířením
2. Backend API (FastAPI)
3. Frontend (Streamlit Cloud)

## 1. Vytvoření PostgreSQL databáze na Render.com

1. Přihlaste se na [Render.com](https://render.com)
2. V horní navigaci klikněte na "New +" a vyberte "PostgreSQL"
3. Vyplňte formulář:
   - **Name**: `risk-analyst-db` (nebo jiný vámi zvolený název)
   - **Database**: `risk_analyst`
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
   - Vyberte repozitář s Risk Analyst aplikací
   - **Branch**: `feature/risk-analyst`

3. Vyplňte formulář:
   - **Name**: `risk-analyst` (nebo jiný vámi zvolený název)
   - **Environment**: `Python 3`
   - **Region**: Vyberte stejný region jako pro databázi
   - **Branch**: `feature/risk-analyst`
   - **Build Command**: 
     ```
     pip install -r backend/requirements.txt && python backend/init_risk_db.py
     ```
   - **Start Command**: 
     ```
     cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type**: Pro testování stačí `Free` plán

4. Klikněte na "Advanced" pro nastavení pokročilých možností

5. V sekci "Environment Variables" přidejte následující proměnné:
   - Klíč: `RISK_DATABASE_URL`
   - Hodnota: Internal Database URL z kroku 1.5 (například `postgresql://user:password@host:port/risk_analyst`)

6. Klikněte na "Create Web Service"

7. Služba se začne vytvářet a nasazovat. Tento proces může trvat několik minut.

8. Po úspěšném nasazení získáte URL vašeho API (například `https://risk-analyst.onrender.com`)

9. Otestujte API:
   - Navštivte `https://vaše-api-url/docs` pro přístup k Swagger dokumentaci
   - Vyzkoušejte endpoint `/` pro ověření připojení k databázi

## 3. Nasazení Frontendu na Streamlit Cloud

1. Přihlaste se na [Streamlit Cloud](https://share.streamlit.io/)

2. Klikněte na "New app"

3. Vyplňte formulář:
   - **Repository**: URL vašeho GitHub repozitáře
   - **Branch**: `feature/risk-analyst`
   - **Main file path**: `frontend/app.py`

4. Klikněte na "Advanced settings"

5. V sekci "Secrets" přidejte následující konfiguraci:
   ```toml
   [api]
   backend_url = "https://risk-analyst.onrender.com"
   ```

6. Klikněte na "Deploy!"

7. Po úspěšném nasazení získáte URL vašeho frontendu

## 4. Ověření nasazení

### Backend API
- **Health Check**: `https://risk-analyst.onrender.com/`
- **API Dokumentace**: `https://risk-analyst.onrender.com/docs`
- **Test Endpointy**:
   - `/api/test-chmi` - Test CHMI (HTML) parsování a lokalizace
  - `/api/test-openmeteo` - Test OpenMeteo API
  - `/api/test-scraping-improved` - Test vylepšeného scrapingu
   - `/api/maintenance/clear-irrelevant-rss` - Údržba, smazání irelevantních RSS

### Frontend
- **URL**: `https://memory-map-feature-risk-analyst-frontend-app.onrender.com`
- **Funkce**: Interaktivní mapa, filtry, statistiky

## 5. Vylepšení deployment

### Database Initialization
- **Robustní error handling** - Lepší handling UNIQUE constraint chyb
- **Transaction management** - Spolehlivé commit/rollback operace
- **Connection timeout** - Lepší handling připojení k databázi
- **Supplier insertion** - Vylepšená logika pro přidávání dodavatelů

### Error Recovery
- **Individual operation handling** - Každá operace v try-catch bloku
- **Transaction recovery** - Proper rollback mechanisms
- **Connection safety** - Safe connection closing
- **Detailed logging** - Better error messages

### CORS Configuration
- **Frontend URL** - Povoleno v CORS nastavení
- **Wildcard support** - Povoleno pro development
- **Security** - Bezpečná komunikace mezi frontend a backend

## 6. Monitoring a Logging

### Backend Logging
- **Structured logging** - Detailní logy všech operací
- **Error tracking** - Sledování chyb a výjimek
- **Performance monitoring** - Monitoring výkonu API
- **Database connection** - Sledování připojení k databázi

### Health Checks
- **API health** - `/` endpoint pro kontrolu dostupnosti
- **Database health** - Kontrola připojení k databázi
- **Scraping health** - Test funkcionality web scrapingu
- **CORS health** - Kontrola komunikace s frontend

## 7. Troubleshooting

### Časté problémy

#### Database Connection Issues
- Zkontrolujte `RISK_DATABASE_URL` environment variable
- Ověřte, že PostGIS rozšíření je aktivováno
- Zkontrolujte SSL nastavení

#### CORS Issues
- Ověřte CORS konfiguraci v `backend/main.py`
- Zkontrolujte frontend URL v allow_origins
- Testujte komunikaci mezi frontend a backend

#### Deployment Issues
- Zkontrolujte build logy na Render.com
- Ověřte, že všechny dependencies jsou v `requirements.txt`
- Testujte lokálně před deployment

### Debugging

#### Backend Debugging
```bash
# Lokální testování
cd backend
python main.py

# Test database connection
python test_risk_db.py

# Test scraping
python test_improved_scraping.py
```

#### Frontend Debugging
```bash
# Lokální testování
cd frontend
streamlit run app.py
```

## 8. Performance Optimization

### Render.com Free plán limity
- **Web Service**: 512 MB RAM, uspání po 15 minutách neaktivity
- **PostgreSQL**: 1 GB prostoru, max 10 současných připojení

### Optimalizace
- Geografické omezení na ČR pro snížení datového objemu
- Cachování dat v session state
- Efektivní dotazy s PostGIS indexy
- Minimalizace API volání
 - Clustering markerů na mapě pro přehlednost ve frontendu

## 9. Security

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

## 10. Aktuální deployment status

### ✅ Funkční komponenty
- **Backend API**: https://risk-analyst.onrender.com
- **Frontend**: https://memory-map-feature-risk-analyst-frontend-app.onrender.com
- **Database**: PostgreSQL s PostGIS na Render.com
- **GitHub Repository**: https://github.com/moziyuri/memory_map/tree/feature/risk-analyst

### 🔧 Vylepšení
- **Robustní database initialization** - Opraveny UNIQUE constraint chyby
- **Transaction management** - Spolehlivé commit/rollback operace
- **OpenMeteo API integration** - Spolehlivé meteorologické data
- **Improved error handling** - Lepší error recovery
- **CORS configuration** - Opravena komunikace frontend-backend

---

**Vytvořeno pro VW Group Risk Analyst pozici - 2025** 