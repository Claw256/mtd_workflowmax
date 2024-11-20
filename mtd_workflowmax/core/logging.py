"""Enhanced logging configuration for WorkflowMax API."""

import logging
import logging.handlers
import json
import uuid
import time
from datetime import datetime
import threading
import os
import sys
import ctypes
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Union
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracking
request_id: ContextVar[str] = ContextVar('request_id', default='')
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

def get_app_log_dir() -> Path:
    """Get application-specific log directory in system temp."""
    temp_dir = Path(tempfile.gettempdir())
    log_dir = temp_dir / 'mtd_workflowmax' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

def enable_virtual_terminal_processing():
    """Enable ANSI escape sequences in Windows terminals."""
    if sys.platform == "win32":
        kernel32 = ctypes.windll.kernel32
        # Get the current console mode
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # Enable ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

# Enable colors for Windows terminals
enable_virtual_terminal_processing()

# ANSI color codes
COLORS = {
    'RESET': '\033[0m',
    'BOLD': '\033[1m',
    'DIM': '\033[2m',
    'BLUE': '\033[34m',
    'GREEN': '\033[32m',
    'YELLOW': '\033[33m',
    'RED': '\033[31m',
    'MAGENTA': '\033[35m',
    'CYAN': '\033[36m',
    'WHITE': '\033[37m',
    'GRAY': '\033[90m'
}

class JsonFormatter(logging.Formatter):
    """Formatter that outputs JSON formatted logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Extract the message
        message = record.msg
        if isinstance(message, dict):
            # If message is already a dict, use it directly
            log_dict = message
        else:
            # Otherwise create a dict with the message
            log_dict = {'message': str(message)}
        
        # Format timestamp nicely
        timestamp = datetime.fromtimestamp(record.created)
        formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Truncate microseconds to 3 digits
        
        # Build the log entry with fields in a logical order
        entry = {
            # Metadata first
            'timestamp': formatted_time,
            'level': record.levelname,
            'logger': record.name,
            
            # Request tracking next
            **({"request_id": request_id.get()} if request_id.get() else {}),
            **({"correlation_id": correlation_id.get()} if correlation_id.get() else {}),
            
            # Message and context
            **log_dict
        }
        
        # Add exception info if present
        if record.exc_info:
            entry['exception'] = self.formatException(record.exc_info)
        
        # Format with nice indentation and add visual separator
        separator = '-' * 80 + '\n'
        json_str = json.dumps(entry, indent=2)
        
        # Add commas between fields
        json_str = json_str.replace('\n  "', ',\n  "')
        
        # Add color coding
        json_str = (
            json_str
            .replace('"timestamp":', f'{COLORS["CYAN"]}"timestamp":{COLORS["RESET"]}')
            .replace('"level":', f'{COLORS["YELLOW"]}"level":{COLORS["RESET"]}')
            .replace('"logger":', f'{COLORS["GREEN"]}"logger":{COLORS["RESET"]}')
            .replace('"message":', f'{COLORS["BLUE"]}"message":{COLORS["RESET"]}')
            .replace('"context":', f'{COLORS["MAGENTA"]}"context":{COLORS["RESET"]}')
            .replace('"request_id":', f'{COLORS["CYAN"]}"request_id":{COLORS["RESET"]}')
            .replace('"correlation_id":', f'{COLORS["CYAN"]}"correlation_id":{COLORS["RESET"]}')
        )
        
        return separator + json_str + '\n'

class PrettyFormatter(logging.Formatter):
    """Formatter that outputs clean, readable logs."""
    
    LEVEL_COLORS = {
        'DEBUG': COLORS['GRAY'],
        'INFO': COLORS['GREEN'],
        'WARNING': COLORS['YELLOW'],
        'ERROR': COLORS['RED'],
        'CRITICAL': COLORS['RED'] + COLORS['BOLD']
    }
    
    def __init__(self):
        """Initialize formatter with custom format."""
        super().__init__()
        # Enable colors by default, they will be disabled if terminal doesn't support them
        self.use_colors = True
        self._check_color_support()
    
    def _check_color_support(self):
        """Check if the terminal supports colors."""
        # Disable colors if NO_COLOR environment variable is set
        if os.getenv('NO_COLOR') is not None:
            self.use_colors = False
            return
            
        # Check if running in a terminal
        if not sys.stdout.isatty():
            self.use_colors = False
            return
            
        # Check for PowerShell
        if os.getenv('PSModulePath') is not None:
            # Colors should work in PowerShell since we enabled virtual terminal processing
            self.use_colors = True
            return
            
        # Check for Windows terminal type
        if sys.platform == "win32":
            # Check if running in Windows Terminal, VSCode, or other modern terminal
            if os.getenv('WT_SESSION') or os.getenv('TERM_PROGRAM'):
                self.use_colors = True
            else:
                # Legacy Windows console
                self.use_colors = False
        else:
            # Unix-like systems generally support colors
            self.use_colors = True
    
    def colorize(self, text: str, color: str) -> str:
        """Add color to text if colors are enabled."""
        if self.use_colors:
            return f"{color}{text}{COLORS['RESET']}"
        return text
    
    def format_timestamp(self, record: logging.LogRecord) -> str:
        """Format timestamp in a readable way."""
        try:
            dt = datetime.fromtimestamp(record.created)
            return dt.strftime('%H:%M:%S')
        except:
            return self.formatTime(record)
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in a clean, readable way."""
        # Build the log message
        parts = []
        
        # Timestamp and level
        level_color = self.LEVEL_COLORS.get(record.levelname, '')
        level_name = self.colorize(f"[{record.levelname:>7}]", level_color)
        parts.append(f"{self.format_timestamp(record)} {level_name}")
        
        # Logger name
        logger_name = record.name
        if '.' in logger_name:
            *modules, name = logger_name.split('.')
            logger_display = '.'.join(m[0] for m in modules) + '.' + name
        else:
            logger_display = logger_name
        parts.append(logger_display)
        
        # Main message
        message = record.msg
        if isinstance(message, str):
            parts.append(message)
        elif isinstance(message, dict):
            # Format dictionary messages
            msg = message.get('message', '')
            context = message.get('context', {})
            parts.append(msg)
            if context:
                context_parts = []
                for key, value in context.items():
                    if isinstance(value, (dict, list)):
                        context_parts.append(f"{key}={json.dumps(value, indent=2)}")
                    else:
                        context_parts.append(f"{key}={value}")
                if context_parts:
                    parts.append('(' + ', '.join(context_parts) + ')')
        else:
            parts.append(str(message))
        
        # Exception information
        if record.exc_info:
            parts.append('\n' + self.formatException(record.exc_info))
        
        return ' '.join(str(p) for p in parts if p)

