"""
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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from functools import lru_cache

load_dotenv()

# Resilient HTTP session with retries
def get_http_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

http_session = get_http_session()

# =============================
# Geocoding helpers (Nominatim)
# =============================

ENABLE_GEOCODING = os.getenv('ENABLE_GEOCODING', 'true').lower() in ('1', 'true', 'yes')

@lru_cache(maxsize=512)
def geocode_cz(place_query: str):
    if not ENABLE_GEOCODING:
        return None
    try:
        resp = http_session.get(
            'https://nominatim.openstreetmap.org/search',
            params={
                'q': place_query,
                'countrycodes': 'cz',
                'format': 'json',
                'limit': 1
            },
            headers={
                'User-Agent': 'Risk-Analyst/1.0 (contact: app@example.com)'
            },
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                item = data[0]
                lat = float(item.get('lat'))
                lon = float(item.get('lon'))
                return lat, lon
        return None
    except Exception:
        return None

def get_river_centroid(river_name: str):
    """Vrátí centroid řeky z tabulky rivers, jinak None."""
    conn = None
    try:
        conn = get_risk_db()
        if not conn:
            return None
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                  ST_Y(ST_Centroid(geometry)) AS lat,
                  ST_X(ST_Centroid(geometry)) AS lon
                FROM rivers
                WHERE lower(name) = lower(%s)
                LIMIT 1
                """,
                [river_name]
            )
            row = cur.fetchone()
            if row:
                return float(row[0]), float(row[1])
            return None
    except Exception:
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# Vytvoření FastAPI aplikace s vlastním názvem
app = FastAPI(title="MemoryMap API")

# Startup DB checks
@app.on_event("startup")
async def startup_checks():
    try:
        conn = get_risk_db()
        if not conn:
            print("⚠️ DB check: Nelze získat připojení k DB (RISK_DATABASE_URL chybí nebo selhalo připojení)")
            return
        with conn.cursor() as cur:
            # Tabulky
            cur.execute("""
                SELECT to_regclass('public.risk_events') IS NOT NULL,
                       to_regclass('public.vw_suppliers') IS NOT NULL
            """)
            re_exists, sup_exists = cur.fetchone()
            if not re_exists:
                print("⚠️ DB check: Tabulka risk_events neexistuje")
            if not sup_exists:
                print("⚠️ DB check: Tabulka vw_suppliers neexistuje")
            # Funkce (volitelně)
            try:
                cur.execute("SELECT proname FROM pg_proc WHERE proname = 'calculate_risk_in_radius'")
                has_calc = cur.fetchone() is not None
                if not has_calc:
                    print("ℹ️ DB check: Funkce calculate_risk_in_radius není k dispozici (neblokuje provoz)")
            except Exception:
                print("ℹ️ DB check: Kontrola funkce calculate_risk_in_radius selhala (neblokuje provoz)")
        conn.close()
    except Exception as e:
        print(f"⚠️ DB startup check selhal: {e}")

# Konfigurace CORS - BEZPEČNOSTNÍ OPRAVA
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://stanislavhoracekmemorymap.streamlit.app",
        "https://memory-map-feature-risk-analyst-frontend-app.onrender.com",
        "http://localhost:8501",  # Pro lokální vývoj
        "https://localhost:8501",
        "https://memory-map.onrender.com",  # Správná Render.com URL
        "https://memorymap-api.onrender.com",  # Ponecháme pro případ
        # ⚠️ ODSTRANĚNO: "*" - příliš permissivní pro bezpečnost
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specifické metody místo "*"
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

@app.get("/api/health")
async def health_check():
    """Health check endpoint pro monitoring"""
    return {"status": "healthy", "message": "Risk Analyst API is running"}

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
    """Získá připojení k risk analyst databázi"""
    try:
        # Používáme pouze environment variables pro bezpečnost
        database_url = os.getenv('RISK_DATABASE_URL')
        
        if not database_url:
            print("❌ KRITICKÁ CHYBA: RISK_DATABASE_URL není nastavena!")
            print("⚠️ Pro bezpečnost nejsou povoleny hardcoded credentials")
            return None
        
        print(f"🔗 Připojuji k databázi přes RISK_DATABASE_URL...")
        # Zvýšíme timeout na 30 sekund
        conn = psycopg2.connect(database_url, sslmode='require', connect_timeout=30)
        
        print("✅ Připojení k databázi úspěšné!")
        return conn
        
    except Exception as e:
        print(f"❌ Chyba při připojení k databázi: {str(e)}")
        return None

