"""
Centralized Logging Module for Zed Video Editor

Provides a configurable, thread-safe logging system for monitoring
internal processes, operations, and errors across the application.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from threading import Lock


class ZedLogger:
    """
    Centralized logger for the Zed video editing application.
    
    Features:
    - Thread-safe singleton pattern
    - Configurable log levels
    - Console and file output support
    - Structured formatting with timestamps
    - Component-based logging (ffmpeg, tasks, operations, etc.)
    """
    
    _instance: Optional['ZedLogger'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'ZedLogger':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._loggers: dict[str, logging.Logger] = {}
        self._log_level = logging.INFO
        self._log_file: Optional[Path] = None
        self._console_handler: Optional[logging.Handler] = None
        self._file_handler: Optional[logging.Handler] = None
        
        # Default format
        self._formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def configure(
        self,
        level: int = logging.INFO,
        log_file: Optional[str | Path] = None,
        console_output: bool = True,
        file_output: bool = False,
    ) -> None:
        """
        Configure global logging settings.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Path to log file (if file_output is True)
            console_output: Enable console logging
            file_output: Enable file logging
        """
        self._log_level = level
        
        if file_output and log_file:
            self._log_file = Path(log_file)
            self._log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Reconfigure all existing loggers
        for logger in self._loggers.values():
            self._setup_logger_handlers(logger)
    
    def _setup_logger_handlers(self, logger: logging.Logger) -> None:
        """Set up handlers for a specific logger."""
        # Clear existing handlers
        logger.handlers.clear()
        
        logger.setLevel(self._log_level)
        
        if self._console_handler is None and self._log_level:
            self._console_handler = logging.StreamHandler(sys.stdout)
            self._console_handler.setFormatter(self._formatter)
        
        if self._console_handler:
            logger.addHandler(self._console_handler)
        
        if self._log_file:
            if self._file_handler is None:
                self._file_handler = logging.FileHandler(self._log_file, encoding='utf-8')
                self._file_handler.setFormatter(self._formatter)
            logger.addHandler(self._file_handler)
    
    def get_logger(self, component: str) -> logging.Logger:
        """
        Get or create a logger for a specific component.
        
        Args:
            component: Component name (e.g., 'ffmpeg', 'tasks', 'operations.clip')
        
        Returns:
            Configured logger instance
        """
        if component not in self._loggers:
            logger = logging.getLogger(f'zed.{component}')
            logger.propagate = False  # Prevent duplicate logs
            self._setup_logger_handlers(logger)
            self._loggers[component] = logger
        
        return self._loggers[component]
    
    @property
    def level(self) -> int:
        """Get current log level."""
        return self._log_level


# Global logger instance
_logger_instance: Optional[ZedLogger] = None

def get_logger(component: str = 'core') -> logging.Logger:
    """
    Convenience function to get a component logger.
    
    Args:
        component: Component name for logging context
    
    Returns:
        Logger instance for the component
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ZedLogger()
    return _logger_instance.get_logger(component)


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str | Path] = None,
    console_output: bool = True,
    file_output: bool = False,
) -> None:
    """
    Configure the global logging system.
    
    Args:
        level: Logging level
        log_file: Path to log file
        console_output: Enable console output
        file_output: Enable file output
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ZedLogger()
    _logger_instance.configure(level, log_file, console_output, file_output)
