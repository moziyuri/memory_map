# 🚗 VW Group Risk Analyst - Memory Map Enhancement

## 🎯 Cíl projektu
**Vytvořit specializovanou verzi Memory Map pro Risk Analyst pozici ve VW Group**

### Proč to bude fungovat:
- ✅ **Web scraping** - Explicitně požadováno v job description
- ✅ **GIS analýza** - PostGIS + geografická data
- ✅ **Supply chain risk** - Dodavatelské řetězce VW Group
- ✅ **Moderní technologie** - Python, PostgreSQL, FastAPI
- ✅ **Vizualizace** - Interaktivní mapy rizik

---

## 📋 Projektový plán

### **Fáze 1: Nová databáze a základní struktura (1-2 hodiny)**
- [ ] Vytvoření nové PostgreSQL databáze na Render.com
- [ ] Implementace tabulek pro risk events
- [ ] Základní API endpointy
- [ ] Testování připojení

### **Fáze 2: Web scraping modul (2-3 hodiny)**
- [ ] CHMI API scraper pro záplavové výstrahy
- [ ] RSS feed parser pro novinky
- [ ] Automatické ukládání do databáze
- [ ] Error handling a logging

### **Fáze 3: Risk analysis a vizualizace (1-2 hodiny)**
- [ ] Geografické funkce pro analýzu rizik
- [ ] Dashboard s vizualizací na mapě
- [ ] Filtry podle typu incidentu
- [ ] Risk scoring algoritmus

### **Fáze 4: Demo data a prezentace (30 min)**
- [ ] Fiktivní dodavatelé VW Group
- [ ] Historické incidenty
- [ ] Ukázka analýzy rizik
- [ ] README s instrukcemi

---

## 🗄️ Databázová struktura

### **Hlavní tabulka: risk_events**
```sql
CREATE TABLE risk_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    location POINT,  -- Geografická pozice
    event_type VARCHAR(50), -- 'flood', 'protest', 'supply_chain', 'geopolitical'
    severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    source VARCHAR(100), -- 'chmi_api', 'rss', 'manual', 'copernicus'
    url TEXT, -- Zdroj dat
    scraped_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Geografický index pro rychlé vyhledávání
CREATE INDEX idx_risk_events_location ON risk_events USING GIST (location);
CREATE INDEX idx_risk_events_type ON risk_events (event_type);
CREATE INDEX idx_risk_events_severity ON risk_events (severity);
```

### **Funkce pro analýzu rizik:**
```sql
-- Funkce pro výpočet rizika v okolí bodu
CREATE OR REPLACE FUNCTION calculate_risk_in_radius(
    point_lat DECIMAL, 
    point_lon DECIMAL, 
    radius_km INTEGER DEFAULT 50
)
RETURNS TABLE(
    event_count INTEGER,
    high_risk_count INTEGER,
    risk_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER as event_count,
        COUNT(*) FILTER (WHERE severity IN ('high', 'critical'))::INTEGER as high_risk_count,
        CASE 
            WHEN COUNT(*) = 0 THEN 0.0
            ELSE (COUNT(*) FILTER (WHERE severity IN ('high', 'critical'))::DECIMAL / COUNT(*)) * 100
        END as risk_score
    FROM risk_events
    WHERE ST_DWithin(
        location::geography, 
        ST_SetSRID(ST_MakePoint(point_lon, point_lat), 4326)::geography, 
        radius_km * 1000
    );
END;
$$ LANGUAGE plpgsql;
```

---

## 🌐 Web Scraping zdroje

### **1. CHMI (Český hydrometeorologický ústav)**
- **URL:** https://hydro.chmi.cz/hpps/
- **Data:** Záplavové výstrahy, stavy vod
- **Formát:** JSON API
- **Frekvence:** Každých 6 hodin

### **2. RSS Feeds pro novinky**
- **České noviny:** iDNES, ČT24, Seznam Zprávy
- **Klíčová slova:** "záplavy", "povodně", "protesty", "doprava"
- **Frekvence:** Každých 2 hodiny

### **3. Copernicus Emergency Management Service**
- **URL:** https://emergency.copernicus.eu/
- **Data:** Satelitní snímky záplav
- **Formát:** GeoTIFF, Shapefile
- **Frekvence:** Denně

---

## 🔧 API Endpointy

### **Základní CRUD operace:**
```python
@app.get("/api/risks")
async def get_risk_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[int] = 50
):
    """Získá risk events s filtry"""

@app.post("/api/risks")
async def create_risk_event(risk: RiskEvent):
    """Vytvoří nový risk event"""

@app.get("/api/risks/{risk_id}")
async def get_risk_event(risk_id: int):
    """Získá konkrétní risk event"""
```

### **Web scraping endpointy:**
```python
@app.get("/api/scrape/chmi")
async def scrape_chmi_floods():
    """Scrape CHMI API pro záplavové výstrahy"""

@app.get("/api/scrape/rss")
async def scrape_rss_feeds():
    """Scrape RSS feeds pro novinky"""

@app.get("/api/scrape/run-all")
async def run_all_scrapers():
    """Spustí všechny scrapers najednou"""
```

### **Analýza rizik:**
```python
@app.get("/api/analysis/risk-map")
async def get_risk_map():
    """Vrátí data pro risk mapu"""

@app.get("/api/analysis/supplier-risk")
async def analyze_supplier_risk(
    lat: float,
    lon: float,
    radius_km: int = 50
):
    """Analýza rizik pro dodavatele"""

@app.get("/api/analysis/statistics")
async def get_risk_statistics():
    """Statistiky rizik"""
```

---

## 🗺️ Frontend - Risk Map

### **Komponenty:**
1. **Leaflet mapa** - Základní mapová vrstva
2. **Risk events layer** - Body incidentů na mapě
3. **Risk zones layer** - Polygony rizikových zón
4. **Supplier markers** - Dodavatelé VW Group
5. **Filters panel** - Filtry podle typu, závažnosti, data
6. **Statistics panel** - Statistiky rizik

### **Interaktivita:**
- **Klik na incident** - Detail informací
- **Hover na dodavatele** - Riziko v okolí
- **Filtry** - Dynamické filtrování
- **Time slider** - Časová osa incidentů

---

## 📊 Demo data pro VW Group

### **Fiktivní dodavatelé:**
```python
VW_SUPPLIERS = [
    {
        "name": "Bosch Electronics",
        "location": (49.8175, 15.4730),  # České Budějovice
        "category": "electronics",
        "risk_level": "medium"
    },
    {
        "name": "Continental Tires",
        "location": (50.0755, 14.4378),  # Praha
        "category": "tires",
        "risk_level": "low"
    },
    {
        "name": "ZF Steering Systems",
        "location": (49.1951, 16.6068),  # Brno
        "category": "steering",
        "risk_level": "high"
    }
]
```

### **Historické incidenty:**
```python
HISTORICAL_INCIDENTS = [
    {
        "title": "Záplavy v jižních Čechách",
        "location": (49.8175, 15.4730),
        "event_type": "flood",
        "severity": "high",
        "date": "2023-06-15"
    },
    {
        "title": "Protesty v Praze",
        "location": (50.0755, 14.4378),
        "event_type": "protest",
        "severity": "medium",
        "date": "2023-07-20"
    }
]
```

---

## 🚀 Implementační postup

### **Krok 1: Nová databáze**
1. Vytvořit novou PostgreSQL na Render.com
2. Nastavit environment variables
3. Testovat připojení

### **Krok 2: Základní struktura**
1. Vytvořit tabulky v PostgreSQL
2. Implementovat základní API endpointy
3. Testovat CRUD operace

### **Krok 3: Web scraping**
1. Implementovat CHMI scraper
2. Implementovat RSS scraper
3. Testovat automatické ukládání

### **Krok 4: Analýza a vizualizace**
1. Implementovat geografické funkce
2. Vytvořit risk mapu
3. Přidat filtry a statistiky

### **Krok 5: Demo a prezentace**
1. Přidat demo data
2. Vytvořit README
3. Připravit prezentaci

---

## 📈 Očekávané výsledky

### **Technické znalosti:**
- ✅ **Web scraping** - CHMI API, RSS feeds
- ✅ **GIS analýza** - PostGIS, geografické funkce
- ✅ **Databáze** - PostgreSQL, komplexní dotazy
- ✅ **API development** - FastAPI, REST endpoints
- ✅ **Data visualization** - Interaktivní mapy

### **Business kontext:**
- ✅ **Supply chain risk** - Dodavatelské řetězce VW
- ✅ **Geographic risk mapping** - Vizuální analýza
- ✅ **Real-time monitoring** - Automatické data
- ✅ **Risk scoring** - Kvantifikace rizik

### **Portfolio hodnota:**
- ✅ **Kompletní aplikace** - End-to-end řešení
- ✅ **Real-world data** - Skutečná data o rizicích
- ✅ **Automotive focus** - Relevantní pro VW Group
- ✅ **Moderní technologie** - Aktuální stack

---

## 🎯 Proč to bude fungovat pro VW Group

### **1. Explicitní požadavky job description:**
- ✅ **Web scraping** - Implementováno
- ✅ **Data analysis** - Python + PostgreSQL
- ✅ **Risk management** - Supply chain focus
- ✅ **Automotive industry** - VW Group kontext

### **2. Konkrétní důkaz znalostí:**
- ✅ **Živá aplikace** - Ne jen teorie
- ✅ **Real-world data** - Skutečná data o rizicích
- ✅ **Moderní technologie** - Co VW používá
- ✅ **Vizualizace** - Snadno pochopitelné

### **3. Relevantní pro pozici:**
- ✅ **Risk analysis** - Analýza dodavatelských rizik
- ✅ **Geographic data** - Prostorová analýza
- ✅ **Automation** - Automatické získávání dat
- ✅ **Reporting** - Dashboard a reporty

---

## ⏱️ Časový plán

### **Celkový čas: 5-7 hodin**
- **Fáze 1:** 1-2 hodiny
- **Fáze 2:** 2-3 hodiny  
- **Fáze 3:** 1-2 hodiny
- **Fáze 4:** 30 minut

### **Priorita:**
1. **Nejdříve** - Nová databáze a základní struktura
2. **Pak** - Web scraping (klíčové pro job description)
3. **Nakonec** - Analýza a vizualizace

---

## 🎉 Výsledek

**Memory Map Risk Analysis = Živý důkaz znalostí pro Risk Analyst pozici ve VW Group**

**Připraven začít implementaci?** 🚀 