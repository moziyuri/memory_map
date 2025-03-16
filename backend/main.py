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
    # Zkusíme najít proměnnou prostředí DATABASE_URL v různých formátech
    DATABASE_URL = None
    env_vars = [
        'DATABASE_URL',
        'RENDER_DATABASE_URL',
        'POSTGRES_URL',
        'PG_URL'
    ]
    
    for var in env_vars:
        if os.getenv(var):
            DATABASE_URL = os.getenv(var)
            print(f"Použití proměnné {var} pro připojení k databázi")
            break
    
    if not DATABASE_URL:
        raise HTTPException(status_code=500, detail="Database configuration missing - no database URL found")
    
    try:
        # Úprava URL pro psycopg2 (pokud používá formát postgres://)
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            print("URL konvertováno z postgres:// na postgresql://")
        
        # Logging pro diagnostiku
        print(f"Connecting to database with URL format: {DATABASE_URL[:10]}...")
        
        # Přímé připojení
        conn = None
        try:
            conn = psycopg2.connect(DATABASE_URL)
            yield conn
        finally:
            if conn:
                conn.close()
                print("Database connection closed")
            
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
    source: Optional[str] = None  # Volitelný zdroj vzpomínky
    date: Optional[str] = None  # Volitelné datum vzpomínky
    
    class Config:
        orm_mode = True  # Umožňuje konverzi z databázových objektů