class StructuredLogger:
    """Logger that outputs structured logs with additional context."""
    
    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _format_log(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """Format log entry as structured dictionary."""
        log_dict = {'message': message}
        if kwargs:
            log_dict['context'] = kwargs
        return log_dict

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(self._format_log('DEBUG', message, **kwargs))

    def info(self, message: str, **kwargs):
        """Log info message."""
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(self._format_log('INFO', message, **kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger.warning(self._format_log('WARNING', message, **kwargs))

    def error(self, message: str, **kwargs):
        """Log error message."""
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger.error(self._format_log('ERROR', message, **kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        if self.logger.isEnabledFor(logging.CRITICAL):
            self.logger.critical(self._format_log('CRITICAL', message, **kwargs))

class LogManager:
    """Manages logging configuration and setup."""
    
    _instance = None
    _debug_enabled = None
    _current_level = logging.INFO
    _initialized = False
    
    LEVEL_MAP = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logging configuration."""
        # Initialization is now handled by configure_logging
        pass
    
    @classmethod
    def is_debug_enabled(cls) -> bool:
        """Check if debug logging is enabled."""
        if cls._debug_enabled is None:
            debug_env = os.getenv('WORKFLOWMAX_DEBUG_LOGGING', '').lower()
            cls._debug_enabled = debug_env in ('true', '1', 'yes', 'on')
        return cls._debug_enabled
    
    @classmethod
    def set_debug_logging(cls, enabled: bool):
        """Enable or disable debug logging."""
        cls._debug_enabled = enabled
        cls.set_log_level('debug' if enabled else 'info')
    
    @classmethod
    def set_log_level(cls, level: Union[str, int]):
        """Set the logging level."""
        if isinstance(level, str):
            level = level.lower()
            if level not in cls.LEVEL_MAP:
                raise ValueError(f"Invalid log level: {level}")
            level_value = cls.LEVEL_MAP[level]
        else:
            level_value = level
        
        cls._current_level = level_value
        
        # Set level on root logger and all existing loggers
        root_logger = logging.getLogger()
        root_logger.setLevel(level_value)
        
        # Update all loggers
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.setLevel(level_value)
            # Also update all handlers for each logger
            for handler in logger.handlers:
                handler.setLevel(level_value)
        
        # Update all handlers on root logger
        for handler in root_logger.handlers:
            handler.setLevel(level_value)
    
    @classmethod
    def configure_logging(cls, level: str = 'info', logs_dir: Optional[Path] = None):
        """Configure logging with specified level and directory.
        
        Args:
            level: Log level to set (debug, info, warning, error, critical)
            logs_dir: Directory for log files (optional)
        """
        if cls._initialized:
            # Just update the log level if already initialized
            cls.set_log_level(level)
            return
            
        # Set up logging directory in system temp if not specified
        if logs_dir is None:
            logs_dir = get_app_log_dir()
        
        # Configure root logger
        root_logger = logging.getLogger()
        level_value = cls.LEVEL_MAP[level.lower()]
        root_logger.setLevel(level_value)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler with pretty formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(PrettyFormatter())
        console_handler.setLevel(level_value)  # Set handler level explicitly
        root_logger.addHandler(console_handler)
        
        # Add file handlers with JSON formatting
        json_formatter = JsonFormatter()
        
        # Main log file - INFO and above
        main_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'workflowmax.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setFormatter(json_formatter)
        main_handler.setLevel(logging.INFO)
        root_logger.addHandler(main_handler)
        
        # Error log file - ERROR and above
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'error.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setFormatter(json_formatter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
        
        # Debug log file - All levels
        debug_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'debug.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        debug_handler.setFormatter(json_formatter)
        debug_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(debug_handler)
        
        # Disable propagation for all loggers
        for name in logging.root.manager.loggerDict:
            logger = logging.getLogger(name)
            logger.propagate = False
        
        cls._initialized = True

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance.
    
    This will initialize logging if not already configured.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    if not LogManager._initialized:
        LogManager.configure_logging()
    return StructuredLogger(name)

def with_logging(func):
    """Decorator to add logging to functions."""
    logger = get_logger(func.__module__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request_id.get():
            request_id.set(str(uuid.uuid4()))
        
        log_args = [str(arg) for arg in args]
        log_kwargs = {k: str(v) for k, v in kwargs.items()}
        
        logger.debug(
            f"Calling {func.__name__}",
            args=log_args,
            kwargs=log_kwargs
        )
        
        try:
            result = func(*args, **kwargs)
            logger.debug(
                f"Completed {func.__name__}",
                result=str(result)
            )
            return result
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
            
    return wrapper

def set_correlation_id(corr_id: Optional[str] = None):
    """Set correlation ID for request tracking."""
    correlation_id.set(corr_id or str(uuid.uuid4()))

def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id.get()
