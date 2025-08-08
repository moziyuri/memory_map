"""
Proper error handling middleware for the Risk Analyst application
Replaces generic exception handling with structured error responses
"""

import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import psycopg2
from logging_config import log_error, log_warning
from datetime import datetime

class RiskAnalystException(Exception):
    """Base exception for Risk Analyst application"""
    def __init__(self, message: str, error_code: str = "UNKNOWN_ERROR", status_code: int = 500):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.message)

class DatabaseConnectionError(RiskAnalystException):
    """Database connection error"""
    def __init__(self, message: str = "Database connection failed"):
        super().__init__(message, "DATABASE_CONNECTION_ERROR", 503)

class ValidationError(RiskAnalystException):
    """Data validation error"""
    def __init__(self, message: str = "Data validation failed"):
        super().__init__(message, "VALIDATION_ERROR", 400)

class ScrapingError(RiskAnalystException):
    """Web scraping error"""
    def __init__(self, message: str = "Scraping operation failed"):
        super().__init__(message, "SCRAPING_ERROR", 502)

class ExternalAPIError(RiskAnalystException):
    """External API error"""
    def __init__(self, message: str = "External API request failed"):
        super().__init__(message, "EXTERNAL_API_ERROR", 502)

def create_error_response(
    message: str,
    error_code: str,
    status_code: int = 500,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create standardized error response
    
    Args:
        message: Human-readable error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        details: Optional additional error details
    
    Returns:
        JSONResponse with error details
    """
    error_response = {
        "error": {
            "message": message,
            "code": error_code,
            "status_code": status_code,
            "timestamp": datetime.now().isoformat()
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

def handle_database_error(error: Exception, operation: str) -> JSONResponse:
    """Handle database-related errors"""
    if isinstance(error, psycopg2.OperationalError):
        log_error(f"Database operational error during {operation}", error=error)
        return create_error_response(
            "Database connection failed",
            "DATABASE_OPERATIONAL_ERROR",
            503
        )
    elif isinstance(error, psycopg2.IntegrityError):
        log_error(f"Database integrity error during {operation}", error=error)
        return create_error_response(
            "Data integrity constraint violated",
            "DATABASE_INTEGRITY_ERROR",
            400
        )
    else:
        log_error(f"Unknown database error during {operation}", error=error)
        return create_error_response(
            "Database operation failed",
            "DATABASE_ERROR",
            500
        )

def handle_validation_error(error: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    log_warning("Data validation failed", errors=str(error.errors()))
    return create_error_response(
        "Invalid data provided",
        "VALIDATION_ERROR",
        400,
        {"validation_errors": error.errors()}
    )

def handle_scraping_error(error: Exception, source: str) -> JSONResponse:
    """Handle web scraping errors"""
    log_error(f"Scraping failed for {source}", error=error)
    return create_error_response(
        f"Failed to scrape data from {source}",
        "SCRAPING_ERROR",
        502,
        {"source": source, "error": str(error)}
    )

def handle_external_api_error(error: Exception, api_name: str) -> JSONResponse:
    """Handle external API errors"""
    log_error(f"External API error for {api_name}", error=error)
    return create_error_response(
        f"External API {api_name} is unavailable",
        "EXTERNAL_API_ERROR",
        502,
        {"api": api_name, "error": str(error)}
    )

async def error_handling_middleware(request: Request, call_next):
    """
    Global error handling middleware
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint function
    
    Returns:
        Response or error response
    """
    try:
        response = await call_next(request)
        return response
    except RiskAnalystException as e:
        log_error(f"Application error: {e.message}", error=e)
        return create_error_response(e.message, e.error_code, e.status_code)
    except ValidationError as e:
        return handle_validation_error(e)
    except psycopg2.Error as e:
        return handle_database_error(e, f"{request.method} {request.url.path}")
    except Exception as e:
        log_error(f"Unexpected error: {str(e)}", error=e)
        return create_error_response(
            "Internal server error",
            "INTERNAL_ERROR",
            500,
            {"traceback": traceback.format_exc()}
        )

# Input validation helpers
def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Validate geographic coordinates"""
    if not (-90 <= latitude <= 90):
        raise ValidationError("Latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise ValidationError("Longitude must be between -180 and 180")
    return True

def validate_czech_republic_coordinates(latitude: float, longitude: float) -> bool:
    """Validate coordinates are within Czech Republic bounds"""
    # Czech Republic approximate bounds
    if not (48.5 <= latitude <= 51.1):
        raise ValidationError("Latitude must be within Czech Republic bounds (48.5-51.1)")
    if not (12.0 <= longitude <= 18.9):
        raise ValidationError("Longitude must be within Czech Republic bounds (12.0-18.9)")
    return True

def validate_severity_level(severity: str) -> bool:
    """Validate risk severity level"""
    valid_levels = ["low", "medium", "high", "critical"]
    if severity.lower() not in valid_levels:
        raise ValidationError(f"Severity must be one of: {', '.join(valid_levels)}")
    return True

def validate_event_type(event_type: str) -> bool:
    """Validate event type"""
    valid_types = ["flood", "supply_chain", "weather", "geopolitical"]
    if event_type.lower() not in valid_types:
        raise ValidationError(f"Event type must be one of: {', '.join(valid_types)}")
    return True 