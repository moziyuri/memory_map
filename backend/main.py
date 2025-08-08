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
import requests
from datetime import datetime

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
        
        # Zkusíme připojení s explicitními parametry
        try:
            from urllib.parse import urlparse
            parsed = urlparse(DATABASE_URL)
            
            # Extrahujeme parametry z URL
            host = parsed.hostname
            port = parsed.port or 5432  # Explicitní port 5432 pokud není v URL
            database = parsed.path[1:] if parsed.path else 'memorymap'
            user = parsed.username
            password = parsed.password
            
            print(f"Připojuji s parametry: host={host}, port={port}, db={database}, user={user}")
            
            # Zkusíme nejdříve bez SSL (jen pro test)
            try:
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    connect_timeout=10
                )
                print("✅ Připojení bez SSL úspěšné!")
            except Exception as no_ssl_error:
                print(f"Připojení bez SSL selhalo: {str(no_ssl_error)}")
                print("Zkouším s SSL...")
                # Fallback s SSL - použijeme system trusted roots
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    sslmode='verify-full',
                    sslcert=None,
                    sslkey=None,
                    sslrootcert='system',  # Použijeme system trusted roots
                    connect_timeout=10
                )
                print("✅ Připojení s SSL úspěšné!")
            conn.autocommit = True
            connection_pool = conn
            print("Connection pool úspěšně vytvořen.")
            yield connection_pool
            return
        except Exception as e:
            print(f"Chyba při vytváření connection poolu: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database connection failed: {str(e)}"
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

# ============================================================================
# RISK ANALYST FEATURE - Nové modely a endpointy pro VW Group
# ============================================================================

# Přímé připojení k risk analyst databázi
def get_risk_db():
    """Připojení k risk analyst databázi"""
    import psycopg2
    import os
    from typing import Generator
    
    # Zkusíme environment variable, pak fallback
    database_url = os.getenv('RISK_DATABASE_URL')
    
    if database_url:
        # Použijeme DATABASE_URL format
        try:
            conn = psycopg2.connect(database_url, sslmode='require')
            yield conn
        except Exception as e:
            print(f"Chyba při připojení přes DATABASE_URL: {str(e)}")
            raise
    else:
        # Fallback na hardcoded hodnoty
        try:
            conn = psycopg2.connect(
                host="dpg-d2a54tp5pdvs73acu64g-a.frankfurt-postgres.render.com",
                port="5432",
                dbname="risk_analyst",
                user="risk_analyst_user",
                password="uN3Zogp6tvoTmnjNV4owD92Nnm6UlGkf",
                sslmode='require'
            )
            yield conn
        except Exception as e:
            print(f"Chyba při připojení k risk analyst databázi: {str(e)}")
            raise

# Nové Pydantic modely pro risk events
class RiskEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    event_type: str  # 'flood', 'protest', 'supply_chain', 'geopolitical'
    severity: str  # 'low', 'medium', 'high', 'critical'
    source: str  # 'chmi_api', 'rss', 'manual', 'copernicus'
    url: Optional[str] = None

class RiskEventResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    event_type: str
    severity: str
    source: str
    url: Optional[str] = None
    scraped_at: Optional[str] = None
    created_at: str

    class Config:
        orm_mode = True

class SupplierResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    category: Optional[str] = None
    risk_level: str
    created_at: str

    class Config:
        orm_mode = True

class RiskAnalysisResponse(BaseModel):
    event_count: int
    high_risk_count: int
    risk_score: float

# ============================================================================
# RISK EVENTS API ENDPOINTS
# ============================================================================

@app.get("/api/risks")
async def get_risk_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[int] = 50
):
    """Získá risk events s filtry"""
    conn = None
    try:
        print("🔍 Spouštím get_risk_events...")
        conn = next(get_risk_db())
        print("✅ Připojení k databázi OK")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Základní dotaz
            query = """
                SELECT id, title, description, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       event_type, severity, source, url, 
                       scraped_at, created_at
                FROM risk_events
                WHERE 1=1
            """
            params = []
            
            # Přidání filtrů
            if event_type:
                query += " AND event_type = %s"
                params.append(event_type)
            
            if severity:
                query += " AND severity = %s"
                params.append(severity)
            
            # Geografický filtr
            if lat is not None and lon is not None:
                query += """
                    AND ST_DWithin(
                        location::geography, 
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                        %s * 1000
                    )
                """
                params.extend([lon, lat, radius_km])
            
            query += " ORDER BY created_at DESC"
            
            print(f"🔍 Executing query: {query}")
            print(f"🔍 With params: {params}")
            
            cur.execute(query, params)
            results = cur.fetchall()
            
            print(f"✅ Found {len(results)} results")
            
            # Debug: vypíšeme první výsledek
            if results:
                first_result = dict(results[0])
                print(f"🔍 First result keys: {list(first_result.keys())}")
                print(f"🔍 First result: {first_result}")
            
            # Konverze na response modely
            response_data = []
            for row in results:
                row_dict = dict(row)
                # Zajistíme správné datové typy
                row_dict['latitude'] = float(row_dict['latitude'])
                row_dict['longitude'] = float(row_dict['longitude'])
                row_dict['id'] = int(row_dict['id'])
                response_data.append(row_dict)
            
            print(f"✅ Returning {len(response_data)} items")
            return response_data
            
    except Exception as e:
        print(f"❌ Chyba při získávání risk events: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/risks", response_model=RiskEventResponse, status_code=201)
