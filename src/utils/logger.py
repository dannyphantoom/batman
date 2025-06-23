"""
Logging utilities for Batman package manager
"""

import logging
import sys
from pathlib import Path
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

def setup_logger(name: str = 'batman', level: str = 'INFO') -> 'BatmanLogger':
    """Setup and configure logger for Batman package manager"""
    
    logger = logging.getLogger(name)
    
    # Avoid adding multiple handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create colored formatter
    formatter = ColoredFormatter(
        fmt='%(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Create file handler for persistent logging
    log_dir = Path.home() / '.batman' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / 'batman.log')
    file_handler.setLevel(logging.DEBUG)
    
    # Create file formatter (without colors)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add file handler to logger
    logger.addHandler(file_handler)
    
    return BatmanLogger(logger)

class BatmanLogger:
    """Enhanced logger with Batman-specific functionality"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def command_start(self, command: str, package: str = "", manager: str = ""):
        """Log the start of a command"""
        msg = f"🦇 Starting {command}"
        if package:
            msg += f" for package '{package}'"
        if manager:
            msg += f" using {manager}"
        self.logger.info(msg)
    
    def command_success(self, command: str, package: str = "", details: str = ""):
        """Log successful command completion"""
        msg = f"✅ {command} completed successfully"
        if package:
            msg += f" for '{package}'"
        if details:
            msg += f" - {details}"
        self.logger.info(msg)
    
    def command_error(self, command: str, error: str, package: str = ""):
        """Log command error"""
        msg = f"❌ {command} failed"
        if package:
            msg += f" for '{package}'"
        msg += f": {error}"
        self.logger.error(msg)
    
    def package_info(self, package: str, version: str = "", manager: str = ""):
        """Log package information"""
        msg = f"📦 Package: {package}"
        if version:
            msg += f" (v{version})"
        if manager:
            msg += f" [{manager}]"
        self.logger.info(msg)
    
    def update_available(self, package: str, current: str, latest: str):
        """Log available update"""
        self.logger.info(f"🔄 Update available for {package}: {current} → {latest}")
    
    def dry_run(self, action: str):
        """Log dry run action"""
        self.logger.info(f"🔍 [DRY RUN] Would execute: {action}")
    
    def progress(self, message: str):
        """Log progress message"""
        self.logger.info(f"⏳ {message}")
    
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(f"⚠️  {message}")
    
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
    
    def error(self, message: str):
        """Log error message"""
        self.logger.error(message)
    
    def setLevel(self, level: str):
        """Set logger level"""
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(numeric_level)
        for handler in self.logger.handlers:
            handler.setLevel(numeric_level) 