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
from qgis.PyQt.QtCore import Qt, QTimer, QUrl, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QApplication, QToolButton
from qgis.core import Qgis, QgsCoordinateTransform, QgsVectorLayer, QgsRectangle, QgsPoint, QgsPointXY, QgsGeometry, QgsWkbTypes, QgsProject, QgsApplication, QgsSettings
from qgis.gui import QgsRubberBand
import processing

from .latLonFunctions import InitLatLonFunctions, UnloadLatLonFunctions
from .zoomToLatLon import ZoomToLatLon
from .multizoom import MultiZoomWidget
from .settings import SettingsWidget, settings
from .provider import LatLonToolsProvider
from .util import epsg4326, tr
from .captureExtent import getExtentString
import os


class LatLonTools:
    digitizerDialog = None
    convertCoordinateDialog = None
    mapTool = None
    showMapTool = None
    copyExtentTool = None

    def __init__(self, iface):
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

    def initGui(self):
        '''Initialize Lot Lon Tools GUI.'''
        # Initialize the Settings Dialog box
        self.settingsDialog = SettingsWidget(self, self.iface, self.iface.mainWindow())

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

        self.zoomToDialog = ZoomToLatLon(self, self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.zoomToDialog)
        
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

        self.multiZoomDialog = MultiZoomWidget(self, self.settingsDialog, self.iface.mainWindow())
        self.multiZoomDialog.hide()
        self.multiZoomDialog.setFloating(True)

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
        '''Unload LatLonTools from the QGIS interface'''
        # Set flag to prevent operations during shutdown
        if not hasattr(self, '_is_unloading'):
            self._is_unloading = False
        self._is_unloading = True
        
        # Use enhanced cleanup functionality if available
        if hasattr(self, '_enhancements') and self._enhancements:
            try:
                self._enhancements.safe_unload()
            except Exception as e:
                # If enhanced cleanup fails, fall back to basic cleanup
                try:
                    from qgis.core import QgsMessageLog, Qgis
                    QgsMessageLog.logMessage(f"Enhanced cleanup failed, using fallback: {str(e)}", "LatLonTools", Qgis.Warning)
                except:
                    pass
                self._fallback_cleanup()
        else:
            # Use comprehensive fallback cleanup 
            self._fallback_cleanup()
            
    def _fallback_cleanup(self):
        """Comprehensive fallback cleanup when enhanced cleanup is not available"""
        try:
            # Disconnect main plugin signals first - check if objects exist
            if hasattr(self, 'iface') and self.iface:
                try:
                    self.iface.currentLayerChanged.disconnect(self.currentLayerChanged)
                except (TypeError, RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'canvas') and self.canvas:
                try:
                    self.canvas.mapToolSet.disconnect(self.resetTools)
                except (TypeError, RuntimeError, AttributeError):
                    pass
                    
            # Disconnect current layer editing signals - may fail if iface is gone
            try:
                if hasattr(self, 'iface') and self.iface:
                    layer = self.iface.activeLayer()
                    if layer is not None:
                        try:
                            layer.editingStarted.disconnect(self.layerEditingChanged)
                            layer.editingStopped.disconnect(self.layerEditingChanged)
                        except (TypeError, RuntimeError, AttributeError):
                            pass
            except (RuntimeError, AttributeError):
                pass
            
            # Clean up crossRb rubber band
            if hasattr(self, 'crossRb') and self.crossRb:
                try:
                    self.crossRb.reset()
                    if hasattr(self, 'canvas') and self.canvas:
                        scene = self.canvas.scene()
                        if scene and self.crossRb in scene.items():
                            scene.removeItem(self.crossRb)
                except (RuntimeError, AttributeError):
                    pass
            
            # Enhanced dialog cleanup with existence checks
            if hasattr(self, 'zoomToDialog') and self.zoomToDialog:
                try:
                    # Disconnect canvas signal if canvas still exists
                    if hasattr(self, 'canvas') and self.canvas:
                        self.canvas.destinationCrsChanged.disconnect(self.zoomToDialog.crsChanged)
                except (TypeError, RuntimeError, AttributeError):
                    pass
                try:
                    self.zoomToDialog.removeMarker()
                    if hasattr(self, 'iface') and self.iface:
                        self.iface.removeDockWidget(self.zoomToDialog)
                    self.zoomToDialog.close()
                    self.zoomToDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'multiZoomDialog') and self.multiZoomDialog:
                try:
                    # Disconnect canvas signal if canvas still exists
                    if hasattr(self, 'canvas') and self.canvas:
                        self.canvas.destinationCrsChanged.disconnect(self.multiZoomDialog.crsChanged)
                except (TypeError, RuntimeError, AttributeError):
                    pass
                try:
                    self.multiZoomDialog.removeMarkers()
                    if hasattr(self, 'iface') and self.iface:
                        self.iface.removeDockWidget(self.multiZoomDialog)
                    self.multiZoomDialog.close()
                    self.multiZoomDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'convertCoordinateDialog') and self.convertCoordinateDialog:
                try:
                    if hasattr(self, 'iface') and self.iface:
                        self.iface.removeDockWidget(self.convertCoordinateDialog)
                    self.convertCoordinateDialog.close()
                    self.convertCoordinateDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'digitizerDialog') and self.digitizerDialog:
                try:
                    self.digitizerDialog.close()
                    self.digitizerDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'settingsDialog') and self.settingsDialog:
                try:
                    self.settingsDialog.close()
                    self.settingsDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            # Cleanup map tools - check existence first
            if hasattr(self, 'mapTool') and self.mapTool:
                try:
                    if hasattr(self, 'canvas') and self.canvas:
                        self.canvas.unsetMapTool(self.mapTool)
                except (RuntimeError, AttributeError):
                    pass
            if hasattr(self, 'showMapTool') and self.showMapTool:
                try:
                    if hasattr(self, 'canvas') and self.canvas:
                        self.canvas.unsetMapTool(self.showMapTool)
                except (RuntimeError, AttributeError):
                    pass
            if hasattr(self, 'copyExtentTool') and self.copyExtentTool:
                try:
                    if hasattr(self, 'canvas') and self.canvas:
                        self.canvas.unsetMapTool(self.copyExtentTool)
                except (RuntimeError, AttributeError):
                    pass
                    
            # Remove menu items - check if actions exist and iface is valid
            menu_action_names = [
                'copyAction', 'copyExtentsAction', 'externMapAction',
                'zoomToAction', 'multiZoomToAction', 'convertCoordinatesAction',
                'conversionsAction', 'settingsAction', 'helpAction', 'digitizeAction'
            ]
            for action_name in menu_action_names:
                if hasattr(self, action_name):
                    try:
                        action = getattr(self, action_name)
                        if action and hasattr(self, 'iface') and self.iface:
                            self.iface.removePluginMenu('Lat Lon Tools', action)
                    except (RuntimeError, AttributeError):
                        pass
                    
            # Remove toolbar icons - check if actions/toolbar exist
            toolbar_action_names = [
                'copyAction', 'copyExtentToolbar', 'zoomToAction',
                'externMapAction', 'multiZoomToAction', 'convertCoordinatesAction',
                'digitizeAction', 'settingsAction'
            ]
            for action_name in toolbar_action_names:
                if hasattr(self, action_name):
                    try:
                        action = getattr(self, action_name)
                        if action and hasattr(self, 'iface') and self.iface:
                            self.iface.removeToolBarIcon(action)
                    except (RuntimeError, AttributeError):
                        pass
                    
            # Remove toolbar - check existence
            if hasattr(self, 'toolbar') and self.toolbar:
                try:
                    self.toolbar.deleteLater()
                    del self.toolbar
                except (RuntimeError, AttributeError):
                    pass
                    
            # Remove translator - check existence
            if hasattr(self, 'translator') and self.translator:
                try:
                    QCoreApplication.removeTranslator(self.translator)
                except (RuntimeError, AttributeError):
                    pass
                
        except Exception as e:
            # Catch any unexpected errors during fallback cleanup
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"Fallback cleanup error (safely ignored): {str(e)}", "LatLonTools", Qgis.Warning)
            except:
                pass
        
        # Clear all references - set to None even if they don't exist
        self.zoomToDialog = None
        self.multiZoomDialog = None
        self.settingsDialog = None
        self.convertCoordinateDialog = None
        self.digitizerDialog = None
        self.showMapTool = None
        self.mapTool = None
        self.copyExtentTool = None
        self.crossRb = None
        self.translator = None
        self.toolbar = None
        
        # Remove processing provider - check existence
        try:
            if hasattr(self, 'provider') and self.provider:
                QgsApplication.processingRegistry().removeProvider(self.provider)
            UnloadLatLonFunctions()
        except (RuntimeError, AttributeError, ImportError):
            pass
            
    def _fallback_cleanup(self):
        """Comprehensive fallback cleanup when enhanced cleanup is not available"""
        try:
            # Disconnect main plugin signals first
            try:
                self.iface.currentLayerChanged.disconnect(self.currentLayerChanged)
            except (TypeError, RuntimeError, AttributeError):
                pass
            try:
                self.canvas.mapToolSet.disconnect(self.resetTools)
            except (TypeError, RuntimeError, AttributeError):
                pass
                
            # Disconnect current layer editing signals
            try:
                layer = self.iface.activeLayer()
                if layer is not None:
                    try:
                        layer.editingStarted.disconnect(self.layerEditingChanged)
                        layer.editingStopped.disconnect(self.layerEditingChanged)
                    except (TypeError, RuntimeError, AttributeError):
                        pass
            except (RuntimeError, AttributeError):
                pass
            
            # Enhanced dialog cleanup
            if hasattr(self, 'zoomToDialog') and self.zoomToDialog:
                try:
                    # Disconnect canvas signal
                    self.canvas.destinationCrsChanged.disconnect(self.zoomToDialog.crsChanged)
                except (TypeError, RuntimeError, AttributeError):
                    pass
                try:
                    self.zoomToDialog.removeMarker()
                    self.iface.removeDockWidget(self.zoomToDialog)
                    self.zoomToDialog.close()
                    self.zoomToDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'multiZoomDialog') and self.multiZoomDialog:
                try:
                    # Disconnect canvas signal
                    self.canvas.destinationCrsChanged.disconnect(self.multiZoomDialog.crsChanged)
                except (TypeError, RuntimeError, AttributeError):
                    pass
                try:
                    self.multiZoomDialog.removeMarkers()
                    self.iface.removeDockWidget(self.multiZoomDialog)
                    self.multiZoomDialog.close()
                    self.multiZoomDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'convertCoordinateDialog') and self.convertCoordinateDialog:
                try:
                    self.iface.removeDockWidget(self.convertCoordinateDialog)
                    self.convertCoordinateDialog.close()
                    self.convertCoordinateDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            if hasattr(self, 'digitizerDialog') and self.digitizerDialog:
                try:
                    self.digitizerDialog.close()
                    self.digitizerDialog.deleteLater()
                except (RuntimeError, AttributeError):
                    pass
                    
            # Cleanup map tools
            if hasattr(self, 'mapTool') and self.mapTool:
                try:
                    self.canvas.unsetMapTool(self.mapTool)
                except (RuntimeError, AttributeError):
                    pass
            if hasattr(self, 'showMapTool') and self.showMapTool:
                try:
                    self.canvas.unsetMapTool(self.showMapTool)
                except (RuntimeError, AttributeError):
                    pass
            if hasattr(self, 'copyExtentTool') and self.copyExtentTool:
                try:
                    self.canvas.unsetMapTool(self.copyExtentTool)
                except (RuntimeError, AttributeError):
                    pass
                    
            # Remove menu items
            menu_actions = [
                'copyAction', 'copyExtentsAction', 'externMapAction',
                'zoomToAction', 'multiZoomToAction', 'convertCoordinatesAction',
                'conversionsAction', 'settingsAction', 'helpAction', 'digitizeAction'
            ]
            for action_name in menu_actions:
                try:
                    action = getattr(self, action_name, None)
                    if action:
                        self.iface.removePluginMenu('Lat Lon Tools', action)
                except (RuntimeError, AttributeError):
                    pass
                    
            # Remove toolbar icons
            toolbar_actions = [
                'copyAction', 'copyExtentToolbar', 'zoomToAction',
                'externMapAction', 'multiZoomToAction', 'convertCoordinatesAction',
                'digitizeAction', 'settingsAction'
            ]
            for action_name in toolbar_actions:
                try:
                    action = getattr(self, action_name, None)
                    if action:
                        self.iface.removeToolBarIcon(action)
                except (RuntimeError, AttributeError):
                    pass
                    
            # Remove toolbar
            try:
                if hasattr(self, 'toolbar'):
                    self.toolbar.deleteLater()
                    del self.toolbar
            except (RuntimeError, AttributeError):
                pass
                
        except Exception as e:
            # Catch any unexpected errors during fallback cleanup
            try:
                from qgis.core import QgsMessageLog, Qgis
                QgsMessageLog.logMessage(f"Fallback cleanup error (safely ignored): {str(e)}", "LatLonTools", Qgis.Warning)
            except:
                pass
        
        # Clear references
        self.zoomToDialog = None
        self.multiZoomDialog = None
        self.settingsDialog = None
        self.convertCoordinateDialog = None
        self.digitizerDialog = None
        self.showMapTool = None
        self.mapTool = None
        self.copyExtentTool = None

        # Remove processing provider
        try:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            UnloadLatLonFunctions()
        except (RuntimeError, AttributeError):
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
        layer = self.iface.activeLayer()
        if not layer or not layer.isValid():
            return
        if isinstance(layer, QgsVectorLayer) and (layer.featureCount() == 0):
            self.iface.messageBar().pushMessage("", tr("This layer has no features - A bounding box cannot be calculated."), level=Qgis.Warning, duration=4)
            return
        if isinstance(layer, QgsVectorLayer):
            extent = layer.boundingBoxOfSelected()
            if extent.isNull():
                self.iface.messageBar().pushMessage("", tr("No features were selected."), level=Qgis.Warning, duration=4)
                return
        else:
            extent = layer.extent()
        src_crs = layer.crs()
        if settings.bBoxCrs == 0:
            dst_crs = epsg4326
        else:
            dst_crs = self.canvas.mapSettings().destinationCrs()
        
        outStr = getExtentString(extent, src_crs, dst_crs)
        clipboard = QApplication.clipboard()
        clipboard.setText(outStr)
        self.iface.messageBar().pushMessage("", "'{}' {}".format(outStr, tr('copied to the clipboard')), level=Qgis.Info, duration=4)

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
        self.crossRb.reset()

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
