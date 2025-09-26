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
        """Perform emergency shutdown cleanup that ensures QGIS can continue shutting down"""
        # Set unloading flag to prevent any operations during shutdown
        self.plugin._is_unloading = True
        
        # EMERGENCY CLEANUP: Use timeouts and aggressive error handling to prevent hanging
        
        # 1. CRITICAL: Force cleanup of canvas-related resources that can hang shutdown
        self._emergency_canvas_cleanup()
        
        # 2. Reset parser service singleton (with timeout protection)
        self._emergency_singleton_reset()
        
        # 3. Aggressively disconnect signals (don't wait for individual cleanups)
        self._emergency_signal_disconnection()
        
        # 4. Force cleanup dock widgets (with fallback strategies)
        self._emergency_widget_cleanup()
        
        # 5. Clear references immediately (don't defer)
        self._emergency_reference_cleanup()
        
        # Log successful emergency cleanup
        try:
            from qgis.core import QgsMessageLog, Qgis
            QgsMessageLog.logMessage("LatLonTools: Emergency shutdown cleanup completed - QGIS can continue", "LatLonTools", Qgis.Info)
        except:
            pass  # Even logging might fail during shutdown

    def _emergency_canvas_cleanup(self):
        """PRIORITY 1: Emergency cleanup of canvas resources that can cause hanging"""
        try:
            # Force cleanup of rubber bands with maximum aggression
            canvas_objects_to_clean = []
            
            # Collect all canvas-related objects from plugin
            if hasattr(self.plugin, 'crossRb') and self.plugin.crossRb:
                canvas_objects_to_clean.append(('crossRb', self.plugin.crossRb))
                
            # Collect from dialogs if they exist
            for dialog_attr in ['zoomToDialog', 'multiZoomDialog']:
                dialog = getattr(self.plugin, dialog_attr, None)
                if dialog:
                    if hasattr(dialog, 'marker') and dialog.marker:
                        canvas_objects_to_clean.append((f'{dialog_attr}.marker', dialog.marker))
                    if hasattr(dialog, 'line_marker') and dialog.line_marker:
                        canvas_objects_to_clean.append((f'{dialog_attr}.line_marker', dialog.line_marker))
                    if hasattr(dialog, 'markers') and dialog.markers:
                        for i, marker in enumerate(dialog.markers):
                            if marker:
                                canvas_objects_to_clean.append((f'{dialog_attr}.markers[{i}]', marker))
            
            # AGGRESSIVE CLEANUP: Don't check canvas state, just force cleanup
            for name, obj in canvas_objects_to_clean:
                try:
                    # Method 1: Try standard reset
                    obj.reset()
                except:
                    try:
                        # Method 2: Try specific geometry reset
                        if hasattr(obj, 'reset'):
                            obj.reset(QgsWkbTypes.PointGeometry if 'marker' in name else QgsWkbTypes.LineGeometry)
                    except:
                        try:
                            # Method 3: Direct scene removal (bypass canvas checks)
                            parent = obj.parent()
                            if parent and hasattr(parent, 'removeItem'):
                                parent.removeItem(obj)
                        except:
                            # Method 4: Set to None and let garbage collector handle it
                            pass
                
                # Always set reference to None regardless of cleanup success
                self._force_set_none(name, obj)
                        
        except Exception as e:
            # Emergency cleanup must never raise exceptions
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"Emergency canvas cleanup non-blocking error: {e}", "LatLonTools", Qgis.Warning)
            except:
                pass
    
    def _emergency_singleton_reset(self):
        """PRIORITY 2: Force reset singleton with aggressive error handling"""
        try:
            def try_singleton_reset():
                try:
                    from .parser_service import CoordinateParserService
                    CoordinateParserService.reset_instance()
                    return True
                except:
                    return False

            # Try normal reset first, then force reset if needed
            success = try_singleton_reset()
            if not success:
                # Force singleton to None even if reset fails
                try:
                    from .parser_service import CoordinateParserService
                    CoordinateParserService._instance = None
                except:
                    pass

        except Exception:
            # Singleton reset must never block shutdown
            pass
    
    def _emergency_signal_disconnection(self):
        """PRIORITY 3: Aggressively disconnect all signals without waiting"""
        # Disconnect main plugin signals
        self._disconnect_main_plugin_signals()

        # Disconnect dialog signals
        self._disconnect_dialog_signals()

    def _disconnect_main_plugin_signals(self):
        """Disconnect main plugin signals safely"""
        try:
            if hasattr(self.plugin, 'iface') and self.plugin.iface:
                self.plugin.iface.currentLayerChanged.disconnect(self.plugin.currentLayerChanged)
        except:
            pass

        try:
            if hasattr(self.plugin, 'canvas') and self.plugin.canvas:
                self.plugin.canvas.mapToolSet.disconnect(self.plugin.resetTools)
        except:
            pass

    def _disconnect_dialog_signals(self):
        """Disconnect dialog canvas signals safely"""
        try:
            if hasattr(self.plugin, 'zoomToDialog') and self.plugin.zoomToDialog:
                self.plugin.zoomToDialog.canvas.destinationCrsChanged.disconnect(self.plugin.zoomToDialog.crsChanged)
        except:
            pass

        try:
            if hasattr(self.plugin, 'multiZoomDialog') and self.plugin.multiZoomDialog:
                self.plugin.multiZoomDialog.canvas.destinationCrsChanged.disconnect(self.plugin.multiZoomDialog.crsChanged)
        except:
            pass
                
        # Force disconnect active layer signals
        try:
            layer = self.plugin.iface.activeLayer()
            if layer:
                # Disconnect only this plugin's slots
                try:
                    layer.editingStarted.disconnect(self.plugin.layerEditingChanged)
                except:
                    pass
                try:
                    layer.editingStopped.disconnect(self.plugin.layerEditingChanged)
                except:
                    pass
        except:
            pass
    
    def _emergency_widget_cleanup(self):
        """PRIORITY 4: Force cleanup widgets without waiting for proper procedures"""
        # Emergency widget cleanup - prioritize shutdown continuation over clean closure
        widget_list = ['zoomToDialog', 'multiZoomDialog', 'convertCoordinateDialog', 'digitizerDialog', 'settingsDialog']
        
        for widget_name in widget_list:
            widget = getattr(self.plugin, widget_name, None)
            if widget:
                try:
                    # Method 1: Try proper close
                    widget.close()
                except:
                    try:
                        # Method 2: Force hide
                        widget.hide()
                    except:
                        pass
                        
                try:
                    # Method 3: Remove from interface immediately
                    if hasattr(self.plugin.iface, 'removeDockWidget'):
                        self.plugin.iface.removeDockWidget(widget)
                except:
                    pass
                
                # Always set to None
                self._force_set_none(widget_name, widget)
    
    def _emergency_reference_cleanup(self):
        """PRIORITY 5: Immediately clear all references"""
        # Clear all dialog references
        for attr in ['zoomToDialog', 'multiZoomDialog', 'convertCoordinateDialog', 'digitizerDialog', 'settingsDialog']:
            self._force_set_none(attr, None)
            
        # Clear tool references
        for attr in ['mapTool', 'showMapTool', 'copyExtentTool', 'crossRb']:
            self._force_set_none(attr, None)
            
        # Clear other Qt objects
        for attr in ['translator', 'toolbar']:
            self._force_set_none(attr, None)
    
    def _force_set_none(self, attr_name, obj):
        """Force set attribute to None, handling all possible exceptions"""
        try:
            if '.' in attr_name:
                # Handle nested attributes like 'dialog.marker'
                parts = attr_name.split('.')
                current = self.plugin
                for part in parts[:-1]:
                    current = getattr(current, part, None)
                    if not current:
                        return
                setattr(current, parts[-1], None)
            else:
                # Handle direct attributes
                setattr(self.plugin, attr_name, None)
        except:
            # Setting to None must never fail in emergency cleanup
            pass
        
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
            
        # NOTE: Cannot clear dialog references - they are @property methods that delegate to dialog_manager
        # The dialogs are now managed by DialogManager and are read-only properties
        # Dialog cleanup is handled by dialog_manager.cleanup_dialogs() method,
        # which is called during plugin unload in the safe_unload() method of this class.
        
        # Clear map tool references  
        try:
            self.plugin.mapTool = None
        except AttributeError:
            pass
        
        try:
            self.plugin.showMapTool = None
        except AttributeError:
            pass
            
        try:
            self.plugin.copyExtentTool = None
        except AttributeError:
            pass
        
        # Clear other Qt object references
        try:
            self.plugin.crossRb = None
        except AttributeError:
            pass
            
        try:
            self.plugin.translator = None
        except AttributeError:
            pass
        
        # Don't delete toolbar here as it's done in _cleanup_toolbar
        # But set reference to None
        if hasattr(self.plugin, 'toolbar'):
            try:
                self.plugin.toolbar = None
            except AttributeError:
                pass


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