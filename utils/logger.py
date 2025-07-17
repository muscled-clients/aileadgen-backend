"""
Comprehensive Logging System for Backend
Provides structured logging with different levels and contexts
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from contextvars import ContextVar
from pathlib import Path
import os

# Context variables for request tracking
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
user_id_context: ContextVar[str] = ContextVar('user_id', default='')

class StructuredFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record):
        # Base log structure
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add request context if available
        request_id = request_id_context.get()
        if request_id:
            log_entry['request_id'] = request_id
            
        user_id = user_id_context.get()
        if user_id:
            log_entry['user_id'] = user_id
        
        # Add extra fields from record
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Handle exceptions
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class APILogger:
    """Centralized logging for the API"""
    
    def __init__(self, name: str = 'ai_lead_gen'):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with appropriate handlers and formatters"""
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Set log level based on environment
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Console handler for development
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # File handler for all logs
        file_handler = logging.FileHandler(log_dir / 'app.log')
        file_handler.setLevel(logging.INFO)
        
        # Error file handler
        error_handler = logging.FileHandler(log_dir / 'errors.log')
        error_handler.setLevel(logging.ERROR)
        
        # Use structured formatter for production, simple for development
        if os.getenv('NODE_ENV') == 'production':
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Apply formatters
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(StructuredFormatter())
        error_handler.setFormatter(StructuredFormatter())
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
    
    def _log_with_context(self, level: int, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log with additional context data"""
        if extra_data:
            self.logger.log(level, message, extra={'extra_data': extra_data})
        else:
            self.logger.log(level, message)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log_with_context(logging.DEBUG, message, kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log_with_context(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log_with_context(logging.WARNING, message, kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message"""
        if error:
            self.logger.error(message, exc_info=True, extra={'extra_data': kwargs})
        else:
            self._log_with_context(logging.ERROR, message, kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message"""
        if error:
            self.logger.critical(message, exc_info=True, extra={'extra_data': kwargs})
        else:
            self._log_with_context(logging.CRITICAL, message, kwargs)

# Create singleton instance
logger = APILogger()

# Helper functions for common logging patterns
def log_api_request(method: str, path: str, status_code: int, duration: float, user_id: str = None):
    """Log API request with performance metrics"""
    logger.info(
        f"API Request: {method} {path}",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration * 1000,
        user_id=user_id
    )

def log_database_operation(operation: str, table: str, duration: float, affected_rows: int = None):
    """Log database operations"""
    logger.info(
        f"Database: {operation} on {table}",
        operation=operation,
        table=table,
        duration_ms=duration * 1000,
        affected_rows=affected_rows
    )

def log_validation_error(field: str, value: Any, error_message: str):
    """Log validation errors"""
    logger.warning(
        f"Validation error: {field}",
        field=field,
        value=str(value),
        error_message=error_message
    )

def log_business_event(event: str, entity_type: str, entity_id: str, details: Dict[str, Any] = None):
    """Log business events (lead created, call initiated, etc.)"""
    logger.info(
        f"Business event: {event}",
        event=event,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {}
    )

def log_security_event(event: str, details: Dict[str, Any] = None):
    """Log security-related events"""
    logger.warning(
        f"Security event: {event}",
        event=event,
        details=details or {}
    )

def log_performance_issue(operation: str, duration: float, threshold: float = 1.0):
    """Log performance issues when operations exceed threshold"""
    if duration > threshold:
        logger.warning(
            f"Performance issue: {operation} took {duration:.2f}s",
            operation=operation,
            duration=duration,
            threshold=threshold
        )

# Context managers for request tracking
class RequestContext:
    """Context manager for request tracking"""
    
    def __init__(self, request_id: str, user_id: str = None):
        self.request_id = request_id
        self.user_id = user_id
        self.request_token = None
        self.user_token = None
    
    def __enter__(self):
        self.request_token = request_id_context.set(self.request_id)
        if self.user_id:
            self.user_token = user_id_context.set(self.user_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        request_id_context.reset(self.request_token)
        if self.user_token:
            user_id_context.reset(self.user_token)

# Decorator for logging function calls
def log_function_call(func):
    """Decorator to log function calls with duration"""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        function_name = f"{func.__module__}.{func.__name__}"
        
        logger.debug(f"Function call started: {function_name}")
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.debug(
                f"Function call completed: {function_name}",
                duration=duration,
                success=True
            )
            
            return result
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.error(
                f"Function call failed: {function_name}",
                error=e,
                duration=duration,
                success=False
            )
            
            raise
    
    return wrapper

# Initialize logging
logger.info("Logger initialized", environment=os.getenv('NODE_ENV', 'development'))