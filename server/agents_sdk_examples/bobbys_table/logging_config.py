"""
Logging configuration for Bobby's Table Restaurant
Sets up structured logging for different components
"""

import logging
import os
from datetime import datetime
import pytz

class EDTFormatter(logging.Formatter):
    """Custom formatter that uses EDT timezone consistently"""
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        self.tz = pytz.timezone('US/Eastern')
    
    def formatTime(self, record, datefmt=None):
        """Format the time in EDT timezone"""
        dt = datetime.fromtimestamp(record.created, tz=self.tz)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S EDT')

def setup_logging():
    """
    Setup logging configuration for the restaurant application
    
    Returns:
        dict: Dictionary of configured loggers
    """
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatters with EDT timezone
    detailed_formatter = EDTFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    simple_formatter = EDTFormatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Configure werkzeug logger to use EDT
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplication
    for handler in werkzeug_logger.handlers[:]:
        werkzeug_logger.removeHandler(handler)
    
    # Add custom handler with EDT formatting
    werkzeug_handler = logging.StreamHandler()
    werkzeug_handler.setFormatter(simple_formatter)
    werkzeug_logger.addHandler(werkzeug_handler)
    
    # Configure main application logger
    main_logger = logging.getLogger('bobbys_table.main')
    main_logger.setLevel(logging.INFO)
    
    # Main log file handler
    main_handler = logging.FileHandler(
        os.path.join(log_dir, 'main.log'),
        encoding='utf-8'
    )
    main_handler.setFormatter(detailed_formatter)
    main_logger.addHandler(main_handler)
    
    # Console handler for main logger
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    main_logger.addHandler(console_handler)
    
    # Configure reservations logger
    reservations_logger = logging.getLogger('bobbys_table.reservations')
    reservations_logger.setLevel(logging.INFO)
    
    reservations_handler = logging.FileHandler(
        os.path.join(log_dir, 'reservations.log'),
        encoding='utf-8'
    )
    reservations_handler.setFormatter(detailed_formatter)
    reservations_logger.addHandler(reservations_handler)
    
    # Configure payments logger
    payments_logger = logging.getLogger('bobbys_table.payments')
    payments_logger.setLevel(logging.INFO)
    
    payments_handler = logging.FileHandler(
        os.path.join(log_dir, 'payments.log'),
        encoding='utf-8'
    )
    payments_handler.setFormatter(detailed_formatter)
    payments_logger.addHandler(payments_handler)
    
    # Configure SMS logger
    sms_logger = logging.getLogger('bobbys_table.sms')
    sms_logger.setLevel(logging.INFO)
    
    sms_handler = logging.FileHandler(
        os.path.join(log_dir, 'sms.log'),
        encoding='utf-8'
    )
    sms_handler.setFormatter(detailed_formatter)
    sms_logger.addHandler(sms_handler)
    
    # Log startup message
    main_logger.info("Bobby's Table Restaurant - Logging initialized with EDT timezone")
    main_logger.info(f"Log files created in: {os.path.abspath(log_dir)}")
    
    # Return dictionary of loggers as expected by app.py
    return {
        'main': main_logger,
        'reservations': reservations_logger,
        'payments': payments_logger,
        'sms': sms_logger
    }

# For backwards compatibility, also provide individual logger functions
def get_main_logger():
    """Get the main application logger"""
    return logging.getLogger('bobbys_table.main')

def get_reservations_logger():
    """Get the reservations logger"""
    return logging.getLogger('bobbys_table.reservations')

def get_payments_logger():
    """Get the payments logger"""
    return logging.getLogger('bobbys_table.payments')

def get_sms_logger():
    """Get the SMS logger"""
    return logging.getLogger('bobbys_table.sms') 