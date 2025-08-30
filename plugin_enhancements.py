"""
Plugin Enhancements Module
Coordinates all enhanced functionality for the Lat Lon Tools plugin:
- Smart Auto-Detect coordinate parsing
- Text preservation during coordinate order changes  
- Enhanced settings persistence
- Safe plugin cleanup
"""

from .enhanced_settings import EnhancedSettingsManager
from .text_preservation import TextPreservationMixin
from .plugin_cleanup import SafePluginCleanup, SafeDockWidgetCleanup
from .smart_parser import SmartCoordinateParser
from .util import tr


class PluginEnhancements:
    """
    Main coordinator class for all plugin enhancements
    Provides a clean interface to integrate new functionality with existing code
    """
    
    def __init__(self, plugin_instance, iface):
        self.plugin = plugin_instance
        self.iface = iface
        self.cleanup_manager = None
        
    def initialize_enhancements(self):
        """Initialize all enhancements - call during plugin setup"""
        # Initialize safe cleanup
        self.cleanup_manager = SafePluginCleanup(self.plugin)
        
    def enhance_settings_dialog(self, settings_widget):
        """Enhance the settings dialog with new functionality"""
        settings_manager = EnhancedSettingsManager(settings_widget)
        
        # Add Smart Auto-Detect option to combo box
        settings_manager.add_smart_auto_detect_option()
        
        # Enhance readSettings method
        original_read_settings = settings_widget.readSettings
        
        def enhanced_read_settings():
            # Call original read settings first
            original_read_settings()
            
            # Apply enhanced settings logic
            settings_widget.zoomToProjection = settings_manager.read_enhanced_settings()
            
        settings_widget.readSettings = enhanced_read_settings
        
        # Add Smart Auto-Detect check method
        settings_widget.zoomToProjIsSmartAuto = lambda: settings_manager.is_smart_auto_detect(settings_widget.zoomToProjection)
        
        # Enhance setZoomToMode method
        original_set_zoom_to_mode = settings_widget.setZoomToMode
        
        def enhanced_set_zoom_to_mode(mode, crs=None):
            if mode == 'smart_auto':
                settings_manager.set_smart_auto_detect_mode()
            else:
                original_set_zoom_to_mode(mode, crs)
                
        settings_widget.setZoomToMode = enhanced_set_zoom_to_mode
        
        # Enhance setEnabled method
        original_set_enabled = settings_widget.setEnabled
        
        def enhanced_set_enabled():
            original_set_enabled()
            # Update coordinate order enable state for Smart Auto-Detect
            settings_manager.update_coordinate_order_enable_state(settings_widget.zoomToProjection)
            
        settings_widget.setEnabled = enhanced_set_enabled
        
        return settings_manager
        
    def enhance_zoom_dialog(self, zoom_dialog):
        """Enhance the zoom to coordinates dialog with new functionality"""
        
        # Add Smart Auto-Detect option to CRS menu
        menu = zoom_dialog.crsmenu
        action = menu.addAction(tr("Smart Auto-Detect"))
        action.setData('smart_auto')
        
        # Enhance the coordinate conversion method
        original_convert_coordinate = zoom_dialog.convertCoordinate
        
        def enhanced_convert_coordinate(text):
            # Smart auto-detect mode
            if zoom_dialog.settings.zoomToProjIsSmartAuto():
                parser = SmartCoordinateParser(zoom_dialog.settings, zoom_dialog.iface)
                result = parser.parse(text)
                if result is not None:
                    return result
                # If smart parser fails, fall back to regular parsing logic
                    
            # Call original method for other modes
            return original_convert_coordinate(text)
            
        zoom_dialog.convertCoordinate = enhanced_convert_coordinate
        
        # Enhance configure method for Smart Auto-Detect labeling
        original_configure = zoom_dialog.configure
        
        def enhanced_configure():
            original_configure()
            
            # Update label for Smart Auto-Detect mode
            if zoom_dialog.settings.zoomToProjIsSmartAuto():
                if zoom_dialog.settings.zoomToCoordOrder == 0:  # Y,X (Lat/Lon)
                    zoom_dialog.label.setText(tr("Enter coordinates (auto-detected, prefers Lat/Lon order)"))
                else:  # X,Y (Lon/Lat) 
                    zoom_dialog.label.setText(tr("Enter coordinates (auto-detected, prefers Lon/Lat order)"))
                    
        zoom_dialog.configure = enhanced_configure
        
        # Add text preservation to X,Y button
        preservation_mixin = TextPreservationMixin()
        
        original_xy_button_clicked = zoom_dialog.xyButtonClicked
        
        def enhanced_xy_button_clicked():
            preservation_mixin.preserve_text_during_order_change(
                zoom_dialog.coordTxt, 
                zoom_dialog.settings, 
                zoom_dialog.configure
            )
            
        zoom_dialog.xyButtonClicked = enhanced_xy_button_clicked
        
        # Add safe cleanup method
        zoom_dialog.cleanup = lambda: SafeDockWidgetCleanup.cleanup_zoom_dialog(zoom_dialog)
        
    def safe_unload(self):
        """Perform safe plugin unload"""
        if self.cleanup_manager:
            self.cleanup_manager.safe_unload()