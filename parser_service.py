"""
Coordinate Parser Service Layer
Provides centralized coordinate parsing functionality to eliminate duplication across UI components
"""
from qgis.core import QgsMessageLog, Qgis

# Handle both plugin context (relative imports) and standalone testing (absolute imports)
try:
    from .smart_parser import SmartCoordinateParser
    from .util import epsg4326
except ImportError:
    from smart_parser import SmartCoordinateParser
    from util import epsg4326


class CoordinateParserService:
    """
    Service layer for coordinate parsing with consistent logging and error handling
    Eliminates code duplication across UI components
    """
    _instance = None
    
    @classmethod
    def get_instance(cls, settings=None, iface=None):
        """
        Singleton pattern for service instance
        Returns existing instance or creates new one if settings/iface provided
        """
        if cls._instance is None and settings is not None and iface is not None:
            cls._instance = cls(settings, iface)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        cls._instance = None
    
    def __init__(self, settings, iface):
        """Initialize service with settings and iface"""
        self.settings = settings
        self.iface = iface
        self._parser = SmartCoordinateParser(settings, iface)
        QgsMessageLog.logMessage("CoordinateParserService: Service initialized", "LatLonTools", Qgis.Info)
    
    def parse_coordinate_with_logging(self, text: str, component_name: str = "Unknown"):
        """
        Parse coordinate with consistent logging and error handling
        
        Args:
            text: Input coordinate text
            component_name: Name of UI component for logging
            
        Returns:
            (success: bool, result: tuple or None, error_msg: str or None)
            Where result is (lat, lon, bounds, source_crs) if success=True
        """
        original_text = text.strip()
        QgsMessageLog.logMessage(f"ParserService.parse_coordinate_with_logging: {component_name} parsing '{original_text}'", "LatLonTools", Qgis.Info)
        
        try:
            result = self._parser.parse(text)
            if result:
                lat, lon, bounds, source_crs = result
                QgsMessageLog.logMessage(f"ParserService.parse_coordinate_with_logging: {component_name} SUCCESS - lat={lat}, lon={lon}, crs={source_crs}", "LatLonTools", Qgis.Info)
                return True, result, None
            else:
                msg = f"{component_name}: SmartParser failed - coordinate not recognized"
                QgsMessageLog.logMessage(f"ParserService.parse_coordinate_with_logging: {msg}", "LatLonTools", Qgis.Warning)
                return False, None, msg
                
        except Exception as e:
            error_msg = f"{component_name}: Parsing error - {e}"
            QgsMessageLog.logMessage(f"ParserService.parse_coordinate_with_logging: ERROR - {error_msg}", "LatLonTools", Qgis.Critical)
            return False, None, error_msg
    
    def parse_coordinate_simple(self, text: str, component_name: str = "Unknown"):
        """
        Simple coordinate parsing that returns result or None
        
        Args:
            text: Input coordinate text
            component_name: Name of UI component for logging
            
        Returns:
            (lat, lon, bounds, source_crs) or None
        """
        success, result, error_msg = self.parse_coordinate_with_logging(text, component_name)
        return result if success else None


class CoordinateParserMixin:
    """
    Mixin to provide consistent coordinate parsing to UI components
    Eliminates the repeated parser instantiation pattern
    """
    
    def _get_parser_service(self):
        """Get or create parser service instance"""
        # Try to get existing singleton
        service = CoordinateParserService.get_instance()
        if service is None:
            # Create new instance with our settings and iface
            service = CoordinateParserService(self.settings, self.iface)
        return service
    
    def parse_coordinate_with_fallback(self, text: str, component_name: str, legacy_parser_func=None):
        """
        Standard coordinate parsing with fallback pattern
        
        Args:
            text: Input coordinate text
            component_name: Name of UI component for logging
            legacy_parser_func: Optional legacy parsing function for fallback
            
        Returns:
            (lat, lon, bounds, source_crs) or None
        """
        parser_service = self._get_parser_service()
        success, result, error_msg = parser_service.parse_coordinate_with_logging(text, component_name)
        
        if success:
            return result
        elif legacy_parser_func:
            try:
                QgsMessageLog.logMessage(f"ParserMixin: {component_name} trying legacy fallback...", "LatLonTools", Qgis.Info)
                legacy_result = legacy_parser_func(text)
                if legacy_result:
                    QgsMessageLog.logMessage(f"ParserMixin: {component_name} legacy fallback SUCCESS", "LatLonTools", Qgis.Info)
                    return legacy_result
                else:
                    QgsMessageLog.logMessage(f"ParserMixin: {component_name} legacy fallback also failed", "LatLonTools", Qgis.Warning)
            except Exception as e:
                QgsMessageLog.logMessage(f"ParserMixin: {component_name} legacy fallback exception - {e}", "LatLonTools", Qgis.Critical)
        
        return None
    
    def parse_coordinate_simple_with_fallback(self, text: str, component_name: str, legacy_parser_func=None):
        """
        Simplified version that returns just the parsed result
        
        Returns:
            (lat, lon, bounds, source_crs) or None
        """
        return self.parse_coordinate_with_fallback(text, component_name, legacy_parser_func)


# Convenience function for components that can't use the mixin
def parse_coordinate_with_service(text: str, component_name: str, settings, iface, legacy_parser_func=None):
    """
    Standalone function for coordinate parsing using service layer
    Useful for components that can't inherit from CoordinateParserMixin
    
    Args:
        text: Input coordinate text
        component_name: Name of UI component for logging
        settings: QGIS settings object
        iface: QGIS interface object
        legacy_parser_func: Optional legacy parsing function for fallback
        
    Returns:
        (lat, lon, bounds, source_crs) or None
    """
    # Get or create service
    service = CoordinateParserService.get_instance(settings, iface)
    success, result, error_msg = service.parse_coordinate_with_logging(text, component_name)
    
    if success:
        return result
    elif legacy_parser_func:
        try:
            QgsMessageLog.logMessage(f"parse_coordinate_with_service: {component_name} trying legacy fallback...", "LatLonTools", Qgis.Info)
            legacy_result = legacy_parser_func(text)
            if legacy_result:
                QgsMessageLog.logMessage(f"parse_coordinate_with_service: {component_name} legacy fallback SUCCESS", "LatLonTools", Qgis.Info)
                return legacy_result
            else:
                QgsMessageLog.logMessage(f"parse_coordinate_with_service: {component_name} legacy fallback also failed", "LatLonTools", Qgis.Warning)
        except Exception as e:
            QgsMessageLog.logMessage(f"parse_coordinate_with_service: {component_name} legacy fallback exception - {e}", "LatLonTools", Qgis.Critical)
    
    return None