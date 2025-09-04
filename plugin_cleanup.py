"""
Plugin Cleanup Module
Provides safe cleanup functionality to prevent QGIS hanging during plugin unload
"""

from qgis.core import QgsWkbTypes, QgsMessageLog, Qgis, QgsApplication
from qgis.PyQt.QtCore import QCoreApplication

try:
    from .latLonFunctions import UnloadLatLonFunctions
except ImportError:
    UnloadLatLonFunctions = None


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
            # Disconnect main plugin signals first
            self._disconnect_main_signals()
            
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
            
            # Remove processing provider
            self._cleanup_processing()
            
        except Exception as e:
            # Catch any unexpected errors during unload to prevent hanging
            try:
                QgsMessageLog.logMessage(f"LatLonTools unload error (safely ignored): {str(e)}", "LatLonTools", Qgis.Info)
            except:
                pass  # Even logging might fail during shutdown

        # Clear references
        self._clear_references()
        
    def _disconnect_main_signals(self):
        """Disconnect main plugin signals to prevent orphaned connections"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        try:
            # Disconnect main canvas and interface signals - check existence
            if hasattr(self.plugin, 'iface') and self.plugin.iface:
                try:
                    self.plugin.iface.currentLayerChanged.disconnect(self.plugin.currentLayerChanged)
                except (RuntimeError, AttributeError, TypeError):
                    pass
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        try:
            if hasattr(self.plugin, 'canvas') and self.plugin.canvas:
                try:
                    self.plugin.canvas.mapToolSet.disconnect(self.plugin.resetTools)
                except (RuntimeError, AttributeError, TypeError):
                    pass
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Disconnect any current layer editing signals - check if iface is valid
        try:
            if hasattr(self.plugin, 'iface') and self.plugin.iface:
                layer = self.plugin.iface.activeLayer()
                if layer is not None:
                    try:
                        layer.editingStarted.disconnect(self.plugin.layerEditingChanged)
                        layer.editingStopped.disconnect(self.plugin.layerEditingChanged)
                    except (RuntimeError, AttributeError, TypeError):
                        pass
        except (RuntimeError, AttributeError, TypeError):
            pass
        
    def _cleanup_dock_widgets(self):
        """Cleanup dock widgets with their custom cleanup methods"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
        
        # Enhanced cleanup for ZoomToLatLon dialog
        if hasattr(self.plugin, 'zoomToDialog') and self.plugin.zoomToDialog:
            try:
                # Call enhanced cleanup if available
                if hasattr(self.plugin.zoomToDialog, 'cleanup'):
                    self.plugin.zoomToDialog.cleanup()
                else:
                    # Fallback cleanup
                    SafeDockWidgetCleanup.cleanup_zoom_dialog(self.plugin.zoomToDialog)
            except (RuntimeError, AttributeError, TypeError):
                pass
                
        # Enhanced cleanup for MultiZoom dialog
        if hasattr(self.plugin, 'multiZoomDialog') and self.plugin.multiZoomDialog:
            try:
                # Call enhanced cleanup if available
                if hasattr(self.plugin.multiZoomDialog, 'cleanup'):
                    self.plugin.multiZoomDialog.cleanup()
                else:
                    # Fallback cleanup
                    SafeDockWidgetCleanup.cleanup_multizoom_dialog(self.plugin.multiZoomDialog)
            except (RuntimeError, AttributeError, TypeError):
                pass
                
        # Cleanup coordinate converter dialog
        if hasattr(self.plugin, 'convertCoordinateDialog') and self.plugin.convertCoordinateDialog:
            try:
                if hasattr(self.plugin.convertCoordinateDialog, 'cleanup'):
                    self.plugin.convertCoordinateDialog.cleanup()
                else:
                    # Basic cleanup
                    try:
                        if hasattr(self.plugin, 'iface') and self.plugin.iface:
                            self.plugin.iface.removeDockWidget(self.plugin.convertCoordinateDialog)
                        self.plugin.convertCoordinateDialog.close()
                        self.plugin.convertCoordinateDialog.deleteLater()
                    except (RuntimeError, AttributeError, TypeError):
                        pass
            except (RuntimeError, AttributeError, TypeError):
                pass
                
        # Cleanup digitizer dialog
        if hasattr(self.plugin, 'digitizerDialog') and self.plugin.digitizerDialog:
            try:
                self.plugin.digitizerDialog.close()
                self.plugin.digitizerDialog.deleteLater()
            except (RuntimeError, AttributeError, TypeError):
                pass
                
        # Cleanup settings dialog
        if hasattr(self.plugin, 'settingsDialog') and self.plugin.settingsDialog:
            try:
                self.plugin.settingsDialog.close()
                self.plugin.settingsDialog.deleteLater()
            except (RuntimeError, AttributeError, TypeError):
                pass
                
    def _cleanup_map_tools(self):
        """Safely unset map tools"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        try:
            if hasattr(self.plugin, 'mapTool') and self.plugin.mapTool:
                if hasattr(self.plugin, 'canvas') and self.plugin.canvas:
                    self.plugin.canvas.unsetMapTool(self.plugin.mapTool)
                self.plugin.mapTool = None
        except (RuntimeError, AttributeError, TypeError):
            pass
        try:
            if hasattr(self.plugin, 'showMapTool') and self.plugin.showMapTool:
                if hasattr(self.plugin, 'canvas') and self.plugin.canvas:
                    self.plugin.canvas.unsetMapTool(self.plugin.showMapTool)
                self.plugin.showMapTool = None
        except (RuntimeError, AttributeError, TypeError):
            pass
        try:
            if hasattr(self.plugin, 'copyExtentTool') and self.plugin.copyExtentTool:
                if hasattr(self.plugin, 'canvas') and self.plugin.canvas:
                    self.plugin.canvas.unsetMapTool(self.plugin.copyExtentTool)
                self.plugin.copyExtentTool = None
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Clean up crossRb rubber band
        try:
            if hasattr(self.plugin, 'crossRb') and self.plugin.crossRb:
                try:
                    self.plugin.crossRb.reset(QgsWkbTypes.LineGeometry)
                    if hasattr(self.plugin, 'canvas') and self.plugin.canvas:
                        scene = self.plugin.canvas.scene()
                        if scene and self.plugin.crossRb in scene.items():
                            scene.removeItem(self.plugin.crossRb)
                except (RuntimeError, AttributeError, TypeError):
                    pass
                self.plugin.crossRb = None
        except (RuntimeError, AttributeError, TypeError):
            pass
            
    def _cleanup_menu_items(self):
        """Remove menu items safely"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        menu_actions = [
            'copyAction', 'copyExtentsAction', 'externMapAction',
            'zoomToAction', 'multiZoomToAction', 'convertCoordinatesAction',
            'conversionsAction', 'settingsAction', 'helpAction', 'digitizeAction'
        ]
        for action_name in menu_actions:
            try:
                if hasattr(self.plugin, action_name):
                    action = getattr(self.plugin, action_name, None)
                    if action and hasattr(self.plugin, 'iface') and self.plugin.iface:
                        self.plugin.iface.removePluginMenu('Lat Lon Tools', action)
            except (RuntimeError, AttributeError, TypeError):
                pass
                
    def _cleanup_interface_widgets(self):
        """Remove dock widgets from interface"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        # Remove ZoomToLatLon dialog
        try:
            if hasattr(self.plugin, 'zoomToDialog') and self.plugin.zoomToDialog:
                if hasattr(self.plugin, 'iface') and self.plugin.iface:
                    self.plugin.iface.removeDockWidget(self.plugin.zoomToDialog)
                # Force close and delete the widget
                self.plugin.zoomToDialog.close()
                self.plugin.zoomToDialog.deleteLater()
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Remove MultiZoom dialog
        try:
            if hasattr(self.plugin, 'multiZoomDialog') and self.plugin.multiZoomDialog:
                if hasattr(self.plugin, 'iface') and self.plugin.iface:
                    self.plugin.iface.removeDockWidget(self.plugin.multiZoomDialog)
                # Force close and delete the widget
                self.plugin.multiZoomDialog.close() 
                self.plugin.multiZoomDialog.deleteLater()
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Remove coordinate converter dialog
        try:
            if hasattr(self.plugin, 'convertCoordinateDialog') and self.plugin.convertCoordinateDialog:
                if hasattr(self.plugin, 'iface') and self.plugin.iface:
                    self.plugin.iface.removeDockWidget(self.plugin.convertCoordinateDialog)
                # Force close and delete the widget
                self.plugin.convertCoordinateDialog.close()
                self.plugin.convertCoordinateDialog.deleteLater()
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Close digitizer dialog
        try:
            if hasattr(self.plugin, 'digitizerDialog') and self.plugin.digitizerDialog:
                self.plugin.digitizerDialog.close()
                self.plugin.digitizerDialog.deleteLater()
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Close settings dialog
        try:
            if hasattr(self.plugin, 'settingsDialog') and self.plugin.settingsDialog:
                self.plugin.settingsDialog.close()
                self.plugin.settingsDialog.deleteLater()
        except (RuntimeError, AttributeError, TypeError):
            pass
            
    def _cleanup_toolbar(self):
        """Remove toolbar icons and toolbar"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        toolbar_actions = [
            'copyAction', 'copyExtentToolbar', 'zoomToAction',
            'externMapAction', 'multiZoomToAction', 
            'convertCoordinatesAction', 'digitizeAction', 'settingsAction'
        ]
        for action_name in toolbar_actions:
            try:
                if hasattr(self.plugin, action_name):
                    action = getattr(self.plugin, action_name, None)
                    if action and hasattr(self.plugin, 'iface') and self.plugin.iface:
                        self.plugin.iface.removeToolBarIcon(action)
            except (RuntimeError, AttributeError, TypeError):
                pass
        
        # Remove and delete toolbar
        try:
            if hasattr(self.plugin, 'toolbar') and self.plugin.toolbar:
                self.plugin.toolbar.deleteLater()
                del self.plugin.toolbar
        except (RuntimeError, AttributeError, TypeError):
            pass
            
        # Remove translator if it exists
        try:
            if hasattr(self.plugin, 'translator') and self.plugin.translator:
                QCoreApplication.removeTranslator(self.plugin.translator)
        except (RuntimeError, AttributeError, TypeError, ImportError):
            pass
            
    def _cleanup_processing(self):
        """Remove processing provider"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        try:
            if hasattr(self.plugin, 'provider') and self.plugin.provider:
                QgsApplication.processingRegistry().removeProvider(self.plugin.provider)
        except (RuntimeError, AttributeError, ImportError, TypeError):
            pass
            
        # Unload functions if available
        try:
            if UnloadLatLonFunctions is not None:
                UnloadLatLonFunctions()
        except (RuntimeError, AttributeError, TypeError):
            pass
            
    def _clear_references(self):
        """Clear object references"""
        # Check if plugin object still exists
        if not hasattr(self, 'plugin') or not self.plugin:
            return
            
        # Clear dialog references - set to None even if they don't exist
        self.plugin.zoomToDialog = None
        self.plugin.multiZoomDialog = None
        self.plugin.settingsDialog = None
        self.plugin.convertCoordinateDialog = None
        self.plugin.digitizerDialog = None
        
        # Clear map tool references  
        self.plugin.mapTool = None
        self.plugin.showMapTool = None
        self.plugin.copyExtentTool = None
        
        # Clear other Qt object references
        self.plugin.crossRb = None
        self.plugin.translator = None
        
        # Don't delete toolbar here as it's done in _cleanup_toolbar
        # But set reference to None
        if hasattr(self.plugin, 'toolbar'):
            self.plugin.toolbar = None


class SafeDockWidgetCleanup:
    """
    Provides safe cleanup functionality for dock widgets
    """
    
    @staticmethod
    def cleanup_zoom_dialog(zoom_dialog):
        """Properly cleanup ZoomToLatLon dialog resources"""
        # Check if dialog object exists and is valid
        if not zoom_dialog:
            return
            
        # Remove markers from canvas
        try:
            if hasattr(zoom_dialog, 'removeMarker') and callable(zoom_dialog.removeMarker):
                zoom_dialog.removeMarker()
        except (RuntimeError, AttributeError, TypeError):
            pass
        
        # Disconnect canvas signals to prevent hanging - only if canvas exists
        if hasattr(zoom_dialog, 'canvas') and zoom_dialog.canvas is not None:
            try:
                if hasattr(zoom_dialog, 'crsChanged') and callable(zoom_dialog.crsChanged):
                    zoom_dialog.canvas.destinationCrsChanged.disconnect(zoom_dialog.crsChanged)
            except (TypeError, RuntimeError, AttributeError):
                # Signal already disconnected or object destroyed
                pass
                
        # Remove rubber bands from canvas completely
        if hasattr(zoom_dialog, 'marker') and zoom_dialog.marker:
            try:
                zoom_dialog.marker.reset(QgsWkbTypes.PointGeometry)
                # Remove from canvas scene if canvas still exists
                if hasattr(zoom_dialog, 'canvas') and zoom_dialog.canvas is not None:
                    try:
                        scene = zoom_dialog.canvas.scene()
                        if scene and zoom_dialog.marker in scene.items():
                            scene.removeItem(zoom_dialog.marker)
                    except (RuntimeError, AttributeError, TypeError):
                        pass
                zoom_dialog.marker = None
            except (RuntimeError, AttributeError, TypeError):
                pass
                
        if hasattr(zoom_dialog, 'line_marker') and zoom_dialog.line_marker:
            try:
                zoom_dialog.line_marker.reset(QgsWkbTypes.LineGeometry)
                # Remove from canvas scene if canvas still exists
                if hasattr(zoom_dialog, 'canvas') and zoom_dialog.canvas is not None:
                    try:
                        scene = zoom_dialog.canvas.scene()
                        if scene and zoom_dialog.line_marker in scene.items():
                            scene.removeItem(zoom_dialog.line_marker)
                    except (RuntimeError, AttributeError, TypeError):
                        pass
                zoom_dialog.line_marker = None
            except (RuntimeError, AttributeError, TypeError):
                pass
                
    @staticmethod
    def cleanup_multizoom_dialog(multizoom_dialog):
        """Properly cleanup MultiZoom dialog resources"""
        # Check if dialog object exists and is valid
        if not multizoom_dialog:
            return
            
        # Remove markers from canvas
        try:
            if hasattr(multizoom_dialog, 'removeMarkers') and callable(multizoom_dialog.removeMarkers):
                multizoom_dialog.removeMarkers()
        except (RuntimeError, AttributeError, TypeError):
            pass
        
        # Disconnect canvas signals to prevent hanging
        if hasattr(multizoom_dialog, 'canvas') and multizoom_dialog.canvas is not None:
            try:
                if hasattr(multizoom_dialog, 'crsChanged') and callable(multizoom_dialog.crsChanged):
                    multizoom_dialog.canvas.destinationCrsChanged.disconnect(multizoom_dialog.crsChanged)
            except (TypeError, RuntimeError, AttributeError):
                # Signal already disconnected or object destroyed
                pass
        
        # Disconnect capture tool signals
        if hasattr(multizoom_dialog, 'captureCoordinate') and multizoom_dialog.captureCoordinate:
            try:
                if hasattr(multizoom_dialog, 'capturedPoint') and callable(multizoom_dialog.capturedPoint):
                    multizoom_dialog.captureCoordinate.capturePoint.disconnect(multizoom_dialog.capturedPoint)
                if hasattr(multizoom_dialog, 'stopCapture') and callable(multizoom_dialog.stopCapture):
                    multizoom_dialog.captureCoordinate.captureStopped.disconnect(multizoom_dialog.stopCapture)
            except (TypeError, RuntimeError, AttributeError):
                pass
                
        # Clean up rubber band markers
        if hasattr(multizoom_dialog, 'markers') and multizoom_dialog.markers:
            try:
                for marker in multizoom_dialog.markers:
                    if marker:
                        try:
                            marker.reset()
                            # Remove from canvas scene if canvas still exists
                            if hasattr(multizoom_dialog, 'canvas') and multizoom_dialog.canvas is not None:
                                try:
                                    scene = multizoom_dialog.canvas.scene()
                                    if scene and marker in scene.items():
                                        scene.removeItem(marker)
                                except (RuntimeError, AttributeError, TypeError):
                                    pass
                        except (RuntimeError, AttributeError, TypeError):
                            pass
                multizoom_dialog.markers = []
            except (RuntimeError, AttributeError, TypeError):
                pass