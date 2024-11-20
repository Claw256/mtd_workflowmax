"""Test and demonstrate enhanced logging functionality."""

import os
from mtd_workflowmax.core.logging import LogManager, get_logger

def demonstrate_logging():
    """Demonstrate different logging levels and debug control."""
    logger = get_logger(__name__)
    
    # Log some messages at different levels
    logger.info("Starting logging demonstration")
    logger.debug("This debug message won't show unless debug is enabled")
    
    # Enable debug logging programmatically
    print("\nEnabling debug logging programmatically:")
    LogManager.set_debug_logging(True)
    logger.debug("This debug message will now show")
    logger.info("Regular info message still shows")
    
    # Disable debug logging programmatically
    print("\nDisabling debug logging programmatically:")
    LogManager.set_debug_logging(False)
    logger.debug("This debug message won't show")
    logger.info("Regular info message still shows")
    
    # Demonstrate environment variable control
    print("\nDemonstrating environment variable control:")
    os.environ['WORKFLOWMAX_DEBUG_LOGGING'] = 'true'
    # Force LogManager to re-check environment variable
    LogManager._debug_enabled = None
    LogManager()  # Reinitialize logging
    logger.debug("Debug message shows due to environment variable")
    
    # Clean up
    del os.environ['WORKFLOWMAX_DEBUG_LOGGING']
    LogManager._debug_enabled = None
    LogManager()  # Reset to default state

if __name__ == '__main__':
    demonstrate_logging()
