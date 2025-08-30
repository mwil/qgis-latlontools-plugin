"""
Plugin Cleanup Module
Provides safe cleanup functionality to prevent QGIS hanging during plugin unload
"""

from qgis.core import QgsWkbTypes


class SafePluginCleanup:
    """
    Handles safe cleanup of plugin resources to prevent QGIS hanging during shutdown
    """
    
    def __init__(self, plugin_instance):
        self.plugin = plugin_instance
        self.plugin._is_unloading = False
        
    def safe_unload(self):
        """Perform safe cleanup of all plugin resources"""
        # Set unloading flag to prevent any operations during shutdown
        self.plugin._is_unloading = True
        
        try:
            # Cleanup dock widgets with their custom cleanup methods
            self._cleanup_dock_widgets()
            
            # Safely unset map tools
            self._cleanup_map_tools()
            
            # Remove menu items safely
            self._cleanup_menu_items()
            
            # Remove dock widgets from interface
            self._cleanup_interface_widgets()
            
            # Remove toolbar icons
            self._cleanup_toolbar()
            
        except Exception as e:
            # Catch any unexpected errors during unload to prevent hanging
            try:
                print(f"LatLonTools unload error (safely ignored): {str(e)}")
            except:
                pass  # Even print might fail during shutdown

        # Clear references
        self._clear_references()
        
    def _cleanup_dock_widgets(self):
        """Cleanup dock widgets with their custom cleanup methods"""
        if hasattr(self.plugin.zoomToDialog, 'cleanup'):
            self.plugin.zoomToDialog.cleanup()
        if hasattr(self.plugin.multiZoomDialog, 'cleanup'):
            self.plugin.multiZoomDialog.cleanup()
        
        # Clear any potential circular references
        if hasattr(self.plugin, 'zoomToDialog') and self.plugin.zoomToDialog:
            try:
                self.plugin.zoomToDialog.removeMarker()
            except (RuntimeError, AttributeError):
                pass
        if hasattr(self.plugin, 'multiZoomDialog') and self.plugin.multiZoomDialog:
            try:
                self.plugin.multiZoomDialog.removeMarkers()
            except (RuntimeError, AttributeError):
                pass
                
    def _cleanup_map_tools(self):
        """Safely unset map tools"""
        try:
            if self.plugin.mapTool:
                self.plugin.canvas.unsetMapTool(self.plugin.mapTool)
        except (RuntimeError, AttributeError):
            pass
        try:
            if self.plugin.showMapTool:
                self.plugin.canvas.unsetMapTool(self.plugin.showMapTool)
        except (RuntimeError, AttributeError):
            pass
            
    def _cleanup_menu_items(self):
        """Remove menu items safely"""
        menu_actions = [
            self.plugin.copyAction, self.plugin.copyExtentsAction, self.plugin.externMapAction,
            self.plugin.zoomToAction, self.plugin.multiZoomToAction, self.plugin.convertCoordinatesAction,
            self.plugin.conversionsAction, self.plugin.settingsAction, self.plugin.helpAction, 
            self.plugin.digitizeAction
        ]
        for action in menu_actions:
            try:
                self.plugin.iface.removePluginMenu('Lat Lon Tools', action)
            except (RuntimeError, AttributeError):
                pass
                
    def _cleanup_interface_widgets(self):
        """Remove dock widgets from interface"""
        try:
            self.plugin.iface.removeDockWidget(self.plugin.zoomToDialog)
        except (RuntimeError, AttributeError):
            pass
        try:
            self.plugin.iface.removeDockWidget(self.plugin.multiZoomDialog)
        except (RuntimeError, AttributeError):
            pass
            
    def _cleanup_toolbar(self):
        """Remove toolbar icons and toolbar"""
        toolbar_actions = [
            self.plugin.copyAction, self.plugin.copyExtentToolbar, self.plugin.zoomToAction,
            self.plugin.externMapAction, self.plugin.multiZoomToAction, 
            self.plugin.convertCoordinatesAction, self.plugin.digitizeAction
        ]
        for action in toolbar_actions:
            try:
                self.plugin.iface.removeToolBarIcon(action)
            except (RuntimeError, AttributeError):
                pass
        
        try:
            del self.plugin.toolbar
        except (RuntimeError, AttributeError):
            pass
            
        # Remove convert coordinate dialog safely
        if hasattr(self.plugin, 'convertCoordinateDialog') and self.plugin.convertCoordinateDialog:
            try:
                self.plugin.iface.removeDockWidget(self.plugin.convertCoordinateDialog)
                self.plugin.convertCoordinateDialog = None
            except (RuntimeError, AttributeError):
                pass
                
    def _clear_references(self):
        """Clear object references"""
        self.plugin.zoomToDialog = None
        self.plugin.multiZoomDialog = None


class SafeDockWidgetCleanup:
    """
    Provides safe cleanup functionality for dock widgets
    """
    
    @staticmethod
    def cleanup_zoom_dialog(zoom_dialog):
        """Properly cleanup ZoomToLatLon dialog resources"""
        # Remove markers from canvas
        zoom_dialog.removeMarker()
        
        # Disconnect canvas signals to prevent hanging - only if canvas exists
        if zoom_dialog.canvas is not None:
            try:
                zoom_dialog.canvas.destinationCrsChanged.disconnect(zoom_dialog.crsChanged)
            except (TypeError, RuntimeError, AttributeError):
                # Signal already disconnected or object destroyed
                pass
                
        # Remove rubber bands from canvas completely
        if hasattr(zoom_dialog, 'marker') and zoom_dialog.marker and zoom_dialog.canvas is not None:
            zoom_dialog.marker.reset(QgsWkbTypes.PointGeometry)
            # Remove from canvas scene
            scene = zoom_dialog.canvas.scene()
            if scene and zoom_dialog.marker in scene.items():
                scene.removeItem(zoom_dialog.marker)
                
        if hasattr(zoom_dialog, 'line_marker') and zoom_dialog.line_marker and zoom_dialog.canvas is not None:
            zoom_dialog.line_marker.reset(QgsWkbTypes.LineGeometry)
            # Remove from canvas scene
            scene = zoom_dialog.canvas.scene()
            if scene and zoom_dialog.line_marker in scene.items():
                scene.removeItem(zoom_dialog.line_marker)