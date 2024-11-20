"""Enhanced logging configuration for WorkflowMax API."""

import logging
import logging.handlers
import json
import uuid
import time
from datetime import datetime
import threading
import os
from pathlib import Path
from typing import Optional, Dict, Any, Union
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracking
request_id: ContextVar[str] = ContextVar('request_id', default='')
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

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

class PrettyFormatter(logging.Formatter):
    """Formatter that outputs visually appealing, readable logs."""
    
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
        self.use_colors = os.name != 'nt'  # Disable colors on Windows
        self._last_section = None
    
    def colorize(self, text: str, color: str) -> str:
        """Add color to text if colors are enabled."""
        if self.use_colors:
            return f"{color}{text}{COLORS['RESET']}"
        return text
    
    def format_timestamp(self, record: logging.LogRecord) -> str:
        """Format timestamp in a readable way."""
        try:
            dt = datetime.fromtimestamp(record.created)
            return self.colorize(dt.strftime('%H:%M:%S'), COLORS['DIM'])
        except:
            return self.colorize(self.formatTime(record), COLORS['DIM'])
    
    def format_section(self, title: str, content: str, level: int = 0) -> str:
        """Format a section with title and content."""
        indent = '  ' * level
        separator = self.colorize('│ ', COLORS['DIM'])
        indented_content = '\n'.join(f"{indent}{separator}{line}" for line in content.split('\n'))
        header = self.colorize(f"{indent}┌─ ", COLORS['DIM'])
        return f"{header}{title}\n{indented_content}"
    
    def format_key_value(self, key: str, value: Any, level: int = 0) -> str:
        """Format a key-value pair."""
        indent = '  ' * level
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)
            return f"{indent}{self.colorize(key + ':', COLORS['CYAN'])}\n" + '\n'.join(f"{indent}  {line}" for line in value.split('\n'))
        return f"{indent}{self.colorize(key + ':', COLORS['CYAN'])} {value}"
    
    def format_percentage(self, value: float) -> str:
        """Format percentage value."""
        return f"{value:.1f}%"
    
    def format_status(self, passed: bool) -> str:
        """Format pass/fail status."""
        if passed:
            return self.colorize('✓ PASS', COLORS['GREEN'])
        return self.colorize('✗ FAIL', COLORS['RED'])
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in a visually appealing way."""
        # Try to parse JSON if message is a JSON string
        try:
            if record.msg.startswith('{') and record.msg.endswith('}'):
                data = json.loads(record.msg)
            else:
                data = {'message': record.msg}
        except:
            data = {'message': record.msg}
        
        # Build the log message
        parts = []
        
        # Timestamp and level
        level_color = self.LEVEL_COLORS.get(record.levelname, '')
        level_name = self.colorize(f"[{record.levelname:^8}]", level_color)
        parts.append(f"{self.format_timestamp(record)} {level_name}")
        
        # Logger name
        logger_name = data.get('logger', record.name)
        if '.' in logger_name:
            *modules, name = logger_name.split('.')
            logger_display = self.colorize('.'.join(m[0] for m in modules) + '.' + name, COLORS['BLUE'])
        else:
            logger_display = self.colorize(logger_name, COLORS['BLUE'])
        parts.append(logger_display)
        
        # Main message
        message = data.get('message', str(record.msg))
        
        # Check if this is a section header
        if message.startswith('=') and message.endswith('='):
            self._last_section = message
            return '\n' + message
        
        # Add extra newline after section headers
        if self._last_section and not message.startswith('='):
            parts.append('')
            self._last_section = None
        
        # Format message
        if '\n' in message:
            parts.append(self.format_section('Message', message))
        else:
            parts.append(message)
        
        # Context information
        context = data.get('context', {})
        if context:
            context_lines = []
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    context_lines.append(self.format_section(key, json.dumps(value, indent=2)))
                else:
                    context_lines.append(self.format_key_value(key, value))
            if context_lines:
                parts.append('\n' + '\n'.join(context_lines))
        
        # Request tracking
        req_id = data.get('request_id') or record.request_id if hasattr(record, 'request_id') else None
        corr_id = data.get('correlation_id') or record.correlation_id if hasattr(record, 'correlation_id') else None
        
        if req_id or corr_id:
            tracking = []
            if req_id:
                tracking.append(self.format_key_value('Request ID', req_id))
            if corr_id:
                tracking.append(self.format_key_value('Correlation ID', corr_id))
            parts.append('\n' + '\n'.join(tracking))
        
        # Exception information
        if record.exc_info:
            parts.append('\n' + self.colorize('Exception:', COLORS['RED']))
            parts.append(self.formatException(record.exc_info))
        
        return ' '.join(str(p) for p in parts if p)

class StructuredLogger:
    """Logger that outputs structured logs with additional context."""
    
    def __init__(self, name: str):
        """Initialize structured logger."""
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _format_log(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """Format log entry as structured dictionary."""
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'logger': self.name,
            'level': level,
            'message': message,
            'thread_id': threading.get_ident(),
            'request_id': request_id.get(),
            'correlation_id': correlation_id.get()
        }
        
        if kwargs:
            serializable_kwargs = {}
            for key, value in kwargs.items():
                try:
                    json.dumps(value)
                    serializable_kwargs[key] = value
                except (TypeError, OverflowError):
                    serializable_kwargs[key] = str(value)
            log_entry['context'] = serializable_kwargs
            
        return log_entry

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                json.dumps(self._format_log('DEBUG', message, **kwargs))
            )

    def info(self, message: str, **kwargs):
        """Log info message."""
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(
                json.dumps(self._format_log('INFO', message, **kwargs))
            )

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger.warning(
                json.dumps(self._format_log('WARNING', message, **kwargs))
            )

    def error(self, message: str, **kwargs):
        """Log error message."""
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger.error(
                json.dumps(self._format_log('ERROR', message, **kwargs))
            )

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        if self.logger.isEnabledFor(logging.CRITICAL):
            self.logger.critical(
                json.dumps(self._format_log('CRITICAL', message, **kwargs))
            )

class LogManager:
    """Manages logging configuration and setup."""
    
    _instance = None
    _debug_enabled = None
    _current_level = logging.INFO
    
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
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize logging configuration."""
        if not self._initialized:
            self._setup_logging()
            self._initialized = True
    
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
        root_logger = logging.getLogger()
        root_logger.setLevel(level_value)
        
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(level_value)
    
    def _setup_logging(self):
        """Configure logging with file and console handlers."""
        logs_dir = self._get_logs_dir()
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(self._current_level)
        
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler with pretty formatting
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(PrettyFormatter())
        console_handler.setLevel(self._current_level)
        root_logger.addHandler(console_handler)
        
        # Add file handlers with JSON formatting for machine processing
        self._add_file_handlers(root_logger, logs_dir)
    
    def _get_logs_dir(self) -> Path:
        """Get logs directory path."""
        return Path('logs')
    
    def _add_file_handlers(self, logger: logging.Logger, logs_dir: Path):
        """Add rotating file handlers for different log levels."""
        json_formatter = logging.Formatter('%(message)s')
        
        # Main log file - INFO and above
        main_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'workflowmax.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setFormatter(json_formatter)
        main_handler.setLevel(logging.INFO)
        logger.addHandler(main_handler)
        
        # Error log file - ERROR and above
        error_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'error.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setFormatter(json_formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
        
        # Debug log file - All levels
        debug_handler = logging.handlers.RotatingFileHandler(
            logs_dir / 'debug.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        debug_handler.setFormatter(json_formatter)
        debug_handler.setLevel(logging.DEBUG)
        logger.addHandler(debug_handler)

def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    LogManager()  # Ensure logging is configured
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
