"""
/***************************************************************************
 *   Copyright (C) 2016 by National Technical University of Athens       *
 *   mpy@hydromech.gr                                                     *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# BUILD: 2026-03-17-08:30-ULTRAFAST

import os
import re
import traceback

from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDockWidget, QApplication, QMenu
from qgis.gui import QgsRubberBand, QgsProjectionSelectionDialog
from qgis.core import (
    Qgis,
    QgsJsonUtils,
    QgsWkbTypes,
    QgsPointXY,
    QgsGeometry,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
    QgsMessageLog,
)
from .util import epsg4326, parseDMSString, tr
from .settings import settings, CoordOrder, H3_INSTALLED
from .utm import isUtm, utm2Point
from .ups import isUps, ups2Point
from . import mgrs
from . import olc
from . import geohash
from .maidenhead import maidenGrid
from . import georef
from .parser_service import parse_coordinate_with_service

if H3_INSTALLED:
    import h3

# Pre-compile regex patterns for performance
COMPILED_REGEX = {
    "whitespace": re.compile(r"\s+"),
    "point_search": re.compile(r"POINT\("),
    "point_extract": re.compile(r"POINT\(\s*([+-]?\d*\.?\d*)\s+([+-]?\d*\.?\d*)"),
    "coord_split": re.compile(r"[\s,;:]+"),
    "mgrs_clean": re.compile(r"\s+"),
    # Ultra-fast path for simple decimal degrees (most common case)
    "simple_decimal": re.compile(
        r"^\s*([+-]?\d+\.?\d*)\s*[\s,;:]+\s*([+-]?\d+\.?\d*)\s*$"
    ),
}

FORM_CLASS, _ = loadUiType(
    os.path.join(os.path.dirname(__file__), "ui/zoomToLatLon.ui")
)


class ZoomToLatLon(QDockWidget, FORM_CLASS):
    def __init__(self, lltools, iface, parent):
        super(ZoomToLatLon, self).__init__(parent)
        self.setupUi(self)
        self.canvas = iface.mapCanvas()
        self.clipboard = QApplication.clipboard()
        self.zoomToolButton.setIcon(QIcon(":/images/themes/default/mActionZoomIn.svg"))
        self.clearToolButton.setIcon(
            QIcon(":/images/themes/default/mIconClearText.svg")
        )
        self.pasteButton.setIcon(QIcon(":/images/themes/default/mActionEditPaste.svg"))
        self.zoomToolButton.clicked.connect(self.zoomToPressed)
        self.clearToolButton.clicked.connect(self.removeMarker)
        self.pasteButton.clicked.connect(self.pasteCoordinate)
        self.optionsButton.setIcon(QIcon(":/images/themes/default/mActionOptions.svg"))
        self.optionsButton.clicked.connect(self.showSettings)
        self.xyIcon = QIcon(os.path.dirname(__file__) + "/images/xy.svg")
        self.yxIcon = QIcon(os.path.dirname(__file__) + "/images/yx.svg")
        self.xyButton.setIcon(self.yxIcon)
        self.xyButton.clicked.connect(self.xyButtonClicked)
        self.crsButton.setIcon(
            QIcon(":/images/themes/default/mIconProjectionEnabled.svg")
        )
        self.crsmenu = QMenu()
        a = self.crsmenu.addAction(tr("WGS 84"))
        a.setData("wgs84")
        a = self.crsmenu.addAction(tr("Project CRS"))
        a.setData("project")
        a = self.crsmenu.addAction(tr("Custom CRS"))
        a.setData("custom")
        a = self.crsmenu.addAction(tr("MGRS"))
        a.setData("mgrs")
        a = self.crsmenu.addAction(tr("Plus Codes"))
        a.setData("pluscode")
        a = self.crsmenu.addAction(tr("Standard UTM"))
        a.setData("utm")
        a = self.crsmenu.addAction(tr("Geohash"))
        a.setData("geohash")
        a = self.crsmenu.addAction(tr("Maidenhead Grid"))
        a.setData("ham")
        if H3_INSTALLED:
            a = self.crsmenu.addAction(tr("H3"))
            a.setData("h3")
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
                self.label.setText("{} {} Y,X".format(tr("Enter"), crsID))
            else:
                self.label.setText("{} {} X,Y".format(tr("Enter"), crsID))
        else:  # Default to custom CRS
            crsID = self.settings.zoomToCustomCrsId()
            if self.settings.zoomToCoordOrder == 0:
                self.label.setText("{} {} Y,X".format(tr("Enter"), crsID))
            else:
                self.label.setText("{} {} X,Y".format(tr("Enter"), crsID))
        if self.settings.zoomToCoordOrder == 0:
            self.xyButton.setIcon(self.yxIcon)
        else:
            self.xyButton.setIcon(self.xyIcon)

    def convertCoordinate(self, text):
        """Parse coordinate text with ultra-fast path for simple decimal degrees."""
        from .debug_logging import log_debug, log_error

        text = text.strip() if text else ""

        # ========== ULTRA-FAST PATH: Simple decimal degrees ==========
        # Handles 90%+ of common coordinate inputs with a single regex match
        m = COMPILED_REGEX["simple_decimal"].match(text)
        if m:
            try:
                val1 = float(m.group(1))
                val2 = float(m.group(2))

                # Apply coordinate order preference
                if self.settings.zoomToCoordOrder == CoordOrder.OrderYX:
                    lat, lon = val1, val2  # Input is "lat, lon"
                else:
                    lat, lon = val2, val1  # Input is "lon, lat"

                # Validate geographic ranges
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon, None, epsg4326)

                # Try swapped if original order failed validation
                if -90 <= lon <= 90 and -180 <= lat <= 180:
                    return (lon, lat, None, epsg4326)

            except (ValueError, TypeError):
                pass  # Fall through to smart parser

        # ========== SMART PARSER PATH: All other formats ==========
        # The smart parser handles: WKT, GeoJSON, MGRS, UTM, UPS, Plus Codes,
        # Geohash, H3, Maidenhead, GEOREF, DMS, and more
        log_debug("Using smart parser for complex format")
        try:
            result = parse_coordinate_with_service(
                text, "ZoomToLatLon", self.settings, self.iface, None
            )
            if result:
                return result
            raise ValueError(tr("Invalid Coordinates"))
        except Exception as e:
            log_error(f"convertCoordinate failed: {e}")
            raise ValueError(tr("Invalid Coordinates"))

    def zoomToPressed(self):
        from .debug_logging import log_debug, log_error, log_warning, log_info

        try:
            text = self.coordTxt.text().strip()
            log_info(f"[v3.14.1] zoomToPressed: '{text}'")

            result = self.convertCoordinate(text)
            if result is None:
                raise ValueError("convertCoordinate returned None")

            (lat, lon, bounds, srcCrs) = result
            log_debug(f"zoomToPressed: lat={lat}, lon={lon}")

            # Validate coordinates
            if lat is None or lon is None:
                raise ValueError("Invalid coordinates")

            # Handle CRS - assume WGS84 if CRS is None or invalid
            if srcCrs is None or not (hasattr(srcCrs, "isValid") and srcCrs.isValid()):
                log_warning(f"Invalid CRS: {srcCrs}, assuming WGS84")
                try:
                    from qgis.core import QgsCoordinateReferenceSystem

                    srcCrs = QgsCoordinateReferenceSystem("EPSG:4326")
                    if not srcCrs.isValid():
                        srcCrs = None
                except Exception as e:
                    log_error(f"Exception creating EPSG:4326: {e}")
                    srcCrs = None

            if srcCrs is None:
                log_warning("Using None CRS - letting zoomTo handle coordinate system")

            pt = self.lltools.zoomTo(srcCrs, lat, lon)

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
                    trans = QgsCoordinateTransform(
                        srcCrs, canvas_crs, QgsProject.instance()
                    )
                    bounds.transform(trans)
                self.line_marker.addGeometry(bounds, None)

            QgsMessageLog.logMessage(
                "ZoomToLatLon.zoomToPressed: Zoom operation completed successfully",
                "LatLonTools",
                Qgis.Info,
            )

        except Exception as e:
            QgsMessageLog.logMessage(
                f"ZoomToLatLon.zoomToPressed: Exception during zoom: {e}",
                "LatLonTools",
                Qgis.Critical,
            )
            import traceback

            QgsMessageLog.logMessage(
                f"ZoomToLatLon.zoomToPressed: Traceback: {traceback.format_exc()}",
                "LatLonTools",
                Qgis.Critical,
            )
            self.iface.messageBar().pushMessage(
                "", tr("Invalid Coordinate"), level=Qgis.Warning, duration=2
            )
            return

    def pasteCoordinate(self):
        text = self.clipboard.text().strip()
        self.coordTxt.clear()
        self.coordTxt.setText(text)

    def removeMarker(self):
        try:
            if hasattr(self, "marker") and self.marker:
                self.marker.reset(QgsWkbTypes.PointGeometry)
        except (RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(
                f"ZoomToLatLon.removeMarker: Exception resetting marker: {e}",
                "LatLonTools",
                Qgis.Warning,
            )
        try:
            if hasattr(self, "line_marker") and self.line_marker:
                self.line_marker.reset(QgsWkbTypes.LineGeometry)
        except (RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(
                f"ZoomToLatLon.removeMarker: Exception resetting line_marker: {e}",
                "LatLonTools",
                Qgis.Warning,
            )
        try:
            self.coordTxt.clear()
        except (RuntimeError, AttributeError) as e:
            QgsMessageLog.logMessage(
                f"ZoomToLatLon.removeMarker: Exception clearing coordTxt: {e}",
                "LatLonTools",
                Qgis.Warning,
            )

    def showSettings(self):
        self.settings.showTab(1)

    def xyButtonClicked(self):
        # Store the current coordinate text to preserve it during configuration
        current_text = self.coordTxt.text()

        if self.settings.zoomToCoordOrder == 0:
            self.settings.setZoomToCoordOrder(1)
        else:
            self.settings.setZoomToCoordOrder(0)
        self.configure()

        # Restore the coordinate text after configuration
        self.coordTxt.setText(current_text)

    def crsTriggered(self, action):
        selection_id = action.data()
        crs = None
        if selection_id == "custom":
            selector = QgsProjectionSelectionDialog()
            selector.setCrs(
                QgsCoordinateReferenceSystem(self.settings.zoomToCustomCRS())
            )
            if selector.exec():
                crs = selector.crs()
        self.settings.setZoomToMode(selection_id, crs)
        self.configure()
