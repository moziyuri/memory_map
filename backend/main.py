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

# Proměnná pro uložení connection poolu - globální pro celou aplikaci
connection_pool = None

def get_db():
    """
    Vytvoří a poskytuje připojení k databázi z connection poolu.
    """
    global connection_pool
    
    # Zjištění URL databáze z proměnných prostředí
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
        print(f"Připojuji se k databázi s URL začínajícím: {DATABASE_URL[:10]}...")
        
        # Pokud connection pool neexistuje, vytvoříme ho
        if connection_pool is None:
            try:
                print("Vytváření nového connection poolu...")
                # Vytvoříme přímé připojení - connection pool zde není nutný, 
                # protože FastAPI již řeší konkurenční požadavky
                conn = psycopg2.connect(DATABASE_URL)
                conn.autocommit = True  # Nastavíme autocommit pro jednodušší práci
                connection_pool = conn
                print("Connection pool úspěšně vytvořen.")
            except Exception as e:
                print(f"Chyba při vytváření connection poolu: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Database connection failed: {str(e)}"
                )
        
        # Vracíme existující připojení z poolu
        try:
            # Zkontrolujeme, zda je připojení stále aktivní
            if connection_pool.closed:
                print("Připojení bylo uzavřeno, vytvořím nové...")
                connection_pool = psycopg2.connect(DATABASE_URL)
                connection_pool.autocommit = True
                print("Nové připojení úspěšně vytvořeno.")
                
            # Vrátíme aktivní připojení - nebudeme ho zavírat, pouze použijeme
            yield connection_pool
        except Exception as e:
            print(f"Chyba při získávání připojení z poolu: {str(e)}")
            # Pokusíme se vytvořit nové připojení
            try:
                connection_pool = psycopg2.connect(DATABASE_URL)
                connection_pool.autocommit = True
                yield connection_pool
            except Exception as new_e:
                print(f"Nelze vytvořit ani náhradní připojení: {str(new_e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Database connection failed: {str(new_e)}"
                )
            
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