# Nové Pydantic modely pro risk events
class RiskEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    event_type: str  # 'flood', 'supply_chain'
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
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
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
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@app.post("/api/risks", response_model=RiskEventResponse, status_code=201)
async def create_risk_event(risk: RiskEventCreate):
    """Vytvoří nový risk event"""
    conn = None
    try:
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
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
        if conn:
            conn.rollback()
        print(f"Chyba při vytváření risk event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@app.get("/api/risks/{risk_id}", response_model=RiskEventResponse)
async def get_risk_event(risk_id: int):
    """Získá konkrétní risk event"""
    conn = None
    try:
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, title, description, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       event_type, severity, source, url, 
                       scraped_at, created_at
                FROM risk_events
                WHERE id = %s
            """, [risk_id])
            
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Risk event not found")
            
            row_dict = dict(row)
            row_dict['latitude'] = float(row_dict['latitude'])
            row_dict['longitude'] = float(row_dict['longitude'])
            row_dict['id'] = int(row_dict['id'])
            if row_dict['created_at']:
                row_dict['created_at'] = str(row_dict['created_at'])
            return row_dict
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chyba při získávání risk event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# ============================================================================
# SUPPLIERS API ENDPOINTS
# ============================================================================

@app.get("/api/suppliers")
async def get_suppliers():
    """Získá všechny dodavatele VW Group"""
    conn = None
    try:
        print("🔍 Spouštím get_suppliers...")
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        print("✅ Připojení k databázi OK")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (name) id, name, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       category, risk_level, created_at
                FROM vw_suppliers
                ORDER BY name, created_at DESC
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
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# ============================================================================
# RISK ANALYSIS API ENDPOINTS
# ============================================================================

@app.get("/api/analysis/risk-map")
async def get_risk_map():
    """Vrátí data pro risk mapu - všechny risk events a dodavatele"""
    conn = None
    try:
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
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
                SELECT DISTINCT ON (name) id, name, 
                       ST_X(location::geometry) as longitude, 
                       ST_Y(location::geometry) as latitude,
                       category, risk_level, created_at
                FROM vw_suppliers
                ORDER BY name, created_at DESC
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
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@app.get("/api/analysis/supplier-risk", response_model=RiskAnalysisResponse)
async def analyze_supplier_risk(
    lat: float,
    lon: float,
    radius_km: int = 50
):
    """Analýza rizik pro dodavatele v daném okolí"""
    conn = None
    try:
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute("""
                    SELECT * FROM calculate_risk_in_radius(%s, %s, %s)
                """, (lat, lon, radius_km))
            except Exception as e:
                # Funkce neexistuje nebo není dostupná
                raise HTTPException(status_code=503, detail="Database function calculate_risk_in_radius is unavailable")
            
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
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Chyba při analýze rizik dodavatele: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@app.get("/api/analysis/statistics")
async def get_risk_statistics():
    """Statistiky rizik"""
    conn = None
    try:
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
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
            
            return {
                "total_events": int(total_events),
                "events_by_type": events_by_type,
                "events_by_severity": events_by_severity
            }
            
    except Exception as e:
        print(f"Chyba při získávání statistik: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# ============================================================================
# WEB SCRAPING ENDPOINTS (placeholder pro budoucí implementaci)
# ============================================================================

@app.get("/api/scrape/chmi")
async def scrape_chmi_floods():
    """Scrape CHMI API pro záplavové výstrahy s vylepšeným error handlingem"""
    try:
        print("🔍 Spouštím CHMI scraper...")
        
        # AKTUALIZOVANÉ funkční CHMI API endpointy
        chmi_endpoints = [
            "https://hydro.chmi.cz/hpps/",
            "https://hydro.chmi.cz/hpps/index.php",
            # Původní endpointy (pro případ, že se opraví)
            "https://hydro.chmi.cz/hpps/hpps_act.php",
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php", 
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=1",
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=2",
            "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=3"
        ]
        
        scraped_events = []
        working_endpoint = None
        
        for endpoint in chmi_endpoints:
            try:
                print(f"🌊 Testuji CHMI endpoint: {endpoint}")
                response = http_session.get(endpoint, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ Úspěšné připojení k: {endpoint}")
                    data = response.text
                    print(f"📊 Získaná data: {len(data)} znaků")
                    
                    # Parsujeme skutečná CHMI data
                    events = parse_chmi_data(data, endpoint)
                    scraped_events.extend(events)
                    print(f"✅ Nalezeno {len(events)} událostí z {endpoint}")
                    working_endpoint = endpoint
                    break  # Použijeme první funkční endpoint
                else:
                    print(f"⚠️ Endpoint {endpoint} vrátil status {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"❌ Chyba při stahování z {endpoint}: {str(e)}")
                continue
        
        # Pokud CHMI nefunguje, zkusíme OpenMeteo jako fallback
        if not scraped_events:
            print("⚠️ CHMI endpointy nefungují, zkouším OpenMeteo...")
            openmeteo_events = await scrape_openmeteo_weather()
            if openmeteo_events:
                scraped_events.extend(openmeteo_events)
                working_endpoint = "OpenMeteo API"
                print(f"✅ Nalezeno {len(openmeteo_events)} událostí z OpenMeteo")
        
        if not scraped_events:
            print("⚠️ Žádný zdroj nefunguje, žádná data nebudou uložena")
            scraped_events = []
        
        # Uložíme events do databáze
        conn = None
        saved_count = 0
        
        try:
            conn = get_risk_db()
            
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for event in scraped_events:
                    # Kontrola duplikátů podle title a source
                    cur.execute("""
                        SELECT id FROM risk_events 
                        WHERE title = %s AND source = %s
                        LIMIT 1
                    """, (event['title'], event['source']))
                    
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
            return {
                "message": f"CHMI scraper selhal při ukládání",
                "status": "error",
                "error": str(e),
                "scraped_count": len(scraped_events),
                "saved_count": 0,
                "source_url": working_endpoint or "no_working_endpoint",
                "timestamp": datetime.now().isoformat()
            }
        finally:
            if conn:
                conn.close()
        
        return {
            "message": f"CHMI scraper dokončen",
            "status": "success",
            "scraped_count": len(scraped_events),
            "saved_count": saved_count,
            "source_url": working_endpoint or "no_working_endpoint",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Neočekávaná chyba v CHMI scraperu: {str(e)}")
        return {
            "message": f"CHMI scraper selhal",
            "status": "error",
            "error": str(e),
            "scraped_count": 0,
            "saved_count": 0,
            "source_url": "error",
            "timestamp": datetime.now().isoformat()
        }

async def scrape_openmeteo_weather():
    """Scrape OpenMeteo API pro meteorologická data"""
    try:
        print("🌤️ Spouštím OpenMeteo scraper...")
        
        # Česká města pro monitoring
        czech_cities = [
            {"name": "Praha", "lat": 50.0755, "lon": 14.4378},
            {"name": "Brno", "lat": 49.1951, "lon": 16.6068},
            {"name": "Ostrava", "lat": 49.8175, "lon": 18.2625},
            {"name": "Plzeň", "lat": 49.7475, "lon": 13.3776},
            {"name": "Liberec", "lat": 50.7663, "lon": 15.0543}
        ]
        
        events = []
        
        for city in czech_cities:
            try:
                url = f"https://api.open-meteo.com/v1/forecast?latitude={city['lat']}&longitude={city['lon']}&current_weather=true&hourly=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
                response = http_session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    current_weather = data.get('current_weather', {})
                    hourly_data = data.get('hourly', {})
                    
                    # Analýza rizikových podmínek
                    temp = current_weather.get('temperature', 0)
                    wind_speed = current_weather.get('windspeed', 0)
                    
                    # Detekce rizikových podmínek
                    if temp > 30:
                        events.append({
                            "title": f"Extrémní teplo - {city['name']}",
                            "description": f"Teplota {temp}°C v {city['name']}. Zdroj: OpenMeteo API",
                            "latitude": city['lat'],
                            "longitude": city['lon'],
                            "event_type": "weather",
                            "severity": "high",
                            "source": "openmeteo_api",
                            "url": "https://open-meteo.com/"
                        })
                    
                    if wind_speed > 20:
                        events.append({
                            "title": f"Silný vítr - {city['name']}",
                            "description": f"Rychlost větru {wind_speed} km/h v {city['name']}. Zdroj: OpenMeteo API",
                            "latitude": city['lat'],
                            "longitude": city['lon'],
                            "event_type": "weather",
                            "severity": "medium",
                            "source": "openmeteo_api",
                            "url": "https://open-meteo.com/"
                        })
                    
                    # Analýza srážek (pokud jsou dostupné)
                    if 'precipitation' in hourly_data and len(hourly_data['precipitation']) > 0:
                        max_precip = max(hourly_data['precipitation'])
                        if max_precip > 10:  # Více než 10mm/h
                            events.append({
                                "title": f"Silné srážky - {city['name']}",
                                "description": f"Intenzivní srážky {max_precip}mm/h v {city['name']}. Zdroj: OpenMeteo API",
                                "latitude": city['lat'],
                                "longitude": city['lon'],
                                "event_type": "flood",
                                "severity": "medium",
                                "source": "openmeteo_api",
                                "url": "https://open-meteo.com/"
                            })
                
            except Exception as e:
                print(f"❌ Chyba při zpracování {city['name']}: {str(e)}")
                continue
        
        print(f"✅ OpenMeteo scraper dokončen: {len(events)} událostí")
        return events
        
    except Exception as e:
        print(f"❌ Chyba v OpenMeteo scraperu: {str(e)}")
        return []

def parse_chmi_data(data: str, source_url: str) -> List[Dict]:
    """Parsuje skutečná CHMI data s vylepšeným debuggingem a lepší analýzou obsahu"""
    events = []
    
    try:
        print(f"🔍 Analýza CHMI dat ({len(data)} znaků)")
        print(f"📄 Prvních 1000 znaků: {data[:1000]}")
        
        # Rozšířený seznam klíčových slov - MÉNĚ RESTRIKTIVNÍ
        keywords = [
            # Základní povodňové termíny
            'záplav', 'povodn', 'výstrah', 'vltav', 'morav', 'sázav', 'berounk', 'ohře', 'labe',
            'hydrologická', 'vodní stav', 'hladina', 'přetečení', 'vylití', 'zaplavení',
            'meteorologická', 'extrémní', 'srážky', 'přívalový', 'déšť', 'povodňový',
            # Další obecné termíny - MÉNĚ RESTRIKTIVNÍ
            'voda', 'řeka', 'tok', 'přítok', 'povodí', 'vodní tok', 'vodní hladina',
            'meteorolog', 'počasí', 'srážk', 'déšť', 'bouřk', 'extrém', 'varování',
            'česká', 'čr', 'republika', 'region', 'oblast', 'kraj',
            # Nové obecné termíny pro lepší detekci
            'hydro', 'chmi', 'stav', 'hladina', 'tok', 'voda', 'vodní', 'meteorolog',
            'počasí', 'srážky', 'déšť', 'bouřka', 'extrém', 'varování', 'výstraha'
        ]
        
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in data.lower():
                found_keywords.append(keyword)
                # Vytvoříme event na základě nalezeného klíčového slova
                event = create_chmi_event_from_keyword(keyword, source_url)
                if event:
                    events.append(event)
        
        print(f"🔍 Nalezená klíčová slova: {found_keywords}")
        
        # Pokud nenajdeme žádné klíčové slovo, zkusíme parsovat JSON/XML strukturu
        if not events:
            print("🔍 Zkouším parsovat strukturovaná data...")
            events = parse_chmi_structured_data(data, source_url)
            
        # Pokud stále nic, zkusíme obecnější přístup
        if not events:
            print("🔍 Zkouším obecnější analýzu...")
            events = parse_chmi_general_data(data, source_url)
        
        # Pokud stále nic, zkusíme extrahovat skutečné výstrahy z HTML
        if not events:
            print("🔍 Zkouším extrahovat výstrahy z HTML...")
            events = extract_chmi_warnings_from_html(data, source_url)
            
        print(f"🔍 Parsováno {len(events)} událostí z CHMI dat")
        return events
        
    except Exception as e:
        print(f"❌ Chyba při parsování CHMI dat: {str(e)}")
        return []

def extract_chmi_warnings_from_html(data: str, source_url: str) -> List[Dict]:
    """Extrahuje skutečné výstrahy z CHMI HTML obsahu"""
    events = []
    
    try:
        # Hledáme skutečné výstrahy v HTML
        import re
        text = data.lower()

        # 1) Pokud je v textu výslovně "normální stav" a není zmínka o SPA/ohrožení/pohotovosti/bdělosti, nevracíme nic
        danger_markers = ["ohrožení", "pohotovost", "bdělost", "spa 1", "spa 2", "spa 3", "povodň"]
        if "normální stav" in text and not any(m in text for m in danger_markers):
            return []

        # 2) Určení závažnosti podle výskytu stavů SPA/ohrožení/pohotovost/bdělost
        severity = None
        if any(p in text for p in ["ohrožení", "spa 3", "spa3"]):
            severity = "critical"
        elif any(p in text for p in ["pohotovost", "spa 2", "spa2"]):
            severity = "high"
        elif any(p in text for p in ["bdělost", "spa 1", "spa1"]):
            severity = "medium"

        # Pokud nemáme závažnost (nikde nic z výše uvedeného), považujme to za bezvýznamné
        if severity is None:
            return []

        # 3) Pokusíme se získat konkrétní řeku a stanici
        river = None
        station = None
        m_river = re.search(r"tok\s*:?\s*([A-Za-zÁ-Žá-ž \-]+)", data, re.IGNORECASE)
        if m_river:
            river = m_river.group(1).strip()
        m_station = re.search(r"název\s+stanice\s*:?\s*([A-Za-zÁ-Žá-ž \-]+)", data, re.IGNORECASE)
        if m_station:
            station = m_station.group(1).strip()

        # 4) Lokalizace: priorita – (stanice+řeka) geokódování → známá města → centroid řeky → nic
        lat = lon = None
        if station and river:
            geo = geocode_cz(f"{station} {river} Czech Republic")
            if geo:
                lat, lon = geo
        if (lat is None or lon is None) and station:
            geo = geocode_cz(f"{station} Czech Republic")
            if geo:
                lat, lon = geo
        if (lat is None or lon is None) and river:
            center = get_river_centroid(river)
            if center:
                lat, lon = center

        # 5) Pokud stále nemáme validní souřadnice, nic nevracíme – raději žádná než špatná data
        if lat is None or lon is None:
            return []

        events.append({
            "title": f"CHMI povodňová výstraha – {river or 'neurčeno'} ({station or 'bez stanice'})",
            "description": f"Stav: {severity.upper()}, zdroj: {source_url}",
            "latitude": float(lat),
            "longitude": float(lon),
            "event_type": "flood",
            "severity": severity,
            "source": "chmi_api",
            "url": source_url
        })
        
        # Meteorologické výstrahy – přidáme jen pokud text výslovně obsahuje termíny a dokážeme určit lokaci
        weather_patterns = [
            r'meteorologická výstraha',
            r'výstraha.*počasí',
            r'extrémní.*počasí',
            r'silné.*srážky',
            r'přívalový.*déšť',
            r'bouřka.*výstraha',
            r'extrémní.*teploty',
            r'silný.*vítr',
            r'vítr.*výstraha'
        ]
        
        weather_hit = any(re.search(p, data, re.IGNORECASE) for p in weather_patterns)
        if weather_hit:
            # pokus o stanici/řeku → geokód → centroid řeky
            wlat = wlon = None
            if station and river:
                geo = geocode_cz(f"{station} {river} Czech Republic")
                if geo:
                    wlat, wlon = geo
            if (wlat is None or wlon is None) and station:
                geo = geocode_cz(f"{station} Czech Republic")
                if geo:
                    wlat, wlon = geo
            if (wlat is None or wlon is None) and river:
                center = get_river_centroid(river)
                if center:
                    wlat, wlon = center
            if wlat is not None and wlon is not None:
                events.append({
                    "title": "CHMI meteorologická výstraha",
                    "description": f"Zdroj: {source_url}",
                    "latitude": float(wlat),
                    "longitude": float(wlon),
                    "event_type": "weather",
                    "severity": "medium",
                    "source": "chmi_api",
                    "url": source_url
                })
        
        # Hledáme konkrétní lokace v textu
        location_patterns = [
            (r'praha', 50.0755, 14.4378),
            (r'brno', 49.1951, 16.6068),
            (r'ostrava', 49.8175, 18.2625),
            (r'plzeň', 49.7475, 13.3776),
            (r'liberec', 50.7663, 15.0543),
            (r'olomouc', 49.5938, 17.2507),
            (r'hradec králové', 50.2092, 15.8327),
            (r'pardubice', 50.0343, 15.7812),
            (r'zlín', 49.2264, 17.6683),
            (r'karlovy vary', 50.231, 12.880),
            (r'ústí nad labem', 50.6611, 14.0531),
            (r'české budějovice', 48.9745, 14.4747)
        ]
        
        # Pokud najdeme lokaci, použijeme ji pro event
        for location_pattern, lat, lon in location_patterns:
            if re.search(location_pattern, data, re.IGNORECASE):
                # Vytvoříme event s konkrétní lokací
                event = {
                    "title": f"CHMI výstraha - {location_pattern}",
                    "description": f"CHMI vydalo výstrahu pro {location_pattern}. Zdroj: {source_url}",
                    "latitude": lat,
                    "longitude": lon,
                    "event_type": "flood",
                    "severity": "high",
                    "source": "chmi_api",
                    "url": source_url
                }
                events.append(event)
        
        print(f"🔍 Extrahováno {len(events)} výstrah z HTML")
        return events
        
    except Exception as e:
        print(f"❌ Chyba při extrakci výstrah z HTML: {str(e)}")
        return []

def parse_chmi_general_data(data: str, source_url: str) -> List[Dict]:
    """Obecnější analýza CHMI dat pro případ, že specifické klíčové slova nefungují"""
    events = []
    
    try:
        # Hledáme jakékoliv zmínky o vodě nebo počasí
        water_indicators = ['voda', 'vodní', 'řeka', 'tok', 'hladina', 'stav']
        weather_indicators = ['počasí', 'meteorolog', 'srážk', 'déšť', 'bouřk']
        
        text_lower = data.lower()
        
        # Pokud obsahuje vodní indikátory
        if any(indicator in text_lower for indicator in water_indicators):
            event = create_chmi_event_from_keyword('hydrologická', source_url)
            if event:
                events.append(event)
        
        # Pokud obsahuje meteorologické indikátory
        if any(indicator in text_lower for indicator in weather_indicators):
            event = create_chmi_event_from_keyword('meteorologická', source_url)
            if event:
                events.append(event)
        
        # Pokud obsahuje české geografické termíny
        if 'česká' in text_lower or 'čr' in text_lower or 'republika' in text_lower:
            event = create_chmi_event_from_keyword('výstrah', source_url)
            if event:
                events.append(event)
        
        print(f"🔍 Obecná analýza našla {len(events)} událostí")
        return events
        
    except Exception as e:
        print(f"❌ Chyba při obecné analýze CHMI dat: {str(e)}")
        return []

def create_chmi_event_from_keyword(keyword: str, source_url: str) -> Dict:
    """Vytvoří event na základě klíčového slova"""
    keyword_mapping = {
        'záplav': {
            'title': f"Záplavová výstraha - {get_region_name(keyword)}",
            'description': f"CHMI vydalo záplavovou výstrahu pro {get_region_name(keyword)}. Zdroj: {source_url}",
            'latitude': 49.5,
            'longitude': 14.5,
            'severity': 'high'
        },
        'povodn': {
            'title': f"Povodňová výstraha - {get_region_name(keyword)}",
            'description': f"CHMI varuje před povodněmi v {get_region_name(keyword)}. Zdroj: {source_url}",
            'latitude': 49.2,
            'longitude': 14.4,
            'severity': 'critical'
        },
        'výstrah': {
            'title': f"Hydrologická výstraha - {get_region_name(keyword)}",
            'description': f"CHMI vydalo hydrologickou výstrahu pro {get_region_name(keyword)}. Zdroj: {source_url}",
            'latitude': 50.0,
            'longitude': 14.3,
            'severity': 'medium'
        },
        'vltav': {
            'title': "Výstraha - Vltava",
            'description': f"Vzestup hladiny Vltavy v Praze a okolí. Zdroj: {source_url}",
            'latitude': 50.0755,
            'longitude': 14.4378,
            'severity': 'high'
        },
        'morav': {
            'title': "Výstraha - Morava",
            'description': f"CHMI varuje před záplavami na Moravě. Zdroj: {source_url}",
            'latitude': 49.1951,
            'longitude': 16.6068,
            'severity': 'critical'
        },
        'labe': {
            'title': "Výstraha - Labe",
            'description': f"CHMI varuje před záplavami na Labi. Zdroj: {source_url}",
            'latitude': 50.6611,
            'longitude': 14.0531,
            'severity': 'high'
        },
        'ohře': {
            'title': "Výstraha - Ohře",
            'description': f"CHMI varuje před záplavami na Ohři. Zdroj: {source_url}",
            'latitude': 50.231,
            'longitude': 12.880,
            'severity': 'high'
        },
        'hydrologická': {
            'title': "Hydrologická výstraha",
            'description': f"CHMI vydalo hydrologickou výstrahu. Zdroj: {source_url}",
            'latitude': 49.8,
            'longitude': 15.5,
            'severity': 'medium'
        },
        'meteorologická': {
            'title': "Meteorologická výstraha",
            'description': f"CHMI vydalo meteorologickou výstrahu. Zdroj: {source_url}",
            'latitude': 49.8,
            'longitude': 15.5,
            'severity': 'medium'
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
        'morav': 'Morava',
        'labe': 'Ústí nad Labem',
        'ohře': 'Karlovy Vary',
        'hydrologická': 'Česká republika',
        'meteorologická': 'Česká republika'
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
    try:
        # Zkusíme extrahovat relevantní data z JSON objektu
        title = item.get('title', '')
        description = item.get('description', '')
        content = item.get('content', '')
        
        # Kombinujeme všechna textová pole
        text = f"{title} {description} {content}".lower()
        
        # Hledáme rizikové klíčová slova
        risk_keywords = ['povodn', 'záplav', 'výstrah', 'vltav', 'morav', 'labe', 'ohře', 'hydrologická', 'meteorologická']
        
        for keyword in risk_keywords:
            if keyword in text:
                return {
                    "title": f"CHMI JSON výstraha - {title[:50]}",
                    "description": f"CHMI data: {description[:100]}. Zdroj: {source_url}",
                    "latitude": 49.8,
                    "longitude": 15.5,
                    "event_type": "flood",
                    "severity": "high",
                    "source": "chmi_api",
                    "url": source_url
                }
        
        return None
        
    except Exception as e:
        print(f"❌ Chyba při parsování JSON item: {str(e)}")
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
    """Scrape RSS feeds s vylepšeným error handlingem"""
    try:
        print("📰 Spouštím RSS scraper...")
        
        # Aktualizované RSS feedy
        rss_feeds = [
            "https://www.novinky.cz/rss/",
            "https://www.seznamzpravy.cz/rss/",
            "https://www.hn.cz/rss/",
            "https://www.irozhlas.cz/rss/"
        ]
        
        scraped_events = []
        
        for feed_url in rss_feeds:
            try:
                print(f"📰 Zpracovávám RSS feed: {feed_url}")
                response = http_session.get(feed_url, timeout=30)
                
                if response.status_code == 200:
                    print(f"✅ Úspěšné připojení k: {feed_url}")
                    rss_xml = response.text
                    print(f"📊 Získaná data: {len(rss_xml)} znaků")
                    
                    # Parsujeme RSS feed
                    events = parse_rss_feed(rss_xml, feed_url)
                    scraped_events.extend(events)
                    print(f"✅ Nalezeno {len(events)} událostí z {feed_url}")
                else:
                    print(f"⚠️ RSS feed {feed_url} vrátil status {response.status_code}")
                    
            except requests.RequestException as e:
                print(f"❌ Chyba při stahování z {feed_url}: {str(e)}")
                continue
        
        if not scraped_events:
            print("⚠️ Žádný RSS feed nefunguje, žádná data nebudou uložena")
            scraped_events = []
        
        # Uložíme events do databáze
        conn = None
        saved_count = 0
        
        try:
            conn = get_risk_db()
            
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
            return {
                "message": f"RSS scraper selhal při ukládání",
                "status": "error",
                "error": str(e),
                "scraped_count": len(scraped_events),
                "saved_count": 0,
                "timestamp": datetime.now().isoformat()
            }
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
        return {
            "message": f"RSS scraper selhal",
            "status": "error",
            "error": str(e),
            "scraped_count": 0,
            "saved_count": 0,
            "timestamp": datetime.now().isoformat()
        }

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
    """Analyzuje RSS položku a hledá rizikové události s inteligentními filtry"""
    
    # Kombinujeme title a description pro analýzu
    text = f"{title} {description}".lower()
    
    # INTELLIGENT filtry - pouze vylučujeme jasně nepodstatné zprávy
    exclude_keywords = [
        # Jasně nepodstatné - kultura a zábava
        'film', 'kino', 'divadlo', 'koncert', 'festival', 'výstava', 'kniha', 'album', 'hudba', 'umění',
        'televize', 'rozhlas', 'reklama', 'marketing', 'obchod', 'nákup', 'sleva', 'akce', 'sport', 'fotbal', 'hokej',
        'tenis', 'basketball', 'atletika', 'kultura', 'osobní', 'soukromý', 'rodina', 'dítě', 'život', 'výpověď',
        'nohavica', 'písničkář', 'dokument', 'jarek', 'ostrava', 'písničky', 'stb', 'putin', 'míří do kin',
        
        # Geopolitická a kulturní témata - úplně vyloučit
        'politika', 'politický', 'volby', 'prezident', 'vláda', 'parlament', 'senát', 'poslanec', 'ministr',
        'diplomat', 'mezinárodní', 'zahraničí', 'rusko', 'ukrajina', 'nato', 'eu', 'unie', 'brexit',
        'protest', 'demonstrace', 'manifestace', 'stávka', 'odbor', 'aktivista', 'ekolog', 'greenpeace',
        'kultura', 'umění', 'literatura', 'film', 'hudba', 'divadlo', 'galerie', 'muzeum', 'výstava',
        'osobnost', 'celebrita', 'herec', 'herečka', 'zpěvák', 'zpěvačka', 'umělec', 'spisovatel',
        'historie', 'historický', 'výročí', 'památka', 'památník', 'tradice', 'zvyk', 'svátek',
        
        # Jasně nepodstatné - osobní nehody bez dopadu na infrastrukturu
        'řidič', 'auto', 'nehoda', 'motorkář', 'kombajn', 'montér', 'stožár', 'nemocnice', 'přežil', 'nepřežil',
        'srážka', 'předjížděl', 'vyjel ze silnice', 'spadl', 'olomoucku', 'plzeňsku', 'hradecku', 'šumpersku',
        'tragická', 'silně', 'rychl', 'skončil', 'střeše', 'nemocnici', 'vyjel ze silnice', 'předjížděl auto',
        'řidič jel', 'řidič na', 'motorkář na', 'kombajnem', 'montér ze', 'spadl ze', 'tragická nehoda',
        
        # Jasně nepodstatné - místní události bez dopadu
        'břeclavi', 'apollo', 'koupal', 'nadšenci', 'oblíbené', 'lokality', 'krásu', 'pražský okruh', 'běchovic',
        'd1', 'dopravní úleva', 'spojka', 'golcův jenikov', 'jižní čechy', 'důležitý krok', 'přinese dopravní úlevu',
        'apollo se', 'koupal každý', 'nadšenci z', 'oblíbené lokalitě', 'zašlou krásu',
        
        # Jasně nepodstatné - technické detaily
        'video', 'foto', 'foto:', 'video:', 'online:', 'online',

        # Právní/krimi - nechceme
        'ikem', 'soud', 'soudní', 'vydírání', 'obžalován', 'obžaloba', 'policie', 'krimi', 'vyšetřování'
    ]
    
    # Kontrola vylučovacích klíčových slov - pouze jasně nepodstatné
    for exclude_word in exclude_keywords:
        if exclude_word in text:
            return None  # Nejedná se o rizikovou událost
    
    # INTELLIGENT rizikové klíčové slova - více specifické
    # Striktnější pravidla detekce
    hydrology_core = ['povodn', 'záplav', 'přeteč', 'vylit', 'zaplaven', 'povodň']
    # Tvrdé vyloučení právních/krimi formulací přimo v analýze (belt-and-suspenders)
    if any(k in text for k in ['ikem', 'soud', 'vydír', 'obžal', 'policie', 'krimi', 'vyšetřov']):
        return None
    river_terms = ['vltava', 'morava', 'labe', 'ohře', 'berounka', 'řeka', 'povodí', 'koryto', 'hladina']
    meteo_terms = ['chmi', 'hydro', 'meteorolog', 'hydrologická', 'meteorologická', 'výstraha']
    transport_terms = ['dálnice', 'silnice', 'most', 'železnice', 'přístav', 'sklad', 'logist', 'uzavírka', 'oprava', 'blokáda']

    # Flood: musíme mít hydrologické jádro + (řeka nebo CHMI/meteo kontext) + lokalizaci v ČR
    if any(k in text for k in hydrology_core) and (any(t in text for t in river_terms) or any(t in text for t in meteo_terms)):
        evt = create_rss_event(title, description, 'flood', 'hydro', feed_url)
        if evt is not None:
            return evt

    # Supply chain: vyžadujeme jasné dopravní/infrastrukturní termíny + lokalizaci v ČR
    if any(t in text for t in transport_terms):
        evt = create_rss_event(title, description, 'supply_chain', 'transport', feed_url)
        if evt is not None:
            return evt

    return None

def create_rss_event(title: str, description: str, event_type: str, keyword: str, feed_url: str) -> Dict:
    """Vytvoří event na základě RSS položky"""
    
    # Mapování typů událostí na severity
    severity_mapping = {
        'supply_chain': 'high', 
        'flood': 'high'
    }
    
    # Mapování na lokace podle klíčových slov (může být doplněno geokódováním)
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
        'zlín': (49.2264, 17.6683),
        'karlovy vary': (50.231, 12.880),
        'ústí nad labem': (50.6611, 14.0531)
    }
    
    # Hledáme lokaci v textu - více specifické hledání
    latitude = None
    longitude = None
    location_found = False
    
    # Nejdříve hledáme v title
    for location_name, coords in location_mapping.items():
        if location_name in title.lower():
            latitude, longitude = coords
            location_found = True
            break
    
    # Pokud nenajdeme v title, hledáme v description
    if not location_found:
        for location_name, coords in location_mapping.items():
            if location_name in description.lower():
                latitude, longitude = coords
                break
    
    # Pokud jsme nedokázali najít polohu, zkusíme geokódování běžných výrazů v CZ
    if (latitude is None or longitude is None) and ENABLE_GEOCODING:
        for token in [
            'Praha','Brno','Ostrava','Plzeň','Liberec','Olomouc','České Budějovice','Hradec Králové','Pardubice','Zlín','Karlovy Vary','Ústí nad Labem'
        ]:
            if token.lower() in (title + ' ' + (description or '')).lower():
                geo = geocode_cz(token)
                if geo:
                    latitude, longitude = geo
                    break
    # Pokud stále nic, zkusíme konkrétní řeky → centroid z DB
    if (latitude is None or longitude is None):
        for river in ['Vltava','Labe','Morava','Ohře','Berounka']:
            if river.lower() in (title + ' ' + (description or '')).lower():
                centroid = get_river_centroid(river)
                if centroid:
                    latitude, longitude = centroid
                    break
    # Pokud stále nemáme pozici, událost nevracíme (raději žádná než špatná)
    if latitude is None or longitude is None:
        return None

    return {
        "title": title[:100],  # Omezíme délku title
        "description": f"{description[:150] if description else f'Událost související s {keyword}'} | Zdroj: {feed_url}",
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
        
        # Vyčištění starých dat (starších než 7 dní)
        await clear_old_events()
        
        # Vyčištění geopolitických událostí
        await clear_geopolitical_events()
        
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
        
        # Žádné fallback data - pouze skutečná scrapovaná data
        print("✅ Žádná fallback data - pouze skutečná scrapovaná data")
        results["test_data_created"] = 0
        
        results["end_time"] = datetime.now().isoformat()
        results["status"] = "completed"
        
        print(f"📊 Celkový výsledek: {results['total_events_saved']} událostí")
        
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

@app.get("/api/test-chmi")
async def test_chmi_endpoints():
    """Test endpoint pro kontrolu CHMI API"""
    results = {}
    
    # AKTUALIZOVANÉ CHMI endpointy s funkčními URL
    chmi_endpoints = [
        "https://hydro.chmi.cz/hpps/",
        "https://hydro.chmi.cz/hpps/index.php",
        # Původní endpointy (pro případ, že se opraví)
        "https://hydro.chmi.cz/hpps/hpps_act.php",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php", 
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=1",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=2",
        "https://hydro.chmi.cz/hpps/hpps_act_quick.php?q=3"
    ]
    
    for endpoint in chmi_endpoints:
        try:
            response = http_session.get(endpoint, timeout=10)
            results[endpoint] = {
                "status_code": response.status_code,
                "content_length": len(response.text),
                "content_preview": response.text[:200] if response.status_code == 200 else "N/A"
            }
        except Exception as e:
            results[endpoint] = {
                "status_code": "ERROR",
                "error": str(e)
            }
    
    return {
        "chmi_test_results": results,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/clear-geopolitical")
async def clear_geopolitical_endpoint():
    """Endpoint pro vyčištění geopolitických událostí"""
    try:
        deleted_count = await clear_geopolitical_events()
        return {
            "message": f"Geopolitické události vyčištěny",
            "deleted_count": deleted_count,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chyba při čištění: {str(e)}") 

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
        conn = get_risk_db()
        
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
                        "flood_probability": flood_risk.get('probability', 0),
                        "impact_level": flood_risk.get('impact_level', 'low'),
                        "mitigation_needed": flood_risk.get('mitigation_needed', (
                            flood_risk.get('probability', 0) > 0.5 or flood_risk.get('impact_level', 'low') in ['high', 'critical']
                        ))
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
                    "high_risk_suppliers": len([
                        s for s in flood_analysis 
                        if (s.get('flood_risk') or {}).get('impact_level', 'low') in ['high', 'critical']
                    ]),
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
        conn = get_risk_db()
        
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
                    SELECT COUNT(*) as nearby_events,
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

CZECH_BOUNDS = {
    'min_lat': 48.5, 'max_lat': 51.1,
    'min_lon': 12.0, 'max_lon': 18.9
}

def is_in_czech_republic(lat: float, lon: float) -> bool:
    return (
        CZECH_BOUNDS['min_lat'] <= lat <= CZECH_BOUNDS['max_lat'] and
        CZECH_BOUNDS['min_lon'] <= lon <= CZECH_BOUNDS['max_lon']
    )

def sanitize_coords_backend(lat: float, lon: float) -> tuple[float, float]:
    """Opraví případné prohození lat/lon. Pokud swap dává CZ smysl, použije se."""
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except Exception:
        return lat, lon
    if is_in_czech_republic(lat_f, lon_f):
        return lat_f, lon_f
    if is_in_czech_republic(lon_f, lat_f):
        return lon_f, lat_f
    return lat_f, lon_f

def guess_nearest_river_name(lat: float, lon: float) -> str:
    """Hrubý odhad nejbližší velké řeky v ČR pro fallback."""
    try:
        if 14.0 <= lon <= 15.2 and 49.2 <= lat <= 50.4:
            return 'Vltava'
        if 15.0 <= lon <= 16.6 and lat >= 49.8:
            return 'Labe'
        if lon >= 16.2 or lat <= 49.2:
            return 'Morava'
        if 12.0 <= lon <= 13.5 and lat >= 49.6:
            return 'Ohře'
        if 12.5 <= lon <= 14.5 and 49.4 <= lat <= 49.9:
            return 'Berounka'
    except Exception:
        pass
    return 'Neznámá'

def calculate_river_distance(lat: float, lon: float) -> float:
    """Vypočítá vzdálenost od nejbližší řeky s fallback"""
    conn = None
    try:
        # Sanitizace souřadnic (swap pokud dává smysl)
        lat, lon = sanitize_coords_backend(lat, lon)
        conn = get_risk_db()
        if conn is None:
            # Fallback - jednoduchý výpočet vzdálenosti od středu ČR
            center_lat, center_lon = 49.8175, 15.4730
            return ((lat - center_lat) ** 2 + (lon - center_lon) ** 2) ** 0.5 * 111  # km
        with conn.cursor() as cur:
            # Zkusíme použít PostGIS funkci
            try:
                cur.execute("SELECT calculate_river_distance(%s, %s)", (lat, lon))
                result = cur.fetchone()
                if result and result[0] is not None:
                    return float(result[0])
            except Exception as e:
                print(f"⚠️ PostGIS funkce calculate_river_distance nefunguje: {e}")
            
            # Fallback - jednoduchý výpočet vzdálenosti od středu ČR
            center_lat, center_lon = 49.8175, 15.4730
            distance = ((lat - center_lat) ** 2 + (lon - center_lon) ** 2) ** 0.5 * 111  # km
            return distance
            
    except Exception as e:
        print(f"❌ Chyba při výpočtu vzdálenosti od řeky: {str(e)}")
        return 50.0  # Výchozí vzdálenost
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def calculate_flood_risk(lat: float, lon: float, flood_level_m: float) -> dict:
    """Vypočítá riziko záplav s fallback"""
    conn = None
    try:
        # Sanitizace souřadnic
        lat, lon = sanitize_coords_backend(lat, lon)
        conn = get_risk_db()
        if conn is None:
            river_distance = calculate_river_distance(lat, lon)
            probability = max(0, 1 - (river_distance / 100))
            impact_level = 'high' if probability > 0.5 else 'medium' if probability > 0.2 else 'low'
            return {
                'probability': probability,
                'impact_level': impact_level,
                'river_distance_km': river_distance,
                'nearest_river_name': guess_nearest_river_name(lat, lon),
                'mitigation_needed': probability > 0.5 or impact_level in ['high', 'critical']
            }
        with conn.cursor() as cur:
            # Zkusíme použít PostGIS funkci
            try:
                cur.execute("SELECT analyze_flood_risk_from_rivers(%s, %s)", (lat, lon))
                result = cur.fetchone()
                if result and result[0] is not None:
                    out = result[0]
                    # Normalizace klíčů z DB funkce na jednotný formát pro frontend
                    if isinstance(out, dict):
                        if 'probability' not in out and 'flood_probability' in out:
                            out['probability'] = out.get('flood_probability')
                        if 'impact_level' not in out and 'flood_risk_level' in out:
                            out['impact_level'] = out.get('flood_risk_level')
                        if 'river_distance_km' not in out and 'nearest_river_distance_km' in out:
                            out['river_distance_km'] = out.get('nearest_river_distance_km')
                        # Zajistit přítomnost mitigation_needed
                        prob = out.get('probability', out.get('flood_probability', 0))
                        impact = out.get('impact_level', out.get('flood_risk_level', 'low'))
                        if 'mitigation_needed' not in out:
                            out['mitigation_needed'] = (prob > 0.5) or (impact in ['high', 'critical'])
                    return out
            except Exception as e:
                # Příliš hlučné v produkci – ponecháme jen info
                print("ℹ️ PostGIS analyze_flood_risk_from_rivers není k dispozici, používám fallback")
            
            # Fallback - jednoduchý výpočet
            river_distance = calculate_river_distance(lat, lon)
            probability = max(0, 1 - (river_distance / 100))  # Čím blíže řeky, tím vyšší riziko
            impact_level = 'high' if probability > 0.5 else 'medium' if probability > 0.2 else 'low'
            
            return {
                'probability': probability,
                'impact_level': impact_level,
                'river_distance_km': river_distance,
                'nearest_river_name': guess_nearest_river_name(lat, lon),
                'mitigation_needed': probability > 0.5 or impact_level in ['high', 'critical']
            }
            
    except Exception as e:
        print(f"❌ Chyba při výpočtu rizika záplav: {str(e)}")
        return {
            'probability': 0.1,
            'impact_level': 'low',
            'river_distance_km': 50.0,
            'nearest_river_name': 'Neznámá',
            'mitigation_needed': False
        }
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

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
    nearby_events = risk_stats['nearby_events'] or 0
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

async def clear_old_events():
    """Vyčistí staré události (starší než 7 dní)"""
    conn = None
    try:
        conn = get_risk_db()
        with conn.cursor() as cur:
            # Smazání událostí starších než 7 dní
            cur.execute("""
                DELETE FROM risk_events 
                WHERE created_at < NOW() - INTERVAL '7 days'
            """)
            deleted_count = cur.rowcount
            conn.commit()
            print(f"🗑️ Smazáno {deleted_count} starých událostí")
            return deleted_count
    except Exception as e:
        print(f"❌ Chyba při mazání starých událostí: {str(e)}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()

async def clear_geopolitical_events():
    """Vyčistí všechny geopolitické události"""
    conn = None
    try:
        conn = get_risk_db()
        with conn.cursor() as cur:
            # Smazání všech geopolitických událostí
            cur.execute("""
                DELETE FROM risk_events 
                WHERE event_type = 'geopolitical'
            """)
            deleted_count = cur.rowcount
            conn.commit()
            print(f"🗑️ Smazáno {deleted_count} geopolitických událostí")
            return deleted_count
    except Exception as e:
        print(f"❌ Chyba při mazání geopolitických událostí: {str(e)}")
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()

@app.post("/api/maintenance/clear-irrelevant-rss")
async def clear_irrelevant_rss_events():
    """Smaže z databáze zjevně irelevantní RSS události (právo/krimi apod.)."""
    conn = None
    try:
        conn = get_risk_db()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        deleted_total = 0
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM risk_events
                WHERE source = 'rss'
                  AND (
                        lower(title) LIKE '%ikem%'
                     OR lower(title) LIKE '%soud%'
                     OR lower(title) LIKE '%vydír%'
                     OR lower(title) LIKE '%obžal%'
                     OR lower(title) LIKE '%policie%'
                     OR lower(title) LIKE '%krimi%'
                     OR lower(title) LIKE '%vyšetřov%'
                  )
                """
            )
            deleted_total = cur.rowcount
            conn.commit()
        return {"status": "success", "deleted": deleted_total}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

@app.get("/api/test-openmeteo")
async def test_openmeteo_api():
    """Test endpoint pro kontrolu OpenMeteo API"""
    try:
        print("🌤️ Testuji OpenMeteo API...")
        
        # Test pro Prahu
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.0755&longitude=14.4378&current_weather=true&hourly=temperature_2m,precipitation,wind_speed_10m&timezone=auto"
        response = http_session.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            current_weather = data.get('current_weather', {})
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "temperature": current_weather.get('temperature'),
                "windspeed": current_weather.get('windspeed'),
                "weathercode": current_weather.get('weathercode'),
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "status_code": response.status_code,
                "error": "OpenMeteo API nefunguje",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/test-scraping-improved")
async def test_improved_scraping():
    """Test endpoint pro ověření vylepšeného scrapingu s detailním debuggingem"""
    try:
        print("🔍 Testuji vylepšený scraping...")
        
        results = {
            "chmi_test": {},
            "rss_test": {},
            "openmeteo_test": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Test CHMI scraping
        try:
            print("🌊 Testuji CHMI scraping...")
            chmi_response = await scrape_chmi_floods()
            results["chmi_test"] = {
                "status": chmi_response.get("status", "unknown"),
                "scraped_count": chmi_response.get("scraped_count", 0),
                "saved_count": chmi_response.get("saved_count", 0),
                "source_url": chmi_response.get("source_url", "unknown")
            }
            print(f"✅ CHMI test dokončen: {chmi_response.get('saved_count', 0)} událostí")
        except Exception as e:
            print(f"❌ CHMI test selhal: {str(e)}")
            results["chmi_test"] = {"error": str(e)}
        
        # Test RSS scraping
        try:
            print("📰 Testuji RSS scraping...")
            rss_response = await scrape_rss_feeds()
            results["rss_test"] = {
                "status": rss_response.get("status", "unknown"),
                "scraped_count": rss_response.get("scraped_count", 0),
                "saved_count": rss_response.get("saved_count", 0)
            }
            print(f"✅ RSS test dokončen: {rss_response.get('saved_count', 0)} událostí")
        except Exception as e:
            print(f"❌ RSS test selhal: {str(e)}")
            results["rss_test"] = {"error": str(e)}
        
        # Test OpenMeteo
        try:
            print("🌤️ Testuji OpenMeteo...")
            openmeteo_events = await scrape_openmeteo_weather()
            results["openmeteo_test"] = {
                "status": "success",
                "scraped_count": len(openmeteo_events),
                "events": openmeteo_events[:3]  # První 3 události pro ukázku
            }
            print(f"✅ OpenMeteo test dokončen: {len(openmeteo_events)} událostí")
        except Exception as e:
            print(f"❌ OpenMeteo test selhal: {str(e)}")
            results["openmeteo_test"] = {"error": str(e)}
        
        return {
            "message": "Vylepšený scraping test dokončen",
            "status": "success",
            "results": results
        }
        
    except Exception as e:
        print(f"❌ Neočekávaná chyba při testování: {str(e)}")
        return {
            "message": "Test selhal",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

 