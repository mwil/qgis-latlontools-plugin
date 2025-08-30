"""
Enhanced Settings Module
Provides smart auto-detect functionality and persistence for the Lat Lon Tools plugin
"""

from qgis.core import QgsSettings, QgsMessageLog
from qgis.PyQt.QtCore import Qt
from .util import tr
from .settings import CoordOrder

try:
    from . import h3
    H3_INSTALLED = True
except ImportError:
    H3_INSTALLED = False


class EnhancedSettingsManager:
    """
    Manages enhanced settings functionality including:
    - Smart Auto-Detect coordinate mode
    - Settings persistence
    - Enhanced combo box options
    """
    
    # Enhanced projection type constants
    ZoomProjectionTypeSmartAuto = 9 if H3_INSTALLED else 8
    ProjectionTypeSmartAuto = 9 if H3_INSTALLED else 8
    
    def __init__(self, settings_widget):
        self.settings = settings_widget
        
    def add_smart_auto_detect_option(self):
        """Add Smart Auto-Detect option to the zoom projection combo box"""
        if H3_INSTALLED:
            items = [
                tr('WGS 84 (Latitude & Longitude) / Auto Detect Format'), 
                tr('Project CRS'), 
                tr('Custom CRS'), 
                tr('MGRS'), 
                tr('Plus Codes (Open Location Code)'), 
                tr('Standard UTM'),
                tr('Geohash'),
                tr('Maidenhead Grid'),
                'H3', 
                tr('Smart Auto-Detect (Any Format)')
            ]
        else:
            items = [
                tr('WGS 84 (Latitude & Longitude) / Auto Detect Format'), 
                tr('Project CRS'), 
                tr('Custom CRS'), 
                tr('MGRS'), 
                tr('Plus Codes (Open Location Code)'), 
                tr('Standard UTM'),
                tr('Geohash'),
                tr('Maidenhead Grid'), 
                tr('Smart Auto-Detect (Any Format)')
            ]
        
        # Clear and repopulate combo box
        self.settings.zoomToProjectionComboBox.clear()
        self.settings.zoomToProjectionComboBox.addItems(items)
        
    def read_enhanced_settings(self):
        """Read settings with enhanced Smart Auto-Detect handling"""
        qset = QgsSettings()
        
        # Read zoom projection setting with proper handling
        qsettings_value = qset.value('/LatLonTools/ZoomToCoordType', 0)
        zoom_projection = int(qsettings_value)
        
        # Handle Smart Auto-Detect and H3 conflicts properly
        if zoom_projection == self.ZoomProjectionTypeSmartAuto:
            # This is Smart Auto-Detect, keep it
            pass
        elif not H3_INSTALLED and zoom_projection == 8:  # ZoomProjectionTypeH3
            # H3 is not installed but user had H3 selected, reset to WGS84
            zoom_projection = 0
        
        # Handle case where index might be out of range
        max_zoom_index = 9 if H3_INSTALLED else 8
        if zoom_projection > max_zoom_index:
            zoom_projection = 0
            
        return zoom_projection
        
    def is_smart_auto_detect(self, zoom_projection):
        """Check if Smart Auto-Detect mode is selected"""
        return zoom_projection == self.ZoomProjectionTypeSmartAuto
        
    def set_smart_auto_detect_mode(self):
        """Set zoom projection to Smart Auto-Detect mode"""
        qset = QgsSettings()
        self.settings.zoomToProjection = self.ZoomProjectionTypeSmartAuto
        self.settings.zoomToProjectionComboBox.setCurrentIndex(self.ZoomProjectionTypeSmartAuto)
        qset.setValue('/LatLonTools/ZoomToCoordType', int(self.ZoomProjectionTypeSmartAuto))
        
    def update_coordinate_order_enable_state(self, zoom_projection):
        """Update enabled state for coordinate order controls in Smart Auto-Detect mode"""
        # Import constants from settings module
        from .settings import SettingsWidget as SW
        
        # Disable coordinate order for Smart Auto-Detect (same as MGRS, Plus Codes, etc.)
        should_disable = (
            zoom_projection == SW.ProjectionTypeMGRS or
            zoom_projection == SW.ProjectionTypePlusCodes or
            zoom_projection == SW.ProjectionTypeUTM or
            zoom_projection == SW.ProjectionTypeGeohash or
            zoom_projection == SW.ProjectionTypeMaidenhead or
            zoom_projection == SW.ZoomProjectionTypeH3 or
            zoom_projection == self.ZoomProjectionTypeSmartAuto
        )
        
        self.settings.zoomToCoordOrderComboBox.setEnabled(not should_disable)