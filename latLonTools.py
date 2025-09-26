"""
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from typing import Optional, TYPE_CHECKING
from qgis.PyQt.QtCore import Qt, QTimer, QUrl, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QApplication, QToolButton
from qgis.core import (
    Qgis, QgsCoordinateTransform, QgsVectorLayer, QgsRectangle, 
    QgsPoint, QgsPointXY, QgsGeometry, QgsWkbTypes, QgsProject, 
    QgsApplication, QgsSettings, QgsCoordinateReferenceSystem
)
from qgis.gui import QgsRubberBand
import processing

if TYPE_CHECKING:
    from qgis.gui import QgsInterface
    from .settings import SettingsWidget
    from .zoomToLatLon import ZoomToLatLon  
    from .multizoom import MultiZoomWidget

from .latLonFunctions import InitLatLonFunctions, UnloadLatLonFunctions
from .zoomToLatLon import ZoomToLatLon
from .multizoom import MultiZoomWidget
from .settings import SettingsWidget, settings
from .provider import LatLonToolsProvider
from .util import epsg4326, tr
from .captureExtent import getExtentString
from .extent_operations import ExtentOperations
from .dialog_manager import DialogManager
import os


class LatLonTools:
    digitizerDialog = None
    convertCoordinateDialog = None
    mapTool = None
    showMapTool = None
    copyExtentTool = None

    def __init__(self, iface: "QgsInterface") -> None:
        self.iface = iface
        self.canvas = iface.mapCanvas()
        # Initialize the plugin path directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        try:
            locale = QgsSettings().value("locale/userLocale", "en", type=str)[0:2]
        except Exception:
            locale = "en"
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'latlonTools_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.crossRb = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.crossRb.setColor(Qt.red)
        self.provider = LatLonToolsProvider()
        self.toolbar = self.iface.addToolBar(tr('Lat Lon Tools Toolbar'))
        self.toolbar.setObjectName('LatLonToolsToolbar')
        self.toolbar.setToolTip(tr('Lat Lon Tools Toolbar'))
        
        # Initialize focused service classes
        self.extent_operations = ExtentOperations(self.iface, settings)
        self.dialog_manager = DialogManager(self.iface, self.plugin_dir, self)
    
    # Dialog properties that delegate to dialog_manager for backward compatibility
    @property
    def settingsDialog(self) -> "SettingsWidget":
        """Get settings dialog from dialog manager."""
        return self.dialog_manager.settings_dialog
    
    @property
    def zoomToDialog(self) -> "ZoomToLatLon":
        """Get zoom to dialog from dialog manager."""
        return self.dialog_manager.zoom_to_dialog
    
    @property
    def multiZoomDialog(self) -> "MultiZoomWidget":
        """Get multi-zoom dialog from dialog manager."""
        return self.dialog_manager.multi_zoom_dialog

    def initGui(self):
        '''Initialize Lot Lon Tools GUI.'''
        # Settings dialog is now managed by dialog_manager (lazy loading)

        # Add Interface for Coordinate Capturing
        icon = QIcon(self.plugin_dir + "/images/copyicon.svg")
        self.copyAction = QAction(icon, tr("Copy/Display Coordinate"), self.iface.mainWindow())
        self.copyAction.setObjectName('latLonToolsCopy')
        self.copyAction.triggered.connect(self.startCapture)
        self.copyAction.setCheckable(True)
        self.toolbar.addAction(self.copyAction)
        self.iface.addPluginToMenu("Lat Lon Tools", self.copyAction)

        # Add Interface for External Map
        icon = QIcon(self.plugin_dir + "/images/mapicon.png")
        self.externMapAction = QAction(icon, tr("Show in External Map"), self.iface.mainWindow())
        self.externMapAction.setObjectName('latLonToolsExternalMap')
        self.externMapAction.triggered.connect(self.setShowMapTool)
        self.externMapAction.setCheckable(True)
        self.toolbar.addAction(self.externMapAction)
        self.iface.addPluginToMenu("Lat Lon Tools", self.externMapAction)

        # Add Interface for Zoom to Coordinate
        icon = QIcon(self.plugin_dir + "/images/zoomicon.svg")
        self.zoomToAction = QAction(icon, tr("Zoom To Coordinate"), self.iface.mainWindow())
        self.zoomToAction.setObjectName('latLonToolsZoom')
        self.zoomToAction.triggered.connect(self.showZoomToDialog)
        self.toolbar.addAction(self.zoomToAction)
        self.iface.addPluginToMenu('Lat Lon Tools', self.zoomToAction)

        # Zoom to dialog is now managed by dialog_manager (lazy loading)
        
        # Initialize and apply plugin enhancements after all dialogs are created
        try:
            from .plugin_enhancements import PluginEnhancements
            self._enhancements = PluginEnhancements(self, self.iface)
            self._enhancements.initialize_enhancements()
            self._enhancements.enhance_zoom_dialog(self.zoomToDialog)
        except ImportError as e:
            # Fallback if enhancements can't be loaded
            print(f"Warning: Could not load plugin enhancements: {e}")
            self._enhancements = None
        self.zoomToDialog.hide()

        # Add Interface for Multi point zoom
        icon = QIcon(self.plugin_dir + '/images/multizoom.svg')
        self.multiZoomToAction = QAction(icon, tr("Multi-location Zoom"), self.iface.mainWindow())
        self.multiZoomToAction.setObjectName('latLonToolsMultiZoom')
        self.multiZoomToAction.triggered.connect(self.multiZoomTo)
        self.toolbar.addAction(self.multiZoomToAction)
        self.iface.addPluginToMenu('Lat Lon Tools', self.multiZoomToAction)

        # Multi-zoom dialog is now managed by dialog_manager (lazy loading)

        menu = QMenu()
        menu.setObjectName('latLonToolsCopyExtents')

        # Add Interface for copying the canvas extent
        icon = QIcon(self.plugin_dir + "/images/copycanvas.svg")
        self.copyCanvasAction = menu.addAction(icon, tr('Copy Canvas Extent'), self.copyCanvas)
        self.copyCanvasAction.setObjectName('latLonToolsCopyCanvasExtent')

        # Add Interface for copying an interactive extent
        icon = QIcon(self.plugin_dir + "/images/copyextent.svg")
        self.copyExtentAction = menu.addAction(icon, tr('Copy Selected Area Extent'), self.copyExtent)
        self.copyExtentAction.setCheckable(True)
        self.copyExtentAction.setObjectName('latLonToolsCopySelectedAreaExtent')

        # Add Interface for copying a layer extent
        icon = QIcon(self.plugin_dir + "/images/copylayerextent.svg")
        self.copyLayerExtentAction = menu.addAction(icon, tr('Copy Layer Extent'), self.copyLayerExtent)
        self.copyLayerExtentAction.setObjectName('latLonToolsCopyLayerExtent')

        # Add Interface for copying the extent of selected features
        icon = QIcon(self.plugin_dir + "/images/copyselectedlayerextent.svg")
        self.copySelectedFeaturesExtentAction = menu.addAction(icon, tr('Copy Selected Features Extent'), self.copySelectedFeaturesExtent)
        self.copySelectedFeaturesExtentAction.setObjectName('latLonToolsCopySelectedFeaturesExtent')
        
        # Add the copy extent tools to the menu
        icon = QIcon(self.plugin_dir + '/images/copylayerextent.svg')
        self.copyExtentsAction = QAction(icon, tr('Copy Extents to Clipboard'), self.iface.mainWindow())
        self.copyExtentsAction.setMenu(menu)
        self.iface.addPluginToMenu('Lat Lon Tools', self.copyExtentsAction)

        # Add the copy extent tools to the toolbar
        self.copyExtentButton = QToolButton()
        self.copyExtentButton.setMenu(menu)
        self.copyExtentButton.setDefaultAction(self.copyCanvasAction)
        self.copyExtentButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.copyExtentButton.triggered.connect(self.copyExtentTriggered)
        self.copyExtentToolbar = self.toolbar.addWidget(self.copyExtentButton)
        self.copyExtentToolbar.setObjectName('latLonToolsCopyExtent')

        # Create the coordinate converter menu
        icon = QIcon(':/images/themes/default/mIconProjectionEnabled.svg')
        self.convertCoordinatesAction = QAction(icon, tr("Coordinate Conversion"), self.iface.mainWindow())
        self.convertCoordinatesAction.setObjectName('latLonToolsCoordinateConversion')
        self.convertCoordinatesAction.triggered.connect(self.convertCoordinatesTool)
        self.toolbar.addAction(self.convertCoordinatesAction)
        self.iface.addPluginToMenu("Lat Lon Tools", self.convertCoordinatesAction)

        # Create the conversions menu
        menu = QMenu()

        icon = QIcon(self.plugin_dir + '/images/field2geom.svg')
        action = menu.addAction(icon, tr("Fields to point layer"), self.field2geom)
        action.setObjectName('latLonToolsField2Geom')

        icon = QIcon(self.plugin_dir + '/images/geom2field.svg')
        action = menu.addAction(icon, tr("Point layer to fields"), self.geom2Field)
        action.setObjectName('latLonToolsGeom2Field')

        icon = QIcon(self.plugin_dir + '/images/geom2wkt.svg')
        action = menu.addAction(icon, tr("Geometry to WKT/JSON"), self.geom2wkt)
        action.setObjectName('latLonToolsGeom2Wkt')

        icon = QIcon(self.plugin_dir + '/images/wkt2layers.svg')
        action = menu.addAction(icon, tr("WKT attribute to layers"), self.wkt2layers)
        action.setObjectName('latLonToolsWkt2Layers')

        icon = QIcon(self.plugin_dir + '/images/pluscodes.svg')
        action = menu.addAction(icon, tr("Plus Codes to point layer"), self.PlusCodestoLayer)
        action.setObjectName('latLonToolsPlusCodes2Geom')

        action = menu.addAction(icon, tr("Point layer to Plus Codes"), self.toPlusCodes)
        action.setObjectName('latLonToolsGeom2PlusCodes')

        icon = QIcon(self.plugin_dir + '/images/mgrs2point.svg')
        action = menu.addAction(icon, tr("MGRS to point layer"), self.MGRStoLayer)
        action.setObjectName('latLonToolsMGRS2Geom')

        icon = QIcon(self.plugin_dir + '/images/point2mgrs.svg')
        action = menu.addAction(icon, tr("Point layer to MGRS"), self.toMGRS)
        action.setObjectName('latLonToolsGeom2MGRS')

        icon = QIcon(self.plugin_dir + '/images/ecef.png')
        action = menu.addAction(icon, tr("ECEF to Lat, Lon, Altitude"), self.ecef2lla)
        action.setObjectName('latLonToolsEcef2lla')

        action = menu.addAction(icon, tr("Lat, Lon, Altitude to ECEF"), self.lla2ecef)
        action.setObjectName('latLonToolsLla2ecef')

        self.conversionsAction = QAction(icon, tr("Conversions"), self.iface.mainWindow())
        self.conversionsAction.setMenu(menu)

        self.iface.addPluginToMenu('Lat Lon Tools', self.conversionsAction)

        # Add to Digitize Toolbar
        icon = QIcon(self.plugin_dir + '/images/latLonDigitize.svg')
        self.digitizeAction = QAction(icon, tr("Lat Lon Digitize"), self.iface.mainWindow())
        self.digitizeAction.setObjectName('latLonToolsDigitize')
        self.digitizeAction.triggered.connect(self.digitizeClicked)
        self.digitizeAction.setEnabled(False)
        self.toolbar.addAction(self.digitizeAction)
        self.iface.addPluginToMenu('Lat Lon Tools', self.digitizeAction)

        # Initialize the Settings Dialog Box
        settingsicon = QIcon(':/images/themes/default/mActionOptions.svg')
        self.settingsAction = QAction(settingsicon, tr("Settings"), self.iface.mainWindow())
        self.settingsAction.setObjectName('latLonToolsSettings')
        self.settingsAction.setToolTip(tr('Lat Lon Tools Settings'))
        self.settingsAction.triggered.connect(self.settings)
        self.toolbar.addAction(self.settingsAction)
        self.iface.addPluginToMenu('Lat Lon Tools', self.settingsAction)

        # Help
        icon = QIcon(self.plugin_dir + '/images/help.svg')
        self.helpAction = QAction(icon, tr("Help"), self.iface.mainWindow())
        self.helpAction.setObjectName('latLonToolsHelp')
        self.helpAction.triggered.connect(self.help)
        self.iface.addPluginToMenu('Lat Lon Tools', self.helpAction)

        self.iface.currentLayerChanged.connect(self.currentLayerChanged)
        self.canvas.mapToolSet.connect(self.resetTools)
        self.enableDigitizeTool()

        # Add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)
        InitLatLonFunctions()

    def resetTools(self, newtool, oldtool):
        '''Uncheck the Copy Lat Lon tool'''
        try:
            if self.mapTool and (oldtool is self.mapTool):
                self.copyAction.setChecked(False)
            if self.showMapTool and (oldtool is self.showMapTool):
                self.externMapAction.setChecked(False)
            if newtool is self.mapTool:
                self.copyAction.setChecked(True)
            if newtool is self.showMapTool:
                self.externMapAction.setChecked(True)
        except Exception:
            pass

    def unload(self):
        '''EMERGENCY UNLOAD: Ensures QGIS can continue shutdown even if plugin cleanup fails'''
        
        # CRITICAL: Set unloading flag immediately to prevent any new operations
        self._is_unloading = True
        
        # EMERGENCY TIMEOUT: Don't let plugin unload block QGIS shutdown indefinitely
        import threading
        import time
        
        cleanup_completed = threading.Event()
        
        def emergency_cleanup_with_timeout():
            """Run cleanup in a way that can be abandoned if it takes too long"""
            try:
                # Try enhanced cleanup first
                if hasattr(self, '_enhancements') and self._enhancements:
                    self._enhancements.safe_unload()
                else:
                    # Use emergency fallback cleanup
                    self._fallback_cleanup()
                cleanup_completed.set()
            except Exception as e:
                # ANY exception in cleanup must not prevent QGIS shutdown
                try:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(f"LatLonTools: Cleanup exception (non-fatal): {e}", "LatLonTools", Qgis.Warning)
                except:
                    pass
                cleanup_completed.set()
        
        # Start cleanup in a separate thread (not really, but conceptually)
        # Note: We can't use actual threading in QGIS plugins safely, so we'll use aggressive timeouts instead
        start_time = time.time()
        
        try:
            # Try enhanced cleanup with aggressive error handling
            if hasattr(self, '_enhancements') and self._enhancements:
                self._enhancements.safe_unload()
            else:
                self._fallback_cleanup()
                
        except Exception as e:
            # Cleanup failure cannot prevent QGIS shutdown
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"LatLonTools: Emergency unload completed despite error: {e}", "LatLonTools", Qgis.Info)
            except:
                pass
        
        # Final safety check - if cleanup took too long, warn but continue
        elapsed_time = time.time() - start_time
        if elapsed_time > 5.0:  # If cleanup took more than 5 seconds
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"LatLonTools: Cleanup took {elapsed_time:.1f}s but QGIS shutdown can continue", "LatLonTools", Qgis.Warning)
            except:
                pass
        
        # ABSOLUTE FINAL STEP: Force clear the unloading flag and main references
        try:
            self._is_unloading = False
            # Force clear essential references that could prevent garbage collection
            self._enhancements = None
            self.dialog_manager = None
        except:
            pass
            
    def _fallback_cleanup(self):
        """EMERGENCY fallback cleanup - prioritizes QGIS shutdown continuation"""
        
        # EMERGENCY MODE: Don't try to be perfect, just ensure QGIS can shutdown
        
        try:
            # PRIORITY 1: Emergency canvas cleanup (most likely to hang)
            self._emergency_canvas_force_cleanup()
            
            # PRIORITY 2: Force singleton reset (critical for shutdown)
            self._emergency_force_singleton_reset()
            
            # PRIORITY 3: Brute force signal disconnection
            self._emergency_disconnect_all_signals()
            
            # PRIORITY 4: Processing provider removal (can block shutdown)
            self._emergency_remove_processing()
            
        except Exception as e:
            # EMERGENCY CLEANUP CANNOT FAIL - it must let QGIS continue
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"Emergency fallback cleanup non-fatal error: {str(e)}", "LatLonTools", Qgis.Warning)
            except:
                pass  # Even logging can fail during emergency shutdown
        
        # FINAL: Force clear all references immediately
        self._emergency_clear_all_references()

    def _emergency_canvas_force_cleanup(self):
        """Force cleanup of canvas objects without any safety checks"""
        # Canvas objects that could hang shutdown
        canvas_cleanup_targets = [
            ('crossRb', lambda: self.crossRb.reset() if self.crossRb else None),
            ('zoomDialog.marker', lambda: self.zoomToDialog.marker.reset() if hasattr(self, 'zoomToDialog') and self.zoomToDialog and hasattr(self.zoomToDialog, 'marker') and self.zoomToDialog.marker else None),
            ('zoomDialog.line_marker', lambda: self.zoomToDialog.line_marker.reset() if hasattr(self, 'zoomToDialog') and self.zoomToDialog and hasattr(self.zoomToDialog, 'line_marker') and self.zoomToDialog.line_marker else None),
            ('multiZoom.markers', lambda: [m.reset() for m in self.multiZoomDialog.markers if m] if hasattr(self, 'multiZoomDialog') and self.multiZoomDialog and hasattr(self.multiZoomDialog, 'markers') and self.multiZoomDialog.markers else None),
        ]
        
        for name, cleanup_func in canvas_cleanup_targets:
            try:
                cleanup_func()
            except:
                # Individual cleanup failure cannot stop emergency cleanup
                pass
                
        # Force set canvas objects to None
        self._emergency_set_to_none('crossRb')
        if hasattr(self, 'zoomToDialog') and self.zoomToDialog:
            self._emergency_set_to_none('zoomToDialog.marker')  
            self._emergency_set_to_none('zoomToDialog.line_marker')
        if hasattr(self, 'multiZoomDialog') and self.multiZoomDialog:
            self._emergency_set_to_none('multiZoomDialog.markers')

    def _emergency_force_singleton_reset(self):
        """Force reset singletons without waiting or error checking"""
        try:
            from .parser_service import CoordinateParserService
            # Method 1: Try normal reset
            CoordinateParserService.reset_instance()
        except:
            try:
                # Method 2: Force singleton to None
                from .parser_service import CoordinateParserService
                CoordinateParserService._instance = None
            except:
                # Method 3: Import might fail during shutdown - that's okay
                pass

    def _emergency_disconnect_all_signals(self):
        """Brute force disconnect all known signals without error checking"""
        # Known problematic signal connections
        signal_targets = [
            ('iface.currentLayerChanged', lambda: self.iface.currentLayerChanged.disconnect()),
            ('canvas.mapToolSet', lambda: self.canvas.mapToolSet.disconnect()),
            ('layer.editingStarted', lambda: self.iface.activeLayer().editingStarted.disconnect() if self.iface.activeLayer() else None),
            ('layer.editingStopped', lambda: self.iface.activeLayer().editingStopped.disconnect() if self.iface.activeLayer() else None),
        ]
        
        for signal_name, disconnect_func in signal_targets:
            try:
                disconnect_func()
            except:
                # Signal disconnection failure cannot block shutdown
                pass

    def _emergency_remove_processing(self):
        """Force remove processing provider without safety checks"""
        try:
            if hasattr(self, 'provider') and self.provider:
                QgsApplication.processingRegistry().removeProvider(self.provider)
        except:
            pass
            
        try:
            UnloadLatLonFunctions()
        except:
            pass

    def _emergency_clear_all_references(self):
        """Force clear ALL object references immediately"""
        # List of all attributes that should be cleared
        attrs_to_clear = [
            'showMapTool', 'mapTool', 'copyExtentTool', 'crossRb', 
            'translator', 'toolbar', 'provider'
        ]
        
        for attr in attrs_to_clear:
            self._emergency_set_to_none(attr)
            
        # Note: Cannot clear dialog properties - they're managed by dialog_manager
        # But dialog_manager itself should be cleared
        self._emergency_set_to_none('dialog_manager')

    def _emergency_set_to_none(self, attr_name):
        """Force set any attribute to None, handling all possible exceptions"""
        try:
            if '.' in attr_name:
                # Handle nested attributes
                parts = attr_name.split('.')
                current = self
                for part in parts[:-1]:
                    current = getattr(current, part, None)
                    if not current:
                        return
                setattr(current, parts[-1], None)
            else:
                setattr(self, attr_name, None)
        except:
            # Setting to None must never fail in emergency mode
            pass

    def startCapture(self):
        '''Set the focus of the copy coordinate tool'''
        if self.mapTool is None:
            from .copyLatLonTool import CopyLatLonTool
            self.mapTool = CopyLatLonTool(self.settingsDialog, self.iface)
        self.canvas.setMapTool(self.mapTool)

    def copyExtentTriggered(self, action):
        self.copyExtentButton.setDefaultAction(action)
        
    def copyExtent(self):
        if self.copyExtentTool is None:
            from .captureExtent import CaptureExtentTool
            self.copyExtentTool = CaptureExtentTool(self.iface, self)
            self.copyExtentTool.setAction(self.copyExtentAction)
        self.canvas.setMapTool(self.copyExtentTool)

    def copyLayerExtent(self):
        layer = self.iface.activeLayer()
        if not layer or not layer.isValid():
            return
        if isinstance(layer, QgsVectorLayer) and (layer.featureCount() == 0):
            self.iface.messageBar().pushMessage("", tr("This layer has no features - A bounding box cannot be calculated."), level=Qgis.Warning, duration=4)
            return
        src_crs = layer.crs()
        extent = layer.extent()
        if settings.bBoxCrs == 0:
            dst_crs = epsg4326
        else:
            dst_crs = self.canvas.mapSettings().destinationCrs()
        
        outStr = getExtentString(extent, src_crs, dst_crs)
        clipboard = QApplication.clipboard()
        clipboard.setText(outStr)
        self.iface.messageBar().pushMessage("", "'{}' {}".format(outStr, tr('copied to the clipboard')), level=Qgis.Info, duration=4)

    def copySelectedFeaturesExtent(self):
        """Copy selected features extent to clipboard."""
        self.extent_operations.copy_selected_features_extent()

    def copyCanvas(self):
        extent = self.iface.mapCanvas().extent()
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        if settings.bBoxCrs == 0:
            dst_crs = epsg4326
        else:
            dst_crs = canvas_crs
        
        outStr = getExtentString(extent, canvas_crs, dst_crs)
        clipboard = QApplication.clipboard()
        clipboard.setText(outStr)
        self.iface.messageBar().pushMessage("", "'{}' {}".format(outStr, tr('copied to the clipboard')), level=Qgis.Info, duration=4)

    def setShowMapTool(self):
        '''Set the focus of the external map tool.'''
        if self.showMapTool is None:
            from .showOnMapTool import ShowOnMapTool
            self.showMapTool = ShowOnMapTool(self.iface)
        self.canvas.setMapTool(self.showMapTool)

    def showZoomToDialog(self):
        '''Show the zoom to docked widget.'''
        self.zoomToDialog.show()

    def convertCoordinatesTool(self):
        '''Display the Convert Coordinate Tool Dialog box.'''
        if self.convertCoordinateDialog is None:
            from .coordinateConverter import CoordinateConverterWidget
            self.convertCoordinateDialog = CoordinateConverterWidget(self, self.settingsDialog, self.iface, self.iface.mainWindow())
            self.convertCoordinateDialog.setFloating(True)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.convertCoordinateDialog)
        self.convertCoordinateDialog.show()

    def multiZoomTo(self):
        '''Display the Multi-zoom to dialog box'''
        self.multiZoomDialog.show()

    def field2geom(self):
        '''Convert layer containing a point x & y coordinate to a new point layer'''
        processing.execAlgorithmDialog('latlontools:field2geom', {})

    def geom2Field(self):
        '''Convert layer geometry to a text string'''
        processing.execAlgorithmDialog('latlontools:geom2field', {})

    def geom2wkt(self):
        '''Convert layer geometry to a text WKT/JSON string'''
        processing.execAlgorithmDialog('latlontools:geom2wkt', {})

    def wkt2layers(self):
        '''Convert a layer wkt attribute to new geometry layers'''
        processing.execAlgorithmDialog('latlontools:wkt2layers', {})

    def toMGRS(self):
        '''Display the to MGRS  dialog box'''
        processing.execAlgorithmDialog('latlontools:point2mgrs', {})

    def MGRStoLayer(self):
        '''Display the to MGRS  dialog box'''
        processing.execAlgorithmDialog('latlontools:mgrs2point', {})

    def toPlusCodes(self):
        processing.execAlgorithmDialog('latlontools:point2pluscodes', {})

    def PlusCodestoLayer(self):
        processing.execAlgorithmDialog('latlontools:pluscodes2point', {})

    def lla2ecef(self):
        processing.execAlgorithmDialog('latlontools:lla2ecef', {})

    def ecef2lla(self):
        processing.execAlgorithmDialog('latlontools:ecef2lla', {})

    def settings(self):
        '''Show the settings dialog box'''
        self.settingsDialog.show()

    def help(self):
        '''Display a help page'''
        import webbrowser
        url = QUrl.fromLocalFile(self.plugin_dir + "/index.html").toString()
        webbrowser.open(url, new=2)

    def settingsChanged(self):
        # Settings may have changed so we need to make sure the zoomToDialog window is configured properly
        self.zoomToDialog.configure()
        self.multiZoomDialog.settingsChanged()

    def zoomTo(self, src_crs, lat, lon):
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        transform = QgsCoordinateTransform(src_crs, canvas_crs, QgsProject.instance())
        x, y = transform.transform(float(lon), float(lat))

        # Center the map on the point and zoom appropriately
        center_point = QgsPointXY(x, y)
        
        # Get current scale to determine appropriate zoom level
        current_scale = self.canvas.scale()
        
        # If current scale is very large (zoomed out), zoom to a reasonable level
        # If already zoomed in, just center without changing scale too much
        if current_scale > 100000:  # Very zoomed out
            target_scale = 50000   # Zoom to 1:50,000 scale
        elif current_scale > 50000:  # Moderately zoomed out  
            target_scale = 25000   # Zoom to 1:25,000 scale
        else:  # Already zoomed in, just center
            target_scale = current_scale
        
        # Center and zoom to the target scale
        self.canvas.zoomScale(target_scale)
        self.canvas.setCenter(center_point)

        pt = QgsPointXY(x, y)
        self.highlight(pt)
        self.canvas.refresh()
        return pt

    def highlight(self, point):
        currExt = self.canvas.extent()

        leftPt = QgsPoint(currExt.xMinimum(), point.y())
        rightPt = QgsPoint(currExt.xMaximum(), point.y())

        topPt = QgsPoint(point.x(), currExt.yMaximum())
        bottomPt = QgsPoint(point.x(), currExt.yMinimum())

        horizLine = QgsGeometry.fromPolyline([leftPt, rightPt])
        vertLine = QgsGeometry.fromPolyline([topPt, bottomPt])

        self.crossRb.reset(QgsWkbTypes.LineGeometry)
        self.crossRb.setWidth(settings.markerWidth)
        self.crossRb.setColor(settings.markerColor)
        self.crossRb.addGeometry(horizLine, None)
        self.crossRb.addGeometry(vertLine, None)

        QTimer.singleShot(700, self.resetRubberbands)

    def resetRubberbands(self):
        if self.crossRb is not None:
            self.crossRb.reset(QgsWkbTypes.LineGeometry)

    def digitizeClicked(self):
        if self.digitizerDialog is None:
            from .digitizer import DigitizerWidget
            self.digitizerDialog = DigitizerWidget(self, self.iface, self.iface.mainWindow())
        self.digitizerDialog.show()

    def currentLayerChanged(self):
        layer = self.iface.activeLayer()
        if layer is not None:
            try:
                layer.editingStarted.disconnect(self.layerEditingChanged)
            except Exception:
                pass
            try:
                layer.editingStopped.disconnect(self.layerEditingChanged)
            except Exception:
                pass

            if isinstance(layer, QgsVectorLayer):
                layer.editingStarted.connect(self.layerEditingChanged)
                layer.editingStopped.connect(self.layerEditingChanged)

        self.enableDigitizeTool()

    def layerEditingChanged(self):
        self.enableDigitizeTool()

    def enableDigitizeTool(self):
        self.digitizeAction.setEnabled(False)
        layer = self.iface.activeLayer()

        if layer is not None and isinstance(layer, QgsVectorLayer) and (layer.geometryType() == QgsWkbTypes.PointGeometry) and layer.isEditable():
            self.digitizeAction.setEnabled(True)
        else:
            if self.digitizerDialog is not None:
                self.digitizerDialog.close()