# Alias pro MemoryText, který používáme v novém endpointu
class MemoryCreate(BaseModel):
    text: str  # Text vzpomínky
    location: str  # Název lokace
    latitude: float  # Zeměpisná šířka
    longitude: float  # Zeměpisná délka
    keywords: Optional[List[str]] = None  # Volitelná klíčová slova
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
                    memory = dict(row)
                    memories.append(memory)
                
                return memories
            except Exception as e:
                print(f"Chyba při získávání vzpomínek: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        print(f"Chyba při připojení k databázi: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
                # Převod na slovník - jednodušší způsob
                return dict(result)
            else:
                raise HTTPException(status_code=404, detail="Memory not found")
                
    except Exception as e:
        print(f"Chyba při získávání vzpomínky {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/api/diagnostic")
async def diagnostic():
    """
    Diagnostický endpoint pro ověření funkčnosti API a stavu databáze.
    Vrací detailní informace o:
    - Stavu připojení k databázi
    - Počtu vzpomínek v databázi
    - Struktuře dat vzpomínek
    - Verzi PostGIS
    """
    conn = None
    result = {
        "status": "initializing",
        "api_version": "1.0.0",
        "timestamp": time.time(),
        "database": {
            "connected": False,
            "tables": [],
            "postgis_version": None,
            "memories_count": 0,
            "sample_memory": None
        },
        "errors": []
    }
    
    try:
        # Připojení k databázi
        conn = next(get_db())
        result["database"]["connected"] = True
        result["status"] = "connected_to_db"
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Získání seznamu tabulek
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [row["table_name"] for row in cur.fetchall()]
            result["database"]["tables"] = tables
            
            # Kontrola existence tabulky memories
            memories_exists = "memories" in tables
            result["database"]["memories_table_exists"] = memories_exists
            
            # Kontrola PostGIS verze
            try:
                cur.execute("SELECT PostGIS_Version()")
                postgis_version = cur.fetchone()
                result["database"]["postgis_version"] = postgis_version["postgis_version"] if postgis_version else None
            except Exception as e:
                result["database"]["postgis_version"] = "not_installed"
                result["errors"].append(f"PostGIS error: {str(e)}")
            
            # Pokud tabulka memories existuje, získáme počet vzpomínek a ukázku
            if memories_exists:
                try:
                    # Počet vzpomínek
                    cur.execute("SELECT COUNT(*) as count FROM memories")
                    count = cur.fetchone()
                    result["database"]["memories_count"] = count["count"] if count else 0
                    
                    # Vzorová vzpomínka s kompletními daty (pokud existuje)
                    if result["database"]["memories_count"] > 0:
                        cur.execute("""
                            SELECT id, text, location, keywords, source, date, coordinates,
                                   ST_X(coordinates::geometry) as longitude, 
                                   ST_Y(coordinates::geometry) as latitude,
                                   created_at
                            FROM memories
                            ORDER BY created_at DESC
                            LIMIT 1
                        """)
                        sample = cur.fetchone()
                        
                        # Převedeme na slovník pro JSON výstup
                        if sample:
                            memory_dict = dict(sample)
                            # Převod PostgreSQL specifických typů na string pro JSON výstup
                            memory_dict["coordinates"] = str(memory_dict["coordinates"])
                            memory_dict["created_at"] = str(memory_dict["created_at"])
                            result["database"]["sample_memory"] = memory_dict
                except Exception as e:
                    result["errors"].append(f"Error querying memories: {str(e)}")
        
        # Přidáme informace o databázovém URL (bezpečně maskované)
        db_url = os.getenv('DATABASE_URL', 'not set')
        if db_url != 'not set':
            # Maskujeme citlivé části
            masked_url = mask_db_url(db_url)
            result["database"]["connection_string"] = masked_url
        
        # Pokud nejsou žádné chyby, označíme jako úspěšné
        if not result["errors"]:
            result["status"] = "healthy"
        
    except Exception as e:
        result["status"] = "error"
        result["errors"].append(str(e))
    
    return result

def mask_db_url(url):
    """Maskuje citlivé části databázového URL"""
    if not url:
        return None
    
    try:
        # PostgreSQL URI formát: postgresql://user:password@host:port/database
        parts = url.split('@')
        if len(parts) > 1:
            # Máme uživatelské jméno/heslo část
            credentials = parts[0].split('://')
            if len(credentials) > 1:
                protocol = credentials[0]
                user_pass = credentials[1].split(':')
                if len(user_pass) > 1:
                    # Maskujeme heslo
                    masked_url = f"{protocol}://{user_pass[0]}:****@{parts[1]}"
                    return masked_url
        
        # Pokud se formát neshoduje s očekávaným, vracíme obecné maskování
        return url.replace('postgres://', 'postgres://****:****@')
    except:
        # V případě problému s parsováním vracíme bezpečnou verzi
        return "database_url_format_error"

# Endpoint pro přidání nové vzpomínky
@app.post("/api/memories", response_model=MemoryResponse, status_code=201)
async def add_memory(memory: MemoryCreate):
    conn = None
    try:
        # Připojení k databázi
        conn = next(get_db())
        
        # Extrahování klíčových slov, pokud nebyla poskytnuta přímo
        keywords = memory.keywords if memory.keywords else extract_keywords(memory.text)
        
        # Vytvoření SQL dotazu s odolností proti SQL injection pomocí parametrizovaného dotazu
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Kontrola existence tabulky a vytvoření, pokud neexistuje
            cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memories')")
            table_exists = cur.fetchone()['exists']
            
            if not table_exists:
                try:
                    print("Tabulka memories neexistuje, vytvářím...")
                    # Nejprve zkontrolujeme, zda je PostGIS nainstalován
                    try:
                        cur.execute("SELECT PostGIS_Version()")
                    except:
                        # Pokud PostGIS není nainstalován, pokusíme se ho přidat
                        try:
                            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                            conn.commit()
                            print("PostGIS rozšíření úspěšně přidáno.")
                        except Exception as e:
                            print(f"Nelze přidat PostGIS rozšíření: {str(e)}")
                            raise HTTPException(
                                status_code=500,
                                detail=f"PostGIS rozšíření není dostupné: {str(e)}"
                            )
                    
                    # Vytvoření tabulky memories
                    cur.execute("""
                        CREATE TABLE memories (
                            id SERIAL PRIMARY KEY,
                            text TEXT NOT NULL,
                            location VARCHAR(255) NOT NULL,
                            coordinates GEOMETRY(POINT, 4326) NOT NULL,
                            keywords TEXT[] DEFAULT '{}',
                            source VARCHAR(255),
                            date DATE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    conn.commit()
                    print("Tabulka memories úspěšně vytvořena.")
                except Exception as e:
                    print(f"Chyba při vytváření tabulky: {str(e)}")
                    conn.rollback()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Nelze vytvořit tabulku memories: {str(e)}"
                    )
            
            try:
                # Vložení nové vzpomínky do databáze
                cur.execute("""
                    INSERT INTO memories (text, location, coordinates, keywords, source, date)
                    VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
                    RETURNING id, text, location, keywords, source, date, 
                              ST_X(coordinates) as longitude, ST_Y(coordinates) as latitude;
                """, (
                    memory.text,
                    memory.location,
                    memory.longitude,
                    memory.latitude,
                    keywords,
                    memory.source,
                    memory.date
                ))
                
                # Získání vloženého záznamu
                new_memory = cur.fetchone()
                conn.commit()
                
                if new_memory:
                    # Převod na slovník a vrácení jako odpověď
                    return dict(new_memory)
                else:
                    raise HTTPException(status_code=500, detail="Failed to retrieve the newly added memory")
                
            except Exception as e:
                # Rollback v případě chyby
                conn.rollback()
                print(f"Chyba při vkládání vzpomínky: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
                
    except Exception as e:
        print(f"Obecná chyba při přidávání vzpomínky: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Nepřidáváme finally blok, který by zavíral připojení, protože používáme connection pool

# Spuštění aplikace, pokud je tento soubor spuštěn přímo
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 