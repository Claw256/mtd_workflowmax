"""Logging configuration for WorkflowMax API client."""

import os
import sys
import logging
import logging.handlers
from datetime import datetime
from typing import Optional
from pathlib import Path

class CustomFormatter(logging.Formatter):
    """Custom formatter with color support for console output."""
    
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }
    
    def format(self, record):
        """Format the log record with appropriate color."""
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

class LogManager:
    """Manages logging configuration and setup."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one log manager exists."""
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logging if not already initialized."""
        if not self._initialized:
            self._setup_logging()
            self._initialized = True
    
    def _setup_logging(self):
        """Set up logging configuration."""
        # Create logs directory
        logs_dir = self._get_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up root logger
        root_logger = logging.getLogger('workflowmax')
        root_logger.setLevel(logging.DEBUG)
        
        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add handlers
        self._add_console_handler(root_logger)
        self._add_file_handlers(root_logger, logs_dir)
    
    def _get_logs_dir(self) -> Path:
        """Get the logs directory path.
        
        Returns:
            Path: Path to logs directory
        """
        # Get the module root directory (3 levels up from this file)
        module_root = Path(__file__).resolve().parent.parent.parent.parent
        return module_root / 'logs'
    
    def _add_console_handler(self, logger: logging.Logger):
        """Add console handler with color formatting.
        
        Args:
            logger: Logger to add handler to
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter())
        logger.addHandler(console_handler)
    
    def _add_file_handlers(self, logger: logging.Logger, logs_dir: Path):
        """Add file handlers for different log levels.
        
        Args:
            logger: Logger to add handlers to
            logs_dir: Directory for log files
        """
        # Detailed formatter for file output
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Main log file with rotation
        main_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'workflowmax.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(file_formatter)
        logger.addHandler(main_handler)
        
        # Error log file with rotation
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'error.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.
    
    Args:
        name: Name for the logger
        
    Returns:
        logging.Logger: Configured logger
        
    Example:
        >>> logger = get_logger('workflowmax.api')
        >>> logger.info('API request successful')
        >>> logger.error('API request failed', exc_info=True)
    """
    # Ensure LogManager is initialized
    LogManager()
    
    # Get and return logger
    logger = logging.getLogger(name)
    
    # Add context filter if not already present
    if not any(isinstance(f, ContextFilter) for f in logger.filters):
        logger.addFilter(ContextFilter())
    
    return logger

class ContextFilter(logging.Filter):
    """Filter that adds contextual information to log records."""
    
    def filter(self, record):
        """Add additional context to the log record.
        
        Args:
            record: Log record to modify
            
        Returns:
            bool: Always True (to include the record)
        """
        # Add timestamp in ISO format
        record.iso_timestamp = datetime.utcnow().isoformat()
        
        # Add process and thread IDs
        record.process_id = os.getpid()
        record.thread_name = threading.current_thread().name
        
        return True

# Initialize logging when module is imported
LogManager()
