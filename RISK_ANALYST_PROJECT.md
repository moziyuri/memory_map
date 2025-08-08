# 🚗 Risk Analyst Dashboard - Advanced Features

## 🎯 Cíl projektu
**Specializovaná aplikace pro analýzu rizik dodavatelského řetězce s pokročilými GIS funkcemi**

### Klíčové funkce:
- ✅ **River flood simulation** - Simulace záplav a jejich dopadu
- ✅ **Geographic data access** - Analýza vzdálenosti od řek, nadmořské výšky
- ✅ **Supply chain impact analysis** - Simulace dopadu na dodavatelský řetězec
- ✅ **Historical event correlation** - Korelace s minulými událostmi
- ✅ **Advanced web crawling** - Monitoring incidentů a geopolitických rizik
- ✅ **Real-time risk assessment** - Komplexní hodnocení rizik v reálném čase
- ✅ **OpenMeteo API integration** - Spolehlivé meteorologické data
- ✅ **Robust error handling** - Vylepšené error handling a deployment

---

## 📋 Pokročilé funkce

### **🌊 River Flood Simulation**
- **Výpočet vzdálenosti od řek** - Analýza blízkosti hlavních řek ČR
- **Elevation profile analysis** - Hodnocení nadmořské výšky a terénu
- **Flood probability calculation** - Simulace pravděpodobnosti záplav
- **Impact assessment** - Hodnocení dopadu na dodavatele

### **🗺️ Geographic Risk Assessment**
- **Multi-factor analysis** - Kombinace řek, výšky, historie
- **Risk scoring algorithm** - Komplexní algoritmus hodnocení rizik
- **Terrain analysis** - Analýza typu terénu a zranitelnosti
- **Historical correlation** - Korelace s minulými událostmi

### **🔗 Supply Chain Impact Analysis**
- **Disruption simulation** - Simulace přerušení dodávek
- **Recovery time estimation** - Odhad doby obnovy
- **Alternative supplier identification** - Identifikace záložních dodavatelů
- **Mitigation action generation** - Generování mitigačních opatření

### **📊 Advanced Analytics**
- **Real-time monitoring** - Monitoring rizik v reálném čase
- **Predictive modeling** - Prediktivní modelování rizik
- **Risk trend analysis** - Analýza trendů rizik
- **Automated reporting** - Automatické generování reportů

### **🌤️ Weather Data Integration**
- **OpenMeteo API** - Spolehlivé meteorologické data (primární)
- **CHMI (HTML)** - Česká hydrologická/meterologická data; flood event vzniká jen při stavech SPA/bdělost/pohotovost/ohrožení a s ověřenou CZ lokalizací (stanice/řeka)
- **Real-time weather monitoring** - Sledování aktuálních podmínek
- **Weather-based risk assessment** - Hodnocení rizik na základě počasí

---

## 🔧 Nové API Endpointy

### **River Flood Simulation**
```python
GET /api/analysis/river-flood-simulation
- supplier_id: Optional[int] - Analýza konkrétního dodavatele
- river_name: Optional[str] - Název řeky
- flood_level_m: Optional[float] - Hladina záplav v metrech
```

### **Geographic Risk Assessment**
```python
GET /api/analysis/geographic-risk-assessment
- lat: float - Zeměpisná šířka
- lon: float - Zeměpisná délka
- radius_km: int - Poloměr analýzy v km
```

### **Supply Chain Impact Analysis**
```python
GET /api/analysis/supply-chain-impact
- supplier_id: Optional[int] - Analýza konkrétního dodavatele
- event_type: Optional[str] - Typ události
```

### **Weather API Testing**
```python
GET /api/test-openmeteo
- Test OpenMeteo API funkcionality
```

### **Improved Scraping Testing**
```python
GET /api/test-scraping-improved
- Komplexní test všech scraperů
```
### **Maintenance**
```python
POST /api/maintenance/clear-irrelevant-rss
- Smaže zjevně irelevantní RSS (právo/krimi) na základě klíčových slov (ikem/soud/vydír/obžal/policie/krimi/vyšetřov)
```

---

## 🗄️ Rozšířená databázová struktura

### **Tabulka vw_suppliers (rozšířená)**
```sql
CREATE TABLE vw_suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    location GEOGRAPHY(POINT, 4326),
    category VARCHAR(100), -- 'electronics', 'tires', 'steering', 'brakes', 'body_parts'
    risk_level VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **Tabulka rivers (nová)**
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

### **Pokročilé geografické funkce**
```sql
-- Funkce pro analýzu vzdálenosti od řek
CREATE OR REPLACE FUNCTION calculate_river_distance(lat DOUBLE PRECISION, lon DOUBLE PRECISION)
RETURNS DOUBLE PRECISION AS $$
DECLARE
    min_distance DOUBLE PRECISION := 999999;
    river_distance DOUBLE PRECISION;
    river_record RECORD;
BEGIN
    FOR river_record IN 
        SELECT name, ST_Distance(
            ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
            geometry::geography
        ) as distance
        FROM rivers
    LOOP
        river_distance := river_record.distance / 1000; -- Převod na km
        IF river_distance < min_distance THEN
            min_distance := river_distance;
        END IF;
    END LOOP;
    
    RETURN min_distance;
END;
$$ LANGUAGE plpgsql;

-- Funkce pro analýzu rizika záplav
CREATE OR REPLACE FUNCTION analyze_flood_risk_from_rivers(lat DOUBLE PRECISION, lon DOUBLE PRECISION)
RETURNS JSON AS $$
DECLARE
    nearest_river_name VARCHAR(255);
    nearest_river_distance DOUBLE PRECISION;
    flood_risk_level VARCHAR(50);
    flood_probability DOUBLE PRECISION;
    result JSON;
BEGIN
    -- Najít nejbližší řeku
    SELECT name, ST_Distance(
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
        geometry::geography
    ) / 1000 as distance
    INTO nearest_river_name, nearest_river_distance
    FROM rivers
    ORDER BY ST_Distance(
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
        geometry::geography
    )
    LIMIT 1;
    
    -- Výpočet rizika na základě vzdálenosti
    IF nearest_river_distance < 2.0 THEN
        flood_risk_level := 'critical';
        flood_probability := 0.9;
    ELSIF nearest_river_distance < 5.0 THEN
        flood_risk_level := 'high';
        flood_probability := 0.7;
    ELSIF nearest_river_distance < 10.0 THEN
        flood_risk_level := 'medium';
        flood_probability := 0.4;
    ELSE
        flood_risk_level := 'low';
        flood_probability := 0.1;
    END IF;
    
    result := json_build_object(
        'nearest_river_name', nearest_river_name,
        'nearest_river_distance_km', nearest_river_distance,
        'flood_risk_level', flood_risk_level,
        'flood_probability', flood_probability,
        'mitigation_needed', flood_risk_level IN ('critical', 'high')
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;
```

---

## 📊 Zdroje dat

### **Reálná data**
- **OpenMeteo API** - Primární zdroj meteorologických dat
- **CHMI (HTML)** - Česká hydrologická/meterologická data; přísná pravidla pro vznik událostí (SPA/bdělost/pohotovost/ohrožení + ověřená CZ lokalizace)
- **RSS feeds** - Zprávy z českých médií
- **River Network Data** - Geografická data řek ČR
- **Historical Event Database** - Historické události pro korelaci

### **Demo data**
- **VW Group Suppliers** - Fiktivní dodavatelé s rizikovým hodnocením
- **Risk Events** - Ukázkové rizikové události
- **River Data** - Geografická data hlavních řek ČR

---

## 🧪 Testing Suite

### **test_weather_api.py**
- Test různých weather APIs (OpenWeatherMap, CHMI, Povodí ČR, OpenMeteo)
- Validace funkcionality před implementací
- Porovnání dostupnosti a kvality dat

### **test_improved_scraping.py**
- Test vylepšeného scrapingu
- Komplexní test všech scraperů
- Detailní reporting výsledků

### **test_current_state.py**
- Test současného stavu aplikace
- Health check všech komponent
- Validace deployment

### **test_backend.py**
- Test backend funkcí
- API endpoint testing
- Database connection testing

---

## 🚀 Deployment Improvements

### **Database Initialization**
- **Robustní error handling** - Lepší handling UNIQUE constraint chyb
- **Transaction management** - Spolehlivé commit/rollback operace
- **Connection timeout** - Lepší handling připojení k databázi
- **Supplier insertion** - Vylepšená logika pro přidávání dodavatelů

### **Error Recovery**
- **Individual operation handling** - Každá operace v try-catch bloku
- **Transaction recovery** - Proper rollback mechanisms
- **Connection safety** - Safe connection closing
- **Detailed logging** - Better error messages

### **CORS Configuration**
- **Frontend URL** - Povoleno v CORS nastavení
- **Wildcard support** - Povoleno pro development
- **Security** - Bezpečná komunikace mezi frontend a backend

---

## 📈 Monitoring a Logging

### **Backend Logging**
- **Structured logging** - Detailní logy všech operací
- **Error tracking** - Sledování chyb a výjimek
- **Performance monitoring** - Monitoring výkonu API
- **Database connection** - Sledování připojení k databázi

### **Health Checks**
- **API health** - `/` endpoint pro kontrolu dostupnosti
- **Database health** - Kontrola připojení k databázi
- **Scraping health** - Test funkcionality web scrapingu
- **CORS health** - Kontrola komunikace s frontend

---

## 🔒 Security

### **API Security**
- **CORS** - Konfigurované pro bezpečnou komunikaci
- **Input validation** - Pydantic modely pro validaci dat
- **SQL injection protection** - Parametrizované dotazy
- **Error handling** - Bezpečné error messages

### **Data Security**
- **Environment variables** - Citlivé údaje v environment proměnných
- **Database credentials** - Bezpečné uložení přihlašovacích údajů
- **SSL connections** - Šifrovaná komunikace s databází
- **Input sanitization** - Očištění vstupních dat

---

## 🎯 Výsledky

### **Funkční aplikace**
- ✅ Kompletní full-stack aplikace
- ✅ Real-time data scraping
- ✅ Interaktivní mapa rizik
- ✅ Pokročilé GIS funkce
- ✅ Robustní error handling

### **Technologická ukázka**
- ✅ Moderní technologie (FastAPI, Streamlit, PostgreSQL)
- ✅ GIS analýza (PostGIS, geografické dotazy)
- ✅ Web scraping (CHMI, OpenMeteo, RSS)
- ✅ Cloud deployment (Render.com, Streamlit Cloud)

### **Business value**
- ✅ Supply chain risk management
- ✅ Real-time monitoring
- ✅ Predictive analytics
- ✅ Geographic risk assessment

---

**Vytvořeno pro VW Group Risk Analyst pozici - 2025** 