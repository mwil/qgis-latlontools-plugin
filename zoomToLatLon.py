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
import os
import re

# Pre-compile regex patterns for performance
COMPILED_REGEX = {
    'whitespace': re.compile(r'\s+'),
    'point_search': re.compile(r'POINT\('),
    'point_extract': re.compile(r'POINT\(\s*([+-]?\d*\.?\d*)\s+([+-]?\d*\.?\d*)'),
    'coord_split': re.compile(r'[\s,;:]+'),
    'mgrs_clean': re.compile(r'\s+'),
}

from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.PyQt.QtWidgets import QDockWidget, QApplication, QMenu
from qgis.PyQt.QtCore import QTextCodec
from qgis.gui import QgsRubberBand, QgsProjectionSelectionDialog
from qgis.core import Qgis, QgsJsonUtils, QgsWkbTypes, QgsPointXY, QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, QgsRectangle, QgsMessageLog
from .util import epsg4326, parseDMSString, tr
from .settings import settings, CoordOrder, H3_INSTALLED
from .utm import isUtm, utm2Point
from .ups import isUps, ups2Point
import traceback

from . import mgrs
from . import olc
from . import geohash
from .maidenhead import maidenGrid
from . import georef
if H3_INSTALLED:
    import h3

from .parser_service import parse_coordinate_with_service

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui/zoomToLatLon.ui'))


class ZoomToLatLon(QDockWidget, FORM_CLASS):

    def __init__(self, lltools, iface, parent):
        super(ZoomToLatLon, self).__init__(parent)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.clipboard = QApplication.clipboard()
        self.zoomToolButton.setIcon(QIcon(':/images/themes/default/mActionZoomIn.svg'))
        self.clearToolButton.setIcon(QIcon(':/images/themes/default/mIconClearText.svg'))
        self.pasteButton.setIcon(QIcon(':/images/themes/default/mActionEditPaste.svg'))
        self.zoomToolButton.clicked.connect(self.zoomToPressed)
        self.clearToolButton.clicked.connect(self.removeMarker)
        self.pasteButton.clicked.connect(self.pasteCoordinate)
        self.optionsButton.setIcon(QIcon(':/images/themes/default/mActionOptions.svg'))
        self.optionsButton.clicked.connect(self.showSettings)
        self.xyIcon = QIcon(os.path.dirname(__file__) + '/images/xy.svg')
        self.yxIcon = QIcon(os.path.dirname(__file__) + '/images/yx.svg')
        self.xyButton.setIcon(self.yxIcon)
        self.xyButton.clicked.connect(self.xyButtonClicked)
        self.crsButton.setIcon(QIcon(':/images/themes/default/mIconProjectionEnabled.svg'))
        self.crsmenu = QMenu()
        a = self.crsmenu.addAction(tr("WGS 84"))
        a.setData('wgs84')
        a = self.crsmenu.addAction(tr("Project CRS"))
        a.setData('project')
        a = self.crsmenu.addAction(tr("Custom CRS"))
        a.setData('custom')
        a = self.crsmenu.addAction(tr("MGRS"))
        a.setData('mgrs')
        a = self.crsmenu.addAction(tr("Plus Codes"))
        a.setData('pluscode')
        a = self.crsmenu.addAction(tr("Standard UTM"))
        a.setData('utm')
        a = self.crsmenu.addAction(tr("Geohash"))
        a.setData('geohash')
        a = self.crsmenu.addAction(tr("Maidenhead Grid"))
        a.setData('ham')
        if H3_INSTALLED:
            a = self.crsmenu.addAction(tr("H3"))
            a.setData('h3')
        # Enhanced functionality added via plugin_enhancements module
        self.crsButton.setMenu(self.crsmenu)
        self.crsButton.triggered.connect(self.crsTriggered)
        self.lltools = lltools
        self.settings = lltools.settingsDialog
        self.iface = iface
        self.coordTxt.returnPressed.connect(self.zoomToPressed)
        self.canvas.destinationCrsChanged.connect(self.crsChanged)
        
        self.marker = QgsRubberBand(self.canvas, QgsWkbTypes.PointGeometry)
        self.marker.setColor(settings.markerColor)
        self.marker.setStrokeColor(settings.markerColor)
        self.marker.setWidth(settings.markerWidth)
        self.marker.setIconSize(settings.markerSize)
        self.marker.setIcon(QgsRubberBand.ICON_CROSS)
        
        self.line_marker = QgsRubberBand(self.canvas, QgsWkbTypes.LineGeometry)
        self.line_marker.setWidth(settings.gridWidth)
        self.line_marker.setColor(settings.gridColor)
        self.configure()

    def showEvent(self, e):
        self.configure()

    def closeEvent(self, event):
        self.removeMarker()
        event.accept()

    def crsChanged(self):
        if self.isVisible():
            self.configure()

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def configure(self):
        self.coordTxt.setText("")
        self.removeMarker()

        if self.settings.zoomToProjIsMGRS():
            # This is an MGRS coordinate
            self.label.setText(tr("Enter MGRS Coordinate"))
        elif self.settings.zoomToProjIsPlusCodes():
            self.label.setText(tr("Enter Plus Codes"))
        elif self.settings.zoomToProjIsGeohash():
            self.label.setText(tr("Enter Geohash"))
        elif self.settings.zoomToProjIsH3():
            self.label.setText(tr("Enter H3 geohash"))
        elif self.settings.zoomToProjIsStandardUtm():
            self.label.setText(tr("Enter Standard UTM"))
        elif self.settings.zoomToProjIsMaidenhead():
            self.label.setText(tr("Enter Maidenhead Grid"))
        elif self.settings.zoomToProjIsWgs84():
            if self.settings.zoomToCoordOrder == 0:
                self.label.setText(tr("Enter 'Latitude, Longitude'"))
            else:
                self.label.setText(tr("Enter 'Longitude, Latitude'"))
        elif self.settings.zoomToProjIsProjectCRS():
            crsID = self.canvas.mapSettings().destinationCrs().authid()
            if self.settings.zoomToCoordOrder == 0:
                self.label.setText("{} {} Y,X".format(tr('Enter'), crsID))
            else:
                self.label.setText("{} {} X,Y".format(tr('Enter'), crsID))
        else:  # Default to custom CRS
            crsID = self.settings.zoomToCustomCrsId()
            if self.settings.zoomToCoordOrder == 0:
                self.label.setText("{} {} Y,X".format(tr('Enter'), crsID))
            else:
                self.label.setText("{} {} X,Y".format(tr('Enter'), crsID))
        if self.settings.zoomToCoordOrder == 0:
            self.xyButton.setIcon(self.yxIcon)
        else:
            self.xyButton.setIcon(self.xyIcon)

    def convertCoordinate(self, text):
        from qgis.core import QgsMessageLog, Qgis
        
        QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: STARTING CONVERSION for input: '{text}'", "LatLonTools", Qgis.Info)
        
        try:
            # Define legacy fallback function
            def legacy_fallback(text):
                """Legacy parsing fallback function"""
                QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: === FALLING BACK TO LEGACY PARSERS ===", "LatLonTools", Qgis.Info)
                
                if self.settings.zoomToProjIsMGRS():
                    QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: Trying MGRS (forced by setting)", "LatLonTools", Qgis.Info)
                    # An MGRS coordinate only format has been specified. This will result in an exception
                    # if it is not a valid MGRS coordinate
                    text2 = COMPILED_REGEX['mgrs_clean'].sub('', str(text))  # Remove all white space
                    lat, lon = mgrs.toWgs(text2)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: MGRS SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(lat, lon, None, epsg4326)

                # Other legacy format checks with minimal logging for brevity
                if self.settings.zoomToProjIsPlusCodes():
                    coord = olc.decode(text)
                    lat = coord.latitudeCenter
                    lon = coord.longitudeCenter
                    rect = QgsRectangle(coord.longitudeLo, coord.latitudeLo, coord.longitudeHi, coord.latitudeHi)
                    geom = QgsGeometry.fromRect(rect)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: PLUS CODES SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(lat, lon, geom, epsg4326)

                if self.settings.zoomToProjIsStandardUtm():
                    pt = utm2Point(text)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: STANDARD UTM SUCCESS: lat={pt.y()}, lon={pt.x()}", "LatLonTools", Qgis.Info)
                    return(pt.y(), pt.x(), None, epsg4326)

                if self.settings.zoomToProjIsGeohash():
                    (lat1, lat2, lon1, lon2) = geohash.decode_extent(text)
                    lat = (lat1 + lat2) / 2
                    lon = (lon1 + lon2) / 2
                    rect = QgsRectangle(lon1, lat1, lon2, lat2)
                    geom = QgsGeometry.fromRect(rect)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: GEOHASH SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(lat, lon, geom, epsg4326)

                if self.settings.zoomToProjIsH3():
                    if not h3.is_valid_cell(text):
                        raise ValueError(tr('Invalid H3 Coordinate'))
                    (lat, lon) = h3.cell_to_latlng(text)
                    coords = h3.cell_to_boundary(text)
                    pts = []
                    for p in coords:
                        pt = QgsPointXY(p[1], p[0])
                        pts.append(pt)
                    pts.append(pts[0])  # Close the polygon
                    geom = QgsGeometry.fromPolylineXY(pts)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: H3 SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(lat, lon, geom, epsg4326)

                if self.settings.zoomToProjIsMaidenhead():
                    (lat, lon, lat1, lon1, lat2, lon2) = maidenGrid(text)
                    rect = QgsRectangle(lon1, lat1, lon2, lat2)
                    geom = QgsGeometry.fromRect(rect)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: MAIDENHEAD SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(float(lat), float(lon), geom, epsg4326)

                # Check for other formats (auto-detection)
                QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: Starting auto-detection of formats...", "LatLonTools", Qgis.Info)
                
                if text[0] == '{':  # This may be a GeoJSON point
                    QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: Trying GeoJSON (auto-detected)", "LatLonTools", Qgis.Info)
                    codec = QTextCodec.codecForName("UTF-8")
                    fields = QgsJsonUtils.stringToFields(text, codec)
                    fet = QgsJsonUtils.stringToFeatureList(text, fields, codec)
                    if (len(fet) == 0) or not fet[0].isValid():
                        QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: GeoJSON parsing failed", "LatLonTools", Qgis.Warning)
                        raise ValueError(tr('Invalid Coordinates'))

                    geom = fet[0].geometry()
                    if geom.isEmpty() or (geom.wkbType() != QgsWkbTypes.Point):
                        QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: GeoJSON geometry invalid", "LatLonTools", Qgis.Warning)
                        raise ValueError(tr('Invalid GeoJSON Geometry'))
                    pt = geom.asPoint()
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: GEOJSON SUCCESS: lat={pt.y()}, lon={pt.x()}", "LatLonTools", Qgis.Info)
                    return(pt.y(), pt.x(), None, epsg4326)

                # Check to see if it is standard UTM
                QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: Checking if input is UTM (auto-detect)...", "LatLonTools", Qgis.Info)
                if isUtm(text):
                    QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: Detected as UTM, parsing...", "LatLonTools", Qgis.Info)
                    pt = utm2Point(text)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: UTM SUCCESS: lat={pt.y()}, lon={pt.x()}", "LatLonTools", Qgis.Info)
                    return(pt.y(), pt.x(), None, epsg4326)
                else:
                    QgsMessageLog.logMessage("ZoomToLatLon.convertCoordinate: Not UTM format", "LatLonTools", Qgis.Info)

                # Check to see if it is a UPS coordinate
                if isUps(text):
                    pt = ups2Point(text)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: UPS SUCCESS: lat={pt.y()}, lon={pt.x()}", "LatLonTools", Qgis.Info)
                    return(pt.y(), pt.x(), None, epsg4326)

                # Try other formats with exception handling
                for format_name, format_func in [
                    ("Georef", lambda: georef.decode(text, False)),
                    ("MGRS", lambda: mgrs.toWgs(COMPILED_REGEX['mgrs_clean'].sub('', str(text)))),
                    ("Plus Codes", lambda: olc.decode(text)),
                    ("Geohash", lambda: geohash.decode_exactly(text))
                ]:
                    try:
                        if format_name == "Plus Codes":
                            coord = format_func()
                            lat = coord.latitudeCenter
                            lon = coord.longitudeCenter
                        elif format_name == "Geohash":
                            (lat, lon, lat_err, lon_err) = format_func()
                        else:
                            result = format_func()
                            if format_name == "Georef":
                                lat, lon, prec = result
                            else:  # MGRS
                                lat, lon = result
                        
                        QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: {format_name.upper()} SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                        return(lat, lon, None, epsg4326)
                    except Exception as e:
                        QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: {format_name} failed: {e}", "LatLonTools", Qgis.Info)
                        continue

                # Check to see if it is a WKT POINT format
                if COMPILED_REGEX['point_search'].search(text) is not None:
                    m = COMPILED_REGEX['point_extract'].findall(text)
                    if len(m) != 1:
                        raise ValueError(tr('Invalid Coordinates'))
                    lon = float(m[0][0])
                    lat = float(m[0][1])
                    if self.settings.zoomToProjIsWgs84():
                        srcCrs = epsg4326
                    elif self.settings.zoomToProjIsProjectCRS():
                        srcCrs = self.canvas.mapSettings().destinationCrs()
                    else:
                        srcCrs = self.settings.zoomToCustomCRS()
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: WKT POINT SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(lat, lon, None, srcCrs)

                # We are left with either DMS or decimal degrees in one of the projections
                if self.settings.zoomToProjIsWgs84():
                    lat, lon = parseDMSString(text, self.settings.zoomToCoordOrder)
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: WGS84 DMS/DECIMAL SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                    return(lat, lon, None, epsg4326)

                # We are left with a non WGS 84 decimal projection
                coords = COMPILED_REGEX['coord_split'].split(text, 1)
                if len(coords) < 2:
                    QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: Not enough coordinates found: {coords}", "LatLonTools", Qgis.Warning)
                    raise ValueError(tr('Invalid Coordinates'))
                if self.settings.zoomToCoordOrder == CoordOrder.OrderYX:
                    lat = float(coords[0])
                    lon = float(coords[1])
                else:
                    lon = float(coords[0])
                    lat = float(coords[1])
                if self.settings.zoomToProjIsProjectCRS():
                    srcCrs = self.canvas.mapSettings().destinationCrs()
                else:
                    srcCrs = self.settings.zoomToCustomCRS()
                QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: DECIMAL SUCCESS: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                return(lat, lon, None, srcCrs)
            
            # Use parser service with fallback
            result = parse_coordinate_with_service(text, "ZoomToLatLon", self.settings, self.iface, legacy_fallback)
            if result:
                return result
            else:
                raise ValueError(tr('Invalid Coordinates'))
        
        except Exception as e:
            QgsMessageLog.logMessage(f"ZoomToLatLon.convertCoordinate: FAILED with exception: {e}", "LatLonTools", Qgis.Critical)
            raise ValueError(tr('Invalid Coordinates'))
        
    def zoomToPressed(self):
        from qgis.core import QgsMessageLog, Qgis
        
        try:
            text = self.coordTxt.text().strip()
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Starting zoom for input: '{text}'", "LatLonTools", Qgis.Info)
            
            result = self.convertCoordinate(text)
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: convertCoordinate result: {result}", "LatLonTools", Qgis.Info)
            
            if result is None:
                QgsMessageLog.logMessage("ZoomToLatLon.zoomToPressed: convertCoordinate returned None", "LatLonTools", Qgis.Critical)
                raise ValueError("convertCoordinate returned None")
                
            (lat, lon, bounds, srcCrs) = result
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Unpacked coordinates: lat={lat}, lon={lon}, bounds={bounds}, srcCrs={srcCrs}", "LatLonTools", Qgis.Info)
            
            # Validate coordinates
            if lat is None or lon is None:
                QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Invalid coordinates: lat={lat}, lon={lon}", "LatLonTools", Qgis.Critical)
                raise ValueError("Invalid coordinates")
                
            # Handle CRS - assume WGS84 if CRS is None or invalid (due to PROJ database issues)
            if srcCrs is None or not (hasattr(srcCrs, 'isValid') and srcCrs.isValid()):
                QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Invalid/None CRS: {srcCrs}, assuming WGS84 coordinates", "LatLonTools", Qgis.Warning)
                try:
                    from qgis.core import QgsCoordinateReferenceSystem
                    srcCrs = QgsCoordinateReferenceSystem('EPSG:4326')
                    if not srcCrs.isValid():
                        QgsMessageLog.logMessage("ZoomToLatLon.zoomToPressed: Even EPSG:4326 creation failed, using None (direct coordinates)", "LatLonTools", Qgis.Critical)
                        srcCrs = None
                except Exception as e:
                    QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Exception creating EPSG:4326: {e}", "LatLonTools", Qgis.Critical)
                    srcCrs = None
            
            # Special handling for PROJ database issues - pass None CRS to let zoomTo handle it
            if srcCrs is None:
                QgsMessageLog.logMessage("ZoomToLatLon.zoomToPressed: Using None CRS - letting zoomTo handle coordinate system", "LatLonTools", Qgis.Warning)
            else:
                QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Using CRS: {srcCrs.authid()}", "LatLonTools", Qgis.Info)
            
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: About to call lltools.zoomTo with srcCrs={srcCrs}, lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
            pt = self.lltools.zoomTo(srcCrs, lat, lon)
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: zoomTo returned point: {pt}", "LatLonTools", Qgis.Info)
            
            self.marker.reset(QgsWkbTypes.PointGeometry)
            self.marker.setWidth(settings.markerWidth)
            self.marker.setIconSize(settings.markerSize)
            self.marker.setColor(settings.markerColor)
            if self.settings.persistentMarker:
                self.marker.addPoint(pt)
            self.line_marker.reset(QgsWkbTypes.LineGeometry)
            self.line_marker.setWidth(settings.gridWidth)
            self.line_marker.setColor(settings.gridColor)
            if bounds and self.settings.showGrid:
                canvas_crs = self.canvas.mapSettings().destinationCrs()
                if srcCrs and srcCrs != canvas_crs:
                    trans = QgsCoordinateTransform(srcCrs, canvas_crs, QgsProject.instance())
                    bounds.transform(trans)
                self.line_marker.addGeometry(bounds, None)
                
            QgsMessageLog.logMessage("ZoomToLatLon.zoomToPressed: Zoom operation completed successfully", "LatLonTools", Qgis.Info)
            
        except Exception as e:
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Exception during zoom: {e}", "LatLonTools", Qgis.Critical)
            import traceback
            QgsMessageLog.logMessage(f"ZoomToLatLon.zoomToPressed: Traceback: {traceback.format_exc()}", "LatLonTools", Qgis.Critical)
            self.iface.messageBar().pushMessage("", tr("Invalid Coordinate"), level=Qgis.Warning, duration=2)
            return

    def pasteCoordinate(self):
        text = self.clipboard.text().strip()
        self.coordTxt.clear()
        self.coordTxt.setText(text)
        
    def removeMarker(self):
        try:
            if hasattr(self, 'marker') and self.marker:
                self.marker.reset(QgsWkbTypes.PointGeometry)
        except (RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(f"ZoomToLatLon.removeMarker: Exception resetting marker: {e}", "LatLonTools", Qgis.Warning)
        try:
            if hasattr(self, 'line_marker') and self.line_marker:
                self.line_marker.reset(QgsWkbTypes.LineGeometry)
        except (RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(f"ZoomToLatLon.removeMarker: Exception resetting line_marker: {e}", "LatLonTools", Qgis.Warning)
        try:
            self.coordTxt.clear()
        except (RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(f"ZoomToLatLon.removeMarker: Exception clearing coordTxt: {e}", "LatLonTools", Qgis.Warning)

    def showSettings(self):
        self.settings.showTab(1)

    def xyButtonClicked(self):
        if self.settings.zoomToCoordOrder == 0:
            self.settings.setZoomToCoordOrder(1)
        else:
            self.settings.setZoomToCoordOrder(0)
        self.configure()

    def crsTriggered(self, action):
        selection_id = action.data()
        crs = None
        if selection_id == 'custom':
            selector = QgsProjectionSelectionDialog()
            selector.setCrs(QgsCoordinateReferenceSystem(self.settings.zoomToCustomCRS()))
            if selector.exec():
                crs = selector.crs()
        self.settings.setZoomToMode(selection_id, crs)
        self.configure()