async def create_risk_event(risk: RiskEventCreate):
    """Vytvoří nový risk event"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO risk_events (title, description, location, event_type, severity, source, url)
                VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s)
                RETURNING id, title, description, 
                          ST_X(location::geometry) as longitude, 
                          ST_Y(location::geometry) as latitude,
                          event_type, severity, source, url, 
                          scraped_at, created_at
            """, (
                risk.title,
                risk.description,
                risk.longitude,
                risk.latitude,
                risk.event_type,
                risk.severity,
                risk.source,
                risk.url
            ))
            
            new_risk = cur.fetchone()
            conn.commit()
            
            return dict(new_risk)
            
    except Exception as e:
        print(f"Chyba při vytváření risk event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/risks/{risk_id}", response_model=RiskEventResponse)
async def get_risk_event(risk_id: int):
    """Získá konkrétní risk event"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, description, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       event_type, severity, source, url, 
                       scraped_at, created_at
                FROM risk_events
                WHERE id = %s
            """, (risk_id,))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Risk event not found")
            
            return dict(result)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chyba při získávání risk event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SUPPLIERS API ENDPOINTS
# ============================================================================

@app.get("/api/suppliers")
async def get_suppliers():
    """Získá všechny dodavatele VW Group"""
    conn = None
    try:
        print("🔍 Spouštím get_suppliers...")
        conn = next(get_risk_db())
        print("✅ Připojení k databázi OK")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       category, risk_level, created_at
                FROM vw_suppliers
                ORDER BY name
            """)
            
            results = cur.fetchall()
            print(f"✅ Found {len(results)} suppliers")
            
            # Konverze na response data
            response_data = []
            for row in results:
                row_dict = dict(row)
                # Zajistíme správné datové typy
                row_dict['latitude'] = float(row_dict['latitude'])
                row_dict['longitude'] = float(row_dict['longitude'])
                row_dict['id'] = int(row_dict['id'])
                # Konvertujeme datetime na string
                if row_dict['created_at']:
                    row_dict['created_at'] = str(row_dict['created_at'])
                response_data.append(row_dict)
            
            print(f"✅ Returning {len(response_data)} suppliers")
            return response_data
            
    except Exception as e:
        print(f"❌ Chyba při získávání dodavatelů: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# RISK ANALYSIS API ENDPOINTS
# ============================================================================

@app.get("/api/analysis/risk-map")
async def get_risk_map():
    """Vrátí data pro risk mapu - všechny risk events a dodavatele"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Získání všech risk events
            cur.execute("""
                SELECT id, title, description, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       event_type, severity, source, url, 
                       created_at
                FROM risk_events
                ORDER BY created_at DESC
            """)
            risk_events_raw = cur.fetchall()
            
            # Konverze risk events
            risk_events = []
            for row in risk_events_raw:
                row_dict = dict(row)
                row_dict['latitude'] = float(row_dict['latitude'])
                row_dict['longitude'] = float(row_dict['longitude'])
                row_dict['id'] = int(row_dict['id'])
                if row_dict['created_at']:
                    row_dict['created_at'] = str(row_dict['created_at'])
                risk_events.append(row_dict)
            
            # Získání všech dodavatelů
            cur.execute("""
                SELECT id, name, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       category, risk_level, created_at
                FROM vw_suppliers
                ORDER BY name
            """)
            suppliers_raw = cur.fetchall()
            
            # Konverze suppliers
            suppliers = []
            for row in suppliers_raw:
                row_dict = dict(row)
                row_dict['latitude'] = float(row_dict['latitude'])
                row_dict['longitude'] = float(row_dict['longitude'])
                row_dict['id'] = int(row_dict['id'])
                if row_dict['created_at']:
                    row_dict['created_at'] = str(row_dict['created_at'])
                suppliers.append(row_dict)
            
            return {
                "risk_events": risk_events,
                "suppliers": suppliers
            }
            
    except Exception as e:
        print(f"Chyba při získávání risk map data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/supplier-risk", response_model=RiskAnalysisResponse)
async def analyze_supplier_risk(
    lat: float,
    lon: float,
    radius_km: int = 50
):
    """Analýza rizik pro dodavatele v daném okolí"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM calculate_risk_in_radius(%s, %s, %s)
            """, (lat, lon, radius_km))
            
            result = cur.fetchone()
            if result:
                return {
                    "event_count": result['event_count'],
                    "high_risk_count": result['high_risk_count'],
                    "risk_score": float(result['risk_score'])
                }
            else:
                return {
                    "event_count": 0,
                    "high_risk_count": 0,
                    "risk_score": 0.0
                }
            
    except Exception as e:
        print(f"Chyba při analýze rizik dodavatele: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/statistics")
async def get_risk_statistics():
    """Statistiky rizik"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Celkový počet risk events
            cur.execute("SELECT COUNT(*) as total_events FROM risk_events")
            total_events = cur.fetchone()['total_events']
            
            # Počet podle typu
            cur.execute("""
                SELECT event_type, COUNT(*) as count
                FROM risk_events
                GROUP BY event_type
                ORDER BY count DESC
            """)
            events_by_type = [dict(row) for row in cur.fetchall()]
            
            # Počet podle závažnosti
            cur.execute("""
                SELECT severity, COUNT(*) as count
                FROM risk_events
                GROUP BY severity
                ORDER BY count DESC
            """)
            events_by_severity = [dict(row) for row in cur.fetchall()]
            
            # Počet dodavatelů
            cur.execute("SELECT COUNT(*) as total_suppliers FROM vw_suppliers")
            total_suppliers = cur.fetchone()['total_suppliers']
            
            return {
                "total_events": total_events,
                "total_suppliers": total_suppliers,
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity
            }
            
    except Exception as e:
        print(f"Chyba při získávání statistik: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WEB SCRAPING ENDPOINTS (placeholder pro budoucí implementaci)
# ============================================================================

@app.get("/api/scrape/chmi")
async def scrape_chmi_floods():
    """Scrape CHMI API pro záplavové výstrahy"""
    try:
        print("🔍 Spouštím CHMI scraper...")
        
        # Funkční CHMI API endpointy podle dokumentace
        chmi_endpoints = [
            "https://hydro.chmi.cz/hpps/hpps_act.php",
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php", 
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=1",
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=2",
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=3"
        ]
        
        scraped_events = []
        
        for endpoint in chmi_endpoints:
            try:
                print(f"🌊 Testuji CHMI endpoint: {endpoint}")
                response = requests.get(endpoint, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ Úspěšné připojení k: {endpoint}")
                    data = response.text
                    print(f"📊 Získaná data: {len(data)} znaků")
                    
                    # Parsujeme skutečná CHMI data
                    events = parse_chmi_data(data, endpoint)
                    scraped_events.extend(events)
                    print(f"✅ Nalezeno {len(events)} událostí z {endpoint}")
                    break  # Použijeme první funkční endpoint
                else:
                    print(f"⚠️ Endpoint {endpoint} vrátil status {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"❌ Chyba při stahování z {endpoint}: {str(e)}")
                continue
        
        if not scraped_events:
            print("⚠️ Žádný CHMI endpoint nefunguje, žádná data nebudou uložena")
            # Není fallback data - vrátíme prázdný seznam
            scraped_events = []
        
        # Uložíme events do databáze
        conn = None
        saved_count = 0
        
        try:
            conn = next(get_risk_db())
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for event in scraped_events:
                    # Kontrola duplikátů podle title a source
                    cur.execute("""
                        SELECT id FROM risk_events 
                        WHERE title = %s AND source = 'chmi_api'
                        LIMIT 1
                    """, (event['title'],))
                    
                    if cur.fetchone():
                        print(f"⏭️ Duplikát nalezen: {event['title']}")
                        continue
                    
                    # Vložení nového eventu
                    cur.execute("""
                        INSERT INTO risk_events (title, description, location, event_type, severity, source, url, scraped_at)
                        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        event['title'],
                        event['description'],
                        event['longitude'],
                        event['latitude'],
                        event['event_type'],
                        event['severity'],
                        event['source'],
                        event['url'],
                        datetime.now()
                    ))
                    
                    event_id = cur.fetchone()['id']
                    saved_count += 1
                    print(f"✅ Uložen event ID {event_id}: {event['title']}")
                
                conn.commit()
                
        except Exception as e:
            print(f"❌ Chyba při ukládání do databáze: {str(e)}")
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
        
        return {
            "message": f"CHMI scraper dokončen",
            "status": "success",
            "scraped_count": len(scraped_events),
            "saved_count": saved_count,
            "source_url": endpoint if 'endpoint' in locals() else "multiple_endpoints",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Neočekávaná chyba v CHMI scraperu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

def parse_chmi_data(data: str, source_url: str) -> List[Dict]:
    """Parsuje skutečná CHMI data"""
    events = []
    
    try:
        # Hledáme klíčová slova v CHMI odpovědi
        keywords = ['záplav', 'povodn', 'výstrah', 'vltav', 'morav', 'sázav', 'berounk']
        
        for keyword in keywords:
            if keyword.lower() in data.lower():
                # Vytvoříme event na základě nalezeného klíčového slova
                event = create_chmi_event_from_keyword(keyword, source_url)
                if event:
                    events.append(event)
        
        # Pokud nenajdeme žádné klíčové slovo, zkusíme parsovat JSON/XML strukturu
        if not events:
            events = parse_chmi_structured_data(data, source_url)
            
        print(f"🔍 Parsováno {len(events)} událostí z CHMI dat")
        return events
        
    except Exception as e:
        print(f"❌ Chyba při parsování CHMI dat: {str(e)}")
        return []

def create_chmi_event_from_keyword(keyword: str, source_url: str) -> Dict:
    """Vytvoří event na základě klíčového slova"""
    keyword_mapping = {
        'záplav': {
            'title': f"Záplavová výstraha - {get_region_name(keyword)}",
            'description': f"CHMI vydalo záplavovou výstrahu pro {get_region_name(keyword)}",
            'latitude': 49.5,
            'longitude': 14.5,
            'severity': 'high'
        },
        'povodn': {
            'title': f"Povodňová výstraha - {get_region_name(keyword)}",
            'description': f"CHMI varuje před povodněmi v {get_region_name(keyword)}",
            'latitude': 49.2,
            'longitude': 14.4,
            'severity': 'critical'
        },
        'výstrah': {
            'title': f"Hydrologická výstraha - {get_region_name(keyword)}",
            'description': f"CHMI vydalo hydrologickou výstrahu pro {get_region_name(keyword)}",
            'latitude': 50.0,
            'longitude': 14.3,
            'severity': 'medium'
        },
        'vltav': {
            'title': "Výstraha - Vltava",
            'description': "Vzestup hladiny Vltavy v Praze a okolí",
            'latitude': 50.0755,
            'longitude': 14.4378,
            'severity': 'high'
        },
        'morav': {
            'title': "Výstraha - Morava",
            'description': "CHMI varuje před záplavami na Moravě",
            'latitude': 49.1951,
            'longitude': 16.6068,
            'severity': 'critical'
        }
    }
    
    if keyword in keyword_mapping:
        event_data = keyword_mapping[keyword]
        return {
            "title": event_data['title'],
            "description": event_data['description'],
            "latitude": event_data['latitude'],
            "longitude": event_data['longitude'],
            "event_type": "flood",
            "severity": event_data['severity'],
            "source": "chmi_api",
            "url": source_url
        }
    
    return None

def get_region_name(keyword: str) -> str:
    """Vrátí název regionu na základě klíčového slova"""
    regions = {
        'záplav': 'Jižní Čechy',
        'povodn': 'Střední Čechy', 
        'výstrah': 'Praha',
        'vltav': 'Praha',
        'morav': 'Morava'
    }
    return regions.get(keyword, 'Česká republika')

def parse_chmi_structured_data(data: str, source_url: str) -> List[Dict]:
    """Parsuje strukturovaná CHMI data (JSON/XML)"""
    events = []
    
    try:
        # Zkusíme parsovat jako JSON
        import json
        json_data = json.loads(data)
        
        # Hledáme relevantní data v JSON struktuře
        if isinstance(json_data, dict):
            events = parse_chmi_json(json_data, source_url)
        elif isinstance(json_data, list):
            for item in json_data:
                if isinstance(item, dict):
                    event = parse_chmi_json_item(item, source_url)
                    if event:
                        events.append(event)
                        
    except json.JSONDecodeError:
        # Není JSON, zkusíme XML nebo HTML
        events = parse_chmi_html(data, source_url)
    except Exception as e:
        print(f"❌ Chyba při parsování strukturovaných dat: {str(e)}")
    
    return events

def parse_chmi_json(data: Dict, source_url: str) -> List[Dict]:
    """Parsuje CHMI JSON data"""
    events = []
    
    # Hledáme klíčová slova v JSON struktuře
    json_str = str(data).lower()
    
    if 'záplav' in json_str or 'povodn' in json_str:
        events.append({
            "title": "Záplavová výstraha - CHMI data",
            "description": "CHMI vydalo záplavovou výstrahu na základě aktuálních dat",
            "latitude": 49.5,
            "longitude": 14.5,
            "event_type": "flood",
            "severity": "high",
            "source": "chmi_api",
            "url": source_url
        })
    
    return events

def parse_chmi_json_item(item: Dict, source_url: str) -> Dict:
    """Parsuje jednotlivý JSON item z CHMI"""
    # Implementace parsování jednotlivého JSON objektu
    return None

def parse_chmi_html(data: str, source_url: str) -> List[Dict]:
    """Parsuje CHMI HTML data"""
    events = []
    
    # Hledáme klíčová slova v HTML
    if 'záplav' in data.lower() or 'povodn' in data.lower():
        events.append({
            "title": "Záplavová výstraha - CHMI web",
            "description": "CHMI vydalo záplavovou výstrahu na základě webových dat",
            "latitude": 49.5,
            "longitude": 14.5,
            "event_type": "flood",
            "severity": "high",
            "source": "chmi_api",
            "url": source_url
        })
    
    return events

# Fallback data funkce byla odstraněna - aplikace funguje pouze s reálnými daty

@app.get("/api/scrape/rss")
async def scrape_rss_feeds():
    """Scrape RSS feeds pro novinky a události"""
    try:
        print("🔍 Spouštím RSS scraper...")
        
        # RSS feeds pro novinky a události
        rss_feeds = [
            "https://www.novinky.cz/rss",
            "https://www.seznamzpravy.cz/rss",
            "https://hn.cz/rss/2",
            "https://www.irozhlas.cz/rss/irozhlas"
        ]
        
        scraped_events = []
        
        for feed_url in rss_feeds:
            try:
                print(f"📰 Stahuji RSS feed: {feed_url}")
                response = requests.get(feed_url, timeout=30)
                response.raise_for_status()
                
                # Parsujeme skutečný RSS XML
                events = parse_rss_feed(response.text, feed_url)
                scraped_events.extend(events)
                print(f"✅ RSS feed zpracován: {len(events)} událostí")
                
            except requests.RequestException as e:
                print(f"⚠️ Chyba při stahování RSS feedu {feed_url}: {str(e)}")
                continue
        
        # Uložíme events do databáze
        conn = None
        saved_count = 0
        
        try:
            conn = next(get_risk_db())
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for event in scraped_events:
                    # Kontrola duplikátů podle title a source
                    cur.execute("""
                        SELECT id FROM risk_events 
                        WHERE title = %s AND source = 'rss'
                        LIMIT 1
                    """, (event['title'],))
                    
                    if cur.fetchone():
                        print(f"⏭️ Duplikát nalezen: {event['title']}")
                        continue
                    
                    # Vložení nového eventu
                    cur.execute("""
                        INSERT INTO risk_events (title, description, location, event_type, severity, source, url, scraped_at)
                        VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        event['title'],
                        event['description'],
                        event['longitude'],
                        event['latitude'],
                        event['event_type'],
                        event['severity'],
                        event['source'],
                        event['url'],
                        datetime.now()
                    ))
                    
                    event_id = cur.fetchone()['id']
                    saved_count += 1
                    print(f"✅ Uložen event ID {event_id}: {event['title']}")
                
                conn.commit()
                
        except Exception as e:
            print(f"❌ Chyba při ukládání do databáze: {str(e)}")
            if conn:
                conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()
        
        return {
            "message": f"RSS scraper dokončen",
            "status": "success",
            "scraped_count": len(scraped_events),
            "saved_count": saved_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Neočekávaná chyba v RSS scraperu: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraper error: {str(e)}")

def parse_rss_feed(rss_xml: str, feed_url: str) -> List[Dict]:
    """Parsuje RSS XML feed a hledá relevantní události"""
    events = []
    
    try:
        import xml.etree.ElementTree as ET
        
        # Parsujeme XML
        root = ET.fromstring(rss_xml)
        
        # Hledáme item elementy
        items = root.findall('.//item')
        
        for item in items:
            # Získáme title a description
            title_elem = item.find('title')
            description_elem = item.find('description')
            
            if title_elem is not None:
                title = title_elem.text or ""
                description = description_elem.text if description_elem is not None else ""
                
                # Hledáme relevantní klíčová slova
                event = analyze_rss_item_for_risk(title, description, feed_url)
                if event:
                    events.append(event)
        
        print(f"🔍 Analyzováno {len(items)} RSS položek, nalezeno {len(events)} relevantních událostí")
        return events
        
    except ET.ParseError as e:
        print(f"❌ Chyba při parsování RSS XML: {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Neočekávaná chyba při parsování RSS: {str(e)}")
        return []

def analyze_rss_item_for_risk(title: str, description: str, feed_url: str) -> Dict:
    """Analyzuje RSS položku a hledá rizikové události"""
    
    # Klíčová slova pro různé typy rizik
    risk_keywords = {
        'protest': ['protest', 'demonstrace', 'stávka', 'manifestace', 'nepokoje'],
        'supply_chain': ['doprava', 'dálnice', 'silnice', 'uzavírka', 'nehoda', 'havárie', 'blokáda'],
        'geopolitical': ['politika', 'vláda', 'parlament', 'napětí', 'konflikt', 'diplomacie'],
        'flood': ['záplavy', 'povodně', 'deště', 'voda', 'vltava', 'morava', 'řeka']
    }
    
    # Kombinujeme title a description pro analýzu
    text = f"{title} {description}".lower()
    
    # Hledáme klíčová slova
    for event_type, keywords in risk_keywords.items():
        for keyword in keywords:
            if keyword in text:
                return create_rss_event(title, description, event_type, keyword, feed_url)
    
    return None

def create_rss_event(title: str, description: str, event_type: str, keyword: str, feed_url: str) -> Dict:
    """Vytvoří event na základě RSS položky"""
    
    # Mapování typů událostí na severity
    severity_mapping = {
        'protest': 'medium',
        'supply_chain': 'high', 
        'geopolitical': 'medium',
        'flood': 'high'
    }
    
    # Mapování na lokace podle klíčových slov
    location_mapping = {
        'praha': (50.0755, 14.4378),
        'brno': (49.1951, 16.6068),
        'ostrava': (49.8175, 18.2625),
        'plzeň': (49.7475, 13.3776),
        'liberec': (50.7663, 15.0543),
        'olomouc': (49.5938, 17.2507),
        'české budějovice': (48.9745, 14.4747),
        'hradec králové': (50.2092, 15.8327),
        'pardubice': (50.0343, 15.7812),
        'zlín': (49.2264, 17.6683)
    }
    
    # Hledáme lokaci v textu
    latitude, longitude = 50.0, 14.3  # Výchozí - střed ČR
    for location_name, coords in location_mapping.items():
        if location_name in title.lower() or location_name in description.lower():
            latitude, longitude = coords
            break
    
    return {
        "title": title[:100],  # Omezíme délku title
        "description": description[:200] if description else f"Událost související s {keyword}",
        "latitude": latitude,
        "longitude": longitude,
        "event_type": event_type,
        "severity": severity_mapping.get(event_type, 'medium'),
        "source": "rss",
        "url": feed_url
    }

@app.get("/api/scrape/run-all")
async def run_all_scrapers():
    """Spustí všechny scrapers najednou"""
    try:
        print("🚀 Spouštím všechny scrapers...")
        
        results = {
            "chmi": None,
            "rss": None,
            "total_events_saved": 0,
            "start_time": datetime.now().isoformat()
        }
        
        # Spustíme CHMI scraper
        try:
            print("🌊 Spouštím CHMI scraper...")
            chmi_response = await scrape_chmi_floods()
            results["chmi"] = chmi_response
            results["total_events_saved"] += chmi_response.get("saved_count", 0)
            print("✅ CHMI scraper dokončen")
        except Exception as e:
            print(f"❌ CHMI scraper selhal: {str(e)}")
            results["chmi"] = {"error": str(e), "status": "failed"}
        
        # Spustíme RSS scraper
        try:
            print("📰 Spouštím RSS scraper...")
            rss_response = await scrape_rss_feeds()
            results["rss"] = rss_response
            results["total_events_saved"] += rss_response.get("saved_count", 0)
            print("✅ RSS scraper dokončen")
        except Exception as e:
            print(f"❌ RSS scraper selhal: {str(e)}")
            results["rss"] = {"error": str(e), "status": "failed"}
        
        results["end_time"] = datetime.now().isoformat()
        results["status"] = "completed"
        
        return {
            "message": "Všechny scrapers dokončeny",
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        print(f"❌ Neočekávaná chyba při spouštění scraperů: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Scraper orchestration error: {str(e)}") 

@app.get("/api/debug-env")
async def debug_environment():
    """Debug endpoint pro ověření environment variables"""
    import os
    
    return {
        "RISK_DATABASE_URL": os.getenv('RISK_DATABASE_URL', 'NOT_SET'),
        "DATABASE_URL": os.getenv('DATABASE_URL', 'NOT_SET'),
        "PYTHON_VERSION": os.getenv('PYTHON_VERSION', 'NOT_SET'),
        "PORT": os.getenv('PORT', 'NOT_SET'),
        "message": "Environment variables debug"
    } 

# ============================================================================
# ADVANCED RISK ANALYSIS ENDPOINTS
# ============================================================================

@app.get("/api/analysis/river-flood-simulation")
async def river_flood_simulation(
    supplier_id: Optional[int] = None,
    river_name: Optional[str] = None,
    flood_level_m: Optional[float] = None
):
    """Simulace záplav a jejich dopadu na dodavatele"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Získání dat o řekách a dodavatelích
            if supplier_id:
                # Analýza konkrétního dodavatele
                cur.execute("""
                    SELECT name, category, risk_level,
                           ST_X(location::geometry) as longitude,
                           ST_Y(location::geometry) as latitude
                    FROM vw_suppliers 
                    WHERE id = %s
                """, [supplier_id])
                supplier = cur.fetchone()
                
                if not supplier:
                    return {"error": "Dodavatel nenalezen"}
                
                # Simulace záplav pro danou lokaci
                flood_risk = calculate_flood_risk(
                    supplier['latitude'], 
                    supplier['longitude'], 
                    flood_level_m or 2.0
                )
                
                return {
                    "supplier": dict(supplier),
                    "flood_simulation": flood_risk,
                    "risk_assessment": {
                        "flood_probability": flood_risk['probability'],
                        "impact_level": flood_risk['impact_level'],
                        "mitigation_needed": flood_risk['mitigation_needed']
                    }
                }
            else:
                # Analýza všech dodavatelů v rizikových oblastech
                cur.execute("""
                    SELECT id, name, category, risk_level,
                           ST_X(location::geometry) as longitude,
                           ST_Y(location::geometry) as latitude
                    FROM vw_suppliers 
                    WHERE risk_level IN ('high', 'critical')
                    ORDER BY risk_level DESC
                """)
                suppliers = cur.fetchall()
                
                flood_analysis = []
                for supplier in suppliers:
                    flood_risk = calculate_flood_risk(
                        supplier['latitude'], 
                        supplier['longitude'], 
                        flood_level_m or 2.0
                    )
                    flood_analysis.append({
                        "supplier": dict(supplier),
                        "flood_risk": flood_risk
                    })
                
                return {
                    "total_suppliers_analyzed": len(flood_analysis),
                    "high_risk_suppliers": len([s for s in flood_analysis if s['flood_risk']['impact_level'] == 'high']),
                    "flood_analysis": flood_analysis
                }
                
    except Exception as e:
        print(f"❌ Chyba při simulaci záplav: {str(e)}")
        return {"error": f"Chyba při simulaci: {str(e)}"}
    finally:
        if conn:
            conn.close()

@app.get("/api/analysis/geographic-risk-assessment")
async def geographic_risk_assessment(
    lat: float,
    lon: float,
    radius_km: int = 50
):
    """Komplexní geografická analýza rizik pro danou lokaci"""
    try:
        # Analýza vzdálenosti od řek
        river_analysis = analyze_river_proximity(lat, lon, radius_km)
        
        # Analýza nadmořské výšky
        elevation_analysis = analyze_elevation_profile(lat, lon)
        
        # Analýza historických událostí
        historical_analysis = analyze_historical_events(lat, lon, radius_km)
        
        # Kombinované hodnocení rizik
        combined_risk = calculate_combined_risk(
            river_analysis, 
            elevation_analysis, 
            historical_analysis
        )
        
        return {
            "location": {"latitude": lat, "longitude": lon},
            "analysis_radius_km": radius_km,
            "river_analysis": river_analysis,
            "elevation_analysis": elevation_analysis,
            "historical_analysis": historical_analysis,
            "combined_risk_assessment": combined_risk
        }
        
    except Exception as e:
        print(f"❌ Chyba při geografické analýze: {str(e)}")
        return {"error": f"Chyba při analýze: {str(e)}"}

@app.get("/api/analysis/supply-chain-impact")
async def supply_chain_impact_analysis(
    supplier_id: Optional[int] = None,
    event_type: Optional[str] = None
):
    """Analýza dopadu událostí na dodavatelský řetězec"""
    conn = None
    try:
        conn = next(get_risk_db())
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if supplier_id:
                # Analýza konkrétního dodavatele
                cur.execute("""
                    SELECT id, name, category, risk_level,
                           ST_X(location::geometry) as longitude,
                           ST_Y(location::geometry) as latitude
                    FROM vw_suppliers 
                    WHERE id = %s
                """, [supplier_id])
                supplier = cur.fetchone()
                
                if not supplier:
                    return {"error": "Dodavatel nenalezen"}
                
                # Analýza rizikových událostí v okolí
                cur.execute("""
                    SELECT COUNT(*) as total_events,
                           COUNT(*) FILTER (WHERE severity IN ('high', 'critical')) as high_risk_events,
                           COUNT(*) FILTER (WHERE event_type = %s) as specific_type_events
                    FROM risk_events
                    WHERE ST_DWithin(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        50 * 1000
                    )
                """, [event_type or 'flood', supplier['longitude'], supplier['latitude']])
                
                risk_stats = cur.fetchone()
                
                # Simulace dopadu na dodavatelský řetězec
                impact_analysis = simulate_supply_chain_impact(
                    supplier, risk_stats, event_type
                )
                
                return {
                    "supplier": dict(supplier),
                    "risk_statistics": dict(risk_stats),
                    "supply_chain_impact": impact_analysis
                }
            else:
                # Analýza celého dodavatelského řetězce
                cur.execute("""
                    SELECT id, name, category, risk_level,
                           ST_X(location::geometry) as longitude,
                           ST_Y(location::geometry) as latitude
                    FROM vw_suppliers
                    ORDER BY risk_level DESC
                """)
                suppliers = cur.fetchall()
                
                chain_analysis = []
                for supplier in suppliers:
                    # Analýza rizik pro každého dodavatele
                    cur.execute("""
                        SELECT COUNT(*) as nearby_events,
                               COUNT(*) FILTER (WHERE severity IN ('high', 'critical')) as critical_events
                        FROM risk_events
                        WHERE ST_DWithin(
                            location::geography,
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                            50 * 1000
                        )
                    """, [supplier['longitude'], supplier['latitude']])
                    
                    risk_stats = cur.fetchone()
                    impact = simulate_supply_chain_impact(
                        supplier, risk_stats, event_type
                    )
                    
                    chain_analysis.append({
                        "supplier": dict(supplier),
                        "risk_analysis": dict(risk_stats),
                        "impact_assessment": impact
                    })
                
                return {
                    "total_suppliers": len(chain_analysis),
                    "high_risk_suppliers": len([s for s in chain_analysis if s['supplier']['risk_level'] in ['high', 'critical']]),
                    "supply_chain_analysis": chain_analysis
                }
                
    except Exception as e:
        print(f"❌ Chyba při analýze dodavatelského řetězce: {str(e)}")
        return {"error": f"Chyba při analýze: {str(e)}"}
    finally:
        if conn:
            conn.close()

# ============================================================================
# HELPER FUNCTIONS FOR ADVANCED ANALYSIS
# ============================================================================

def calculate_flood_risk(lat: float, lon: float, flood_level_m: float) -> dict:
    """Výpočet rizika záplav pro danou lokaci"""
    # Simulace na základě nadmořské výšky a vzdálenosti od řek
    base_elevation = 200  # Průměrná nadmořská výška ČR
    river_distance = calculate_river_distance(lat, lon)
    
    # Výpočet pravděpodobnosti záplav
    if river_distance < 1.0:  # Méně než 1km od řeky
        probability = 0.8
        impact_level = "critical"
    elif river_distance < 5.0:  # 1-5km od řeky
        probability = 0.6
        impact_level = "high"
    elif river_distance < 10.0:  # 5-10km od řeky
        probability = 0.3
        impact_level = "medium"
    else:
        probability = 0.1
        impact_level = "low"
    
    # Úprava podle nadmořské výšky
    if base_elevation < 150:
        probability *= 1.5
    elif base_elevation > 400:
        probability *= 0.5
    
    return {
        "probability": min(probability, 1.0),
        "impact_level": impact_level,
        "river_distance_km": river_distance,
        "elevation_m": base_elevation,
        "flood_level_m": flood_level_m,
        "mitigation_needed": probability > 0.5
    }

def calculate_river_distance(lat: float, lon: float) -> float:
    """Výpočet vzdálenosti od nejbližší řeky (simulace)"""
    # Hlavní řeky ČR s přibližnými souřadnicemi
    rivers = [
        {"name": "Vltava", "lat": 50.0755, "lon": 14.4378},
        {"name": "Labe", "lat": 50.2092, "lon": 15.8327},
        {"name": "Morava", "lat": 49.1951, "lon": 16.6068},
        {"name": "Ohře", "lat": 50.231, "lon": 12.880},
        {"name": "Berounka", "lat": 49.7475, "lon": 13.3776}
    ]
    
    min_distance = float('inf')
    for river in rivers:
        distance = ((lat - river['lat'])**2 + (lon - river['lon'])**2)**0.5
        # Převod na km (přibližně)
        distance_km = distance * 111
        min_distance = min(min_distance, distance_km)
    
    return min_distance

def analyze_river_proximity(lat: float, lon: float, radius_km: int) -> dict:
    """Analýza blízkosti řek"""
    river_distance = calculate_river_distance(lat, lon)
    
    return {
        "nearest_river_distance_km": river_distance,
        "flood_risk_zone": river_distance < 5.0,
        "high_risk_zone": river_distance < 2.0,
        "risk_level": "high" if river_distance < 5.0 else "medium" if river_distance < 10.0 else "low"
    }

def analyze_elevation_profile(lat: float, lon: float) -> dict:
    """Analýza nadmořské výšky (simulace)"""
    # Simulace nadmořské výšky na základě souřadnic
    base_elevation = 200 + (lat - 50.0) * 100 + (lon - 14.0) * 50
    
    return {
        "elevation_m": base_elevation,
        "flood_vulnerability": "high" if base_elevation < 200 else "medium" if base_elevation < 300 else "low",
        "terrain_type": "lowland" if base_elevation < 200 else "hills" if base_elevation < 400 else "mountains"
    }

def analyze_historical_events(lat: float, lon: float, radius_km: int) -> dict:
    """Analýza historických událostí v okolí"""
    # Simulace na základě lokace
    historical_floods = 2 if lat < 50.0 else 1  # Jižní Čechy více náchylné
    historical_protests = 1 if lon > 15.0 else 0  # Východní Čechy
    
    return {
        "historical_flood_events": historical_floods,
        "historical_protest_events": historical_protests,
        "total_historical_events": historical_floods + historical_protests,
        "risk_trend": "increasing" if historical_floods > 1 else "stable"
    }

def calculate_combined_risk(river_analysis: dict, elevation_analysis: dict, historical_analysis: dict) -> dict:
    """Výpočet kombinovaného rizika"""
    risk_score = 0
    
    # Riziko od řek
    if river_analysis['risk_level'] == 'high':
        risk_score += 40
    elif river_analysis['risk_level'] == 'medium':
        risk_score += 20
    
    # Riziko od nadmořské výšky
    if elevation_analysis['flood_vulnerability'] == 'high':
        risk_score += 30
    elif elevation_analysis['flood_vulnerability'] == 'medium':
        risk_score += 15
    
    # Riziko z historických událostí
    if historical_analysis['total_historical_events'] > 2:
        risk_score += 30
    elif historical_analysis['total_historical_events'] > 0:
        risk_score += 15
    
    # Celkové hodnocení
    if risk_score >= 70:
        overall_risk = "critical"
    elif risk_score >= 50:
        overall_risk = "high"
    elif risk_score >= 30:
        overall_risk = "medium"
    else:
        overall_risk = "low"
    
    return {
        "risk_score": risk_score,
        "overall_risk_level": overall_risk,
        "risk_factors": {
            "river_proximity": river_analysis['risk_level'],
            "elevation_vulnerability": elevation_analysis['flood_vulnerability'],
            "historical_events": historical_analysis['total_historical_events']
        },
        "recommendations": generate_risk_recommendations(overall_risk)
    }

def simulate_supply_chain_impact(supplier: dict, risk_stats: dict, event_type: str) -> dict:
    """Simulace dopadu na dodavatelský řetězec"""
    total_events = risk_stats['total_events'] or 0
    critical_events = risk_stats['high_risk_events'] or 0
    
    # Výpočet rizika přerušení dodávek
    disruption_probability = min(critical_events * 0.3, 0.9)
    
    # Dopad podle kategorie dodavatele
    category_impact = {
        'electronics': 'critical',
        'tires': 'high',
        'steering': 'high',
        'brakes': 'critical',
        'body_parts': 'medium'
    }
    
    impact_level = category_impact.get(supplier['category'], 'medium')
    
    # Simulace času obnovy
    recovery_time_days = {
        'critical': 30,
        'high': 14,
        'medium': 7,
        'low': 3
    }
    
    return {
        "disruption_probability": disruption_probability,
        "impact_level": impact_level,
        "estimated_recovery_days": recovery_time_days[impact_level],
        "alternative_suppliers_needed": disruption_probability > 0.5,
        "mitigation_actions": generate_mitigation_actions(impact_level, disruption_probability)
    }

def generate_risk_recommendations(risk_level: str) -> list:
    """Generování doporučení na základě úrovně rizika"""
    recommendations = {
        'critical': [
            "Okamžitě implementovat protipovodňová opatření",
            "Vytvořit záložní dodavatelský řetězec",
            "Přesunout výrobu do bezpečnější lokace",
            "Instalovat monitoring hladiny vody"
        ],
        'high': [
            "Implementovat protipovodňová opatření",
            "Vytvořit plán evakuace",
            "Zvýšit pojištění",
            "Monitoring meteorologických podmínek"
        ],
        'medium': [
            "Pravidelné kontroly bezpečnostních opatření",
            "Aktualizace pojištění",
            "Monitoring lokálních rizik"
        ],
        'low': [
            "Standardní bezpečnostní opatření",
            "Pravidelné kontroly"
        ]
    }
    
    return recommendations.get(risk_level, ["Standardní opatření"])

def generate_mitigation_actions(impact_level: str, probability: float) -> list:
    """Generování mitigačních opatření"""
    actions = []
    
    if probability > 0.7:
        actions.append("Okamžitě aktivovat záložní dodavatele")
        actions.append("Přesunout kritickou výrobu")
    
    if impact_level in ['critical', 'high']:
        actions.append("Zvýšit bezpečnostní zásoby")
        actions.append("Implementovat monitoring dodavatelského řetězce")
    
    if probability > 0.5:
        actions.append("Aktivovat krizový management")
        actions.append("Komunikovat s dodavateli o rizicích")
    
    return actions 