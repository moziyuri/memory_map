"""
Proper logging configuration for the Risk Analyst application
Replaces print statements with structured logging
"""

import logging
import sys
from datetime import datetime
from typing import Optional

# Configure logging
def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """
    Setup structured logging for the application
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for logging
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger("risk_analyst")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create default logger
logger = setup_logging()

# Convenience functions for different log levels
def log_info(message: str, **kwargs):
    """Log info message with optional context"""
    context = f" | {kwargs}" if kwargs else ""
    logger.info(f"{message}{context}")

def log_warning(message: str, **kwargs):
    """Log warning message with optional context"""
    context = f" | {kwargs}" if kwargs else ""
    logger.warning(f"⚠️ {message}{context}")

def log_error(message: str, error: Optional[Exception] = None, **kwargs):
    """Log error message with optional exception and context"""
    context = f" | {kwargs}" if kwargs else ""
    error_info = f" | Error: {str(error)}" if error else ""
    logger.error(f"❌ {message}{error_info}{context}")

def log_success(message: str, **kwargs):
    """Log success message with optional context"""
    context = f" | {kwargs}" if kwargs else ""
    logger.info(f"✅ {message}{context}")

def log_debug(message: str, **kwargs):
    """Log debug message with optional context"""
    context = f" | {kwargs}" if kwargs else ""
    logger.debug(f"🔍 {message}{context}")

# Database logging
def log_db_connection(host: str, database: str, success: bool, error: Optional[str] = None):
    """Log database connection attempts"""
    if success:
        log_success(f"Database connection successful", host=host, database=database)
    else:
        log_error(f"Database connection failed", host=host, database=database, error=error)

# API logging
def log_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Log API request details"""
    level = "INFO" if status_code < 400 else "WARNING" if status_code < 500 else "ERROR"
    getattr(logger, level.lower())(f"API {method} {endpoint} - {status_code} ({duration:.2f}s)")

# Scraping logging
def log_scraping_result(source: str, events_found: int, success: bool, error: Optional[str] = None):
    """Log scraping operation results"""
    if success:
        log_success(f"Scraping completed", source=source, events_found=events_found)
    else:
        log_error(f"Scraping failed", source=source, error=error) 