# Endpoint pro analýzu a uložení nové vzpomínky
@app.post("/api/analyze", response_model=MemoryResponse)
async def analyze_text(data: MemoryText):
    conn = None
    try:
        # Jednoduchá extrakce klíčových slov
        keywords = extract_keywords(data.text)
        
        # Připojení k databázi
        conn = next(get_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Kontrola existence tabulky
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')")
            table_exists = cur.fetchone()['exists']
            
            if not table_exists:
                # Pokud tabulka neexistuje, vytvořme ji
                try:
                    print("Tabulka memories neexistuje, vytvářím ji...")
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS memories (
                            id SERIAL PRIMARY KEY,
                            text TEXT NOT NULL,
                            location VARCHAR(255) NOT NULL,
                            coordinates GEOGRAPHY(POINT, 4326) NOT NULL,
                            keywords TEXT[],
                            source TEXT,
                            date TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    ''')
                    conn.commit()
                except Exception as create_error:
                    print(f"Chyba při vytváření tabulky: {str(create_error)}")
                    raise HTTPException(status_code=500, detail="Nelze vytvořit tabulku memories")
            
            # Kontrola PostGIS rozšíření
            try:
                cur.execute("SELECT PostGIS_Version()")
            except Exception as postgis_error:
                print(f"PostGIS není nainstalován: {str(postgis_error)}")
                raise HTTPException(status_code=500, detail="PostGIS rozšíření není dostupné")
            
            try:
                # Vložení vzpomínky do databáze, včetně geografických dat
                cur.execute("""
                    INSERT INTO memories (text, location, keywords, source, date, coordinates)
                    VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                    RETURNING id, text, location, keywords, source, date,
                            ST_X(coordinates::geometry) as longitude, ST_Y(coordinates::geometry) as latitude
                """, (data.text, data.location, keywords, data.source, data.date,
                      data.longitude, data.latitude))
                
                # Získání vloženého záznamu
                result = cur.fetchone()
                conn.commit()
                
                if result:
                    # Převod na očekávaný formát
                    memory = {
                        "id": result["id"],
                        "text": result["text"],
                        "location": result["location"],
                        "keywords": result["keywords"] if result["keywords"] else [],
                        "source": result["source"],
                        "date": result["date"],
                        "longitude": result["longitude"],
                        "latitude": result["latitude"]
                    }
                    return memory
                else:
                    raise HTTPException(status_code=500, detail="Failed to insert memory")
            except Exception as insert_error:
                print(f"Chyba při vkládání vzpomínky: {str(insert_error)}")
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"Database error: {str(insert_error)}")
                
    except Exception as e:
        print(f"Obecná chyba při analýze textu: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# Endpoint pro získání všech vzpomínek
@app.get("/api/memories", response_model=List[MemoryResponse])
async def get_memories():
    conn = None
    try:
        # Připojení k databázi
        conn = next(get_db())
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Kontrola existence tabulky
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')")
            table_exists = cur.fetchone()['exists']
            
            if not table_exists:
                print("Tabulka memories neexistuje, vracím prázdný seznam")
                return []
                
            # Kontrola PostGIS rozšíření
            try:
                cur.execute("SELECT PostGIS_Version()")
            except Exception as postgis_error:
                print(f"PostGIS není nainstalován: {str(postgis_error)}")
                return []
            
            try:
                # Získání všech vzpomínek, včetně extrakce geografických souřadnic
                cur.execute("""
                    SELECT id, text, location, keywords, source, date,
                           ST_X(coordinates::geometry) as longitude, ST_Y(coordinates::geometry) as latitude
                    FROM memories
                    ORDER BY created_at DESC
                """)
                
                # Transformace výsledků do seznamu objektů podle očekávaného formátu
                results = cur.fetchall()
                
                # Převod na očekávaný formát
                memories = []
                for row in results:
                    memory = {
                        "id": row["id"],
                        "text": row["text"],
                        "location": row["location"],
                        "keywords": row["keywords"] if row["keywords"] else [],
                        "source": row["source"],
                        "date": row["date"],
                        "longitude": row["longitude"],
                        "latitude": row["latitude"]
                    }
                    memories.append(memory)
                
                return memories
            except Exception as query_error:
                print(f"Chyba při dotazu na memories: {str(query_error)}")
                return []
            
    except Exception as e:
        # Zachycení a předání chybové zprávy
        print(f"Obecná chyba při získávání vzpomínek: {str(e)}")
        return []
    finally:
        # Bezpečné uzavření připojení k databázi
        if conn:
            conn.close()

@app.get("/api/memories/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: int):
    """Získání detailu konkrétní vzpomínky"""
    conn = None
    try:
        # Připojení k databázi
        conn = next(get_db())
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, text, location, keywords, source, date,
                       ST_X(coordinates::geometry) as longitude, ST_Y(coordinates::geometry) as latitude
                FROM memories
                WHERE id = %s
            """, (memory_id,))
            
            result = cur.fetchone()
            if result:
                # Převod na očekávaný formát
                memory = {
                    "id": result["id"],
                    "text": result["text"],
                    "location": result["location"],
                    "keywords": result["keywords"] if result["keywords"] else [],
                    "source": result["source"],
                    "date": result["date"],
                    "longitude": result["longitude"],
                    "latitude": result["latitude"]
                }
                return memory
            else:
                raise HTTPException(status_code=404, detail="Memory not found")
                
    except Exception as e:
        print(f"Chyba při získávání vzpomínky {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bezpečné uzavření připojení k databázi
        if conn:
            conn.close()

# Diagnostický endpoint pro kontrolu proměnných prostředí
@app.get("/api/debug")
async def debug_info():
    # Příprava informací o proměnných prostředí (bezpečným způsobem)
    env_vars = os.environ.keys()
    db_env_vars = []
    
    # Sbíráme všechny proměnné související s databází
    for key in env_vars:
        if 'DB' in key.upper() or 'DATABASE' in key.upper() or 'POSTGRES' in key.upper():
            db_env_vars.append(key)
    
    env_info = {
        "DATABASE_URL_EXISTS": os.getenv('DATABASE_URL') is not None,
        "DATABASE_RELATED_VARS": db_env_vars,
        "ENV_VARS_COUNT": len(list(env_vars)),
        "ENVIRONMENT": os.getenv('ENVIRONMENT', 'not set'),
        "PORT": os.getenv('PORT', 'not set')
    }
    
    # Přidáme začátek každé databázové proměnné (bezpečně)
    for key in db_env_vars:
        value = os.getenv(key, '')
        if value:
            env_info[f"{key}_PREFIX"] = value[:10] + "..." if len(value) > 10 else value
    
    # Kontrola připojení k databázi
    db_connection_status = "Unknown"
    db_error = None
    db_details = {}
    
    # Zkusíme najít a použít databázovou URL
    database_url = None
    potential_db_vars = ['DATABASE_URL', 'RENDER_DATABASE_URL', 'POSTGRES_URL', 'PG_URL']
    
    for var in potential_db_vars:
        if os.getenv(var):
            database_url = os.getenv(var)
            db_details["used_env_var"] = var
            break
    
    try:
        if database_url:
            db_details["url_starts_with"] = database_url[:10] + "..."
            
            # Analýza URL
            from urllib.parse import urlparse
            try:
                parsed = urlparse(database_url)
                db_details["schema"] = parsed.scheme
                db_details["netloc"] = parsed.netloc
                db_details["path"] = parsed.path
                db_details["username_present"] = parsed.username is not None
                db_details["password_present"] = parsed.password is not None
                db_details["hostname"] = parsed.hostname
                db_details["port"] = parsed.port
            except Exception as parse_error:
                db_details["url_parse_error"] = str(parse_error)
            
            if database_url.startswith('postgres://'):
                modified_url = database_url.replace('postgres://', 'postgresql://', 1)
                db_details["modified_url_starts_with"] = modified_url[:10] + "..."
                database_url = modified_url
            
            try:
                conn = psycopg2.connect(database_url, connect_timeout=5)
                cur = conn.cursor()
                
                # Kontrola základních informací o databázi
                cur.execute("SELECT version();")
                db_details["version"] = cur.fetchone()[0]
                
                # Kontrola PostGIS
                try:
                    cur.execute("SELECT PostGIS_Version();")
                    db_details["postgis_version"] = cur.fetchone()[0]
                except Exception as postgis_error:
                    db_details["postgis_error"] = str(postgis_error)
                
                # Kontrola tabulek
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                db_details["tables"] = [row[0] for row in cur.fetchall()]
                
                # Zkontrolujeme tabulku memories
                try:
                    cur.execute("SELECT COUNT(*) FROM memories")
                    db_details["memories_count"] = cur.fetchone()[0]
                except Exception as table_error:
                    db_details["memories_table_error"] = str(table_error)
                
                conn.close()
                db_connection_status = "Connected"
                db_error = None
                
            except Exception as db_connect_error:
                db_connection_status = "Connection Failed"
                db_error = str(db_connect_error)
        else:
            db_connection_status = "No Database URL Found"
            db_error = "No suitable database URL environment variable found"
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