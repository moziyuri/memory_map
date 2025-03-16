"""
MemoryMap Backend API

Tento modul poskytuje REST API pro aplikaci MemoryMap, která umožňuje ukládání a správu
geograficky umístěných vzpomínek. Součást projektu vytvořeného pro demonstraci
technických dovedností při přípravě na pohovor.

Hlavní funkce:
- Správa vzpomínek s geografickou lokací
- Fulltextové vyhledávání ve vzpomínkách
- Prostorové dotazy pro okolní místa

Autor: Vytvořeno jako ukázka dovedností pro pohovor.
"""

from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import psycopg2  # Knihovna pro připojení k PostgreSQL databázi
from pydantic import BaseModel  # Pro validaci dat
from typing import List, Optional, Dict, Any  # Pro typovou kontrolu
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor
import json
import time

load_dotenv()

# Vytvoření FastAPI aplikace s vlastním názvem
app = FastAPI(title="MemoryMap API")

# Konfigurace CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://stanislavhoracekmemorymap.streamlit.app",
        "http://localhost:8501",  # Pro lokální vývoj
        "https://localhost:8501",
        "https://memory-map.onrender.com",  # Správná Render.com URL
        "https://memorymap-api.onrender.com"  # Ponecháme pro případ
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_keywords(text: str) -> List[str]:
    """Jednoduchá extrakce klíčových slov z textu"""
    # Rozdělíme text na slova a vybereme slova delší než 4 znaky
    words = [word.strip('.,!?()[]{}":;') for word in text.split()]
    keywords = [word for word in words if len(word) > 4]
    # Vrátíme unikátní klíčová slova
    return list(set(keywords))[:5]  # Omezíme na max 5 klíčových slov

# Funkce pro připojení k databázi
def get_db():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database configuration missing")
    
    try:
        # Úprava URL pro psycopg2 (pokud používá formát postgres://)
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        # Logging pro diagnostiku
        print(f"Connecting to database with URL format: {DATABASE_URL[:10]}...")
        
        # Vytvoření slovníku s parametry připojení
        # Místo použití celého URL používáme individuální parametry
        conn = psycopg2.connect(DATABASE_URL)
        
        # Vrácení spojení ke konzumaci
        try:
            yield conn
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        # Detailnější chybová zpráva pro diagnostiku
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )

# Základní endpoint pro kontrolu, zda API běží
@app.get("/")
async def root():
    return {"message": "MemoryMap API is running"}

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

# Endpoint pro analýzu a uložení nové vzpomínky
@app.post("/api/analyze", response_model=MemoryResponse)
async def analyze_text(data: MemoryText):
    try:
        # Jednoduchá extrakce klíčových slov
        keywords = extract_keywords(data.text)
        
        # Připojení k databázi
        conn = get_db()
        with conn.cursor() as cur:
            # Vložení vzpomínky do databáze, včetně geografických dat
            cur.execute("""
                INSERT INTO memories (text, location, keywords, source, date, coordinates)
                VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                RETURNING id, text, location, keywords, source, date,
                          ST_X(coordinates) as longitude, ST_Y(coordinates) as latitude
            """, (data.text, data.location, keywords, data.source, data.date,
                  data.longitude, data.latitude))
            
            # Získání vloženého záznamu
            result = cur.fetchone()
            conn.commit()
            
            if result:
                return {
                    "id": result[0],
                    "text": result[1],
                    "location": result[2],
                    "keywords": result[3],
                    "source": result[4],
                    "date": result[5],
                    "longitude": result[6],
                    "latitude": result[7]
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to insert memory")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
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
                SELECT id, text, location, keywords, source, date,
                       ST_X(coordinates) as longitude, ST_Y(coordinates) as latitude
                FROM memories
                ORDER BY created_at DESC
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
                "longitude": row[6],
                "latitude": row[7]
            } for row in results]
            
    except Exception as e:
        # Zachycení a předání chybové zprávy
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bezpečné uzavření připojení k databázi
        if conn:
            conn.close()

@app.get("/api/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: int):
    """Získání detailu konkrétní vzpomínky"""
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, text, location, keywords, source, date,
                       ST_X(coordinates) as longitude, ST_Y(coordinates) as latitude
                FROM memories
                WHERE id = %s
            """, (memory_id,))
            
            result = cur.fetchone()
            if result:
                return {
                    "id": result[0],
                    "text": result[1],
                    "location": result[2],
                    "keywords": result[3],
                    "source": result[4],
                    "date": result[5],
                    "longitude": result[6],
                    "latitude": result[7]
                }
            else:
                raise HTTPException(status_code=404, detail="Memory not found")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Diagnostický endpoint pro kontrolu proměnných prostředí
@app.get("/api/debug")
async def debug_info():
    # Příprava informací o proměnných prostředí (bezpečným způsobem)
    env_vars = os.environ.keys()
    
    env_info = {
        "DATABASE_URL_EXISTS": os.getenv('DATABASE_URL') is not None,
        "DATABASE_URL_PREFIX": os.getenv('DATABASE_URL', '')[:10] + "..." if os.getenv('DATABASE_URL') else None,
        "ENV_VARS": list(env_vars),
        "ENVIRONMENT": os.getenv('ENVIRONMENT', 'not set'),
        "PORT": os.getenv('PORT', 'not set')
    }
    
    # Kontrola připojení k databázi
    db_connection_status = "Unknown"
    db_error = None
    db_details = {}
    try:
        DATABASE_URL = os.getenv('DATABASE_URL')
        if DATABASE_URL:
            db_details["url_starts_with"] = DATABASE_URL[:10] + "..."
            
            if DATABASE_URL.startswith('postgres://'):
                modified_url = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
                db_details["modified_url_starts_with"] = modified_url[:10] + "..."
                DATABASE_URL = modified_url
            
            try:
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
                cur = conn.cursor()
                
                # Kontrola základních informací o databázi
                cur.execute("SELECT version();")
                db_details["version"] = cur.fetchone()[0]
                
                # Kontrola PostGIS
                cur.execute("SELECT PostGIS_Version();")
                db_details["postgis_version"] = cur.fetchone()[0]
                
                # Kontrola tabulek
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                db_details["tables"] = [row[0] for row in cur.fetchall()]
                
                conn.close()
                db_connection_status = "Connected"
                db_error = None
                
            except Exception as db_connect_error:
                db_connection_status = "Connection Failed"
                db_error = str(db_connect_error)
        else:
            db_connection_status = "No DATABASE_URL"
            db_error = "DATABASE_URL environment variable not set"
    except Exception as e:
        db_connection_status = "Failed"
        db_error = str(e)
    
    return {
        "status": "API is running",
        "environment": env_info,
        "database": {
            "status": db_connection_status,
            "error": db_error,
            "details": db_details
        }
    }

# Spuštění aplikace, pokud je tento soubor spuštěn přímo
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 