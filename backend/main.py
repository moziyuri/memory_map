from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import spacy  # Knihovna pro zpracování přirozeného jazyka
import psycopg2  # Knihovna pro připojení k PostgreSQL databázi
from pydantic import BaseModel  # Pro validaci dat
from typing import List, Optional, Dict, Any  # Pro typovou kontrolu
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import json
import whisper
import tempfile

load_dotenv()

# Vytvoření FastAPI aplikace s vlastním názvem
app = FastAPI(title="MemoryMap AI API")

# Povolení CORS (Cross-Origin Resource Sharing) - umožňuje frontendové aplikaci
# komunikovat s tímto API i když běží na jiné doméně/portu
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Povolí přístup ze všech domén
    allow_credentials=True,
    allow_methods=["*"],  # Povolí všechny HTTP metody (GET, POST, atd.)
    allow_headers=["*"],  # Povolí všechny HTTP hlavičky
)

# Inicializace spaCy pro rozpoznávání entit v textu
try:
    nlp = spacy.load("xx_ent_wiki_sm")  # Načtení vícejazyčného modelu
except OSError:
    # Pokud model není nainstalován, stáhneme ho
    os.system("python -m spacy download xx_ent_wiki_sm")
    nlp = spacy.load("xx_ent_wiki_sm")

# Funkce pro připojení k databázi
def get_db():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database configuration missing")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Základní endpoint pro kontrolu, zda API běží
@app.get("/")
async def root():
    return {"message": "MemoryMap AI API is running"}

# Definice struktury dat pro vstupní data
class MemoryText(BaseModel):
    text: str  # Text vzpomínky
    location: str  # Název lokace
    latitude: float  # Zeměpisná šířka
    longitude: float  # Zeměpisná délka
    source: Optional[str] = None  # Volitelný zdroj vzpomínky
    date: Optional[str] = None  # Volitelné datum vzpomínky

# Definice struktury dat pro výstupní data
class MemoryResponse(BaseModel):
    id: int  # Identifikátor vzpomínky v databázi
    text: str  # Text vzpomínky
    location: str  # Název lokace
    keywords: List[str]  # Seznam klíčových slov
    latitude: float  # Zeměpisná šířka
    longitude: float  # Zeměpisná délka
    source: Optional[str]  # Volitelný zdroj vzpomínky
    date: Optional[str]  # Volitelné datum vzpomínky

# Definice struktury dat pro georeferencování
class GeoreferenceRequest(BaseModel):
    place_name: str  # Název místa k georeferencování
    historical_period: Optional[str] = "1950"  # Historické období (výchozí 1950)

# Endpoint pro georeferencování historických názvů míst
@app.post("/georef")
async def georeference_placename(request: GeoreferenceRequest):
    """Pokusí se georeferencovat historický název místa"""
    conn = None
    try:
        # Připojení k databázi
        conn = get_db()
        with conn.cursor() as cur:
            # Použití PostgreSQL funkce levenshtein pro hledání podobných názvů
            # Tato funkce vyžaduje rozšíření fuzzystrmatch v PostgreSQL
            cur.execute("""
                SELECT name, ST_AsText(location) FROM place_names
                WHERE name ILIKE %s OR alt_name ILIKE %s
                ORDER BY levenshtein(name, %s) LIMIT 1
            """, (f"%{request.place_name}%", f"%{request.place_name}%", request.place_name))
            
            result = cur.fetchone()
            if result:
                return {"name": result[0], "geometry": result[1]}
            
            # Pokud nenajdeme místo v naší databázi, zkusíme hledat v OSM datech
            # (vyžaduje odpovídající tabulku v databázi)
            cur.execute("""
                SELECT name, ST_AsText(way) FROM osm_data
                WHERE name ILIKE %s OR tags->'alt_name' ILIKE %s
                ORDER BY levenshtein(name, %s) LIMIT 1
            """, (f"%{request.place_name}%", f"%{request.place_name}%", request.place_name))
            
            result = cur.fetchone()
            if result:
                return {"name": result[0], "geometry": result[1]}
                
            # Pokud jsme nic nenašli, vrátíme chybu
            return {"error": "Místo nenalezeno"}
    except Exception as e:
        # Zachycení a předání chybové zprávy
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bezpečné uzavření připojení k databázi
        if conn:
            conn.close()

# Endpoint pro analýzu a uložení nové vzpomínky
@app.post("/api/analyze", response_model=MemoryResponse)
async def analyze_text(data: MemoryText):
    try:
        # Použití spaCy pro extrakci klíčových slov/entit z textu
        doc = nlp(data.text)
        keywords = [ent.text for ent in doc.ents]
        
        # Připojení k databázi
        conn = get_db()
        with conn.cursor() as cur:
            # Vložení vzpomínky do databáze, včetně geografických dat
            # ST_SetSRID a ST_MakePoint jsou PostGIS funkce pro práci s geografickými daty
            cur.execute("""
                INSERT INTO memories (text, location, keywords, source, date)
                VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
                RETURNING id, text, ST_AsText(location), keywords, source, date
            """, (data.text, data.longitude, data.latitude, keywords, data.source, data.date))
            
            # Získání vloženého záznamu
            result = cur.fetchone()
            conn.commit()
            
            if result:
                # Vrácení strukturovaných dat
                return {
                    "id": result[0],
                    "text": result[1],
                    "location": result[2],
                    "keywords": result[3],
                    "latitude": data.latitude,
                    "longitude": data.longitude,
                    "source": result[4],
                    "date": result[5]
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to insert memory")
                
    except Exception as e:
        # Zachycení a předání chybové zprávy
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bezpečné uzavření připojení k databázi
        if 'conn' in locals():
            conn.close()

# Endpoint pro získání všech vzpomínek
@app.get("/api/memories", response_model=List[MemoryResponse])
async def get_memories():
    conn = None
    try:
        # Připojení k databázi
        conn = get_db()
        with conn.cursor() as cur:
            # Získání všech vzpomínek, včetně extrakce geografických souřadnic
            cur.execute("""
                SELECT id, text, ST_AsText(location), keywords, source, date,
                       ST_Y(location), ST_X(location)
                FROM memories
            """)
            
            # Transformace výsledků do seznamu objektů
            results = cur.fetchall()
            return [{
                "id": row[0],
                "text": row[1],
                "location": row[2],
                "keywords": row[3],
                "source": row[4],
                "date": row[5],
                "latitude": row[6],
                "longitude": row[7]
            } for row in results]
            
    except Exception as e:
        # Zachycení a předání chybové zprávy
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bezpečné uzavření připojení k databázi
        if conn:
            conn.close()

# Spuštění aplikace, pokud je tento soubor spuštěn přímo
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 