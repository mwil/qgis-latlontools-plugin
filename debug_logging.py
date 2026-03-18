"""
Debug logging utilities for coordinate parsing performance optimization.

Set DEBUG_PARSING = True to enable verbose logging during development.
In production, DEBUG_PARSING = False eliminates logging overhead.
"""

DEBUG_PARSING = False  # Production default - set True for debugging


def log_debug(msg, tag="LatLonTools"):
    """
    Conditional debug logging - only logs when DEBUG_PARSING is True.
    Use for verbose parsing step-by-step logging.
    """
    if not DEBUG_PARSING:
        return
    try:
        from qgis.core import QgsMessageLog, Qgis

        QgsMessageLog.logMessage(msg, tag, Qgis.Info)
    except Exception:
        pass  # Silently fail if QGIS not available


def log_info(msg, tag="LatLonTools"):
    """
    Always log at Info level - use sparingly for important messages only.
    Reserved for significant events (errors, warnings, initialization).
    """
    try:
        from qgis.core import QgsMessageLog, Qgis

        QgsMessageLog.logMessage(msg, tag, Qgis.Info)
    except Exception:
        pass


def log_warning(msg, tag="LatLonTools"):
    """Always log warnings - these indicate potential issues."""
    try:
        from qgis.core import QgsMessageLog, Qgis

        QgsMessageLog.logMessage(msg, tag, Qgis.Warning)
    except Exception:
        pass


def log_error(msg, tag="LatLonTools"):
    """Always log errors - these indicate failures."""
    try:
        from qgis.core import QgsMessageLog, Qgis

        QgsMessageLog.logMessage(msg, tag, Qgis.Critical)
    except Exception:
        pass


def enable_debug_logging():
    """Enable verbose debug logging for development/debugging."""
    global DEBUG_PARSING
    DEBUG_PARSING = True


def disable_debug_logging():
    """Disable verbose debug logging for production."""
    global DEBUG_PARSING
    DEBUG_PARSING = False


def is_debug_enabled():
    """Check if debug logging is currently enabled."""
    return DEBUG_PARSING
