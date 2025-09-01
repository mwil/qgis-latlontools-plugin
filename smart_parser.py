"""
Smart coordinate parser module
Implements intelligent coordinate detection and parsing for any input format
"""
import re
from qgis.core import (
    QgsGeometry, QgsCoordinateReferenceSystem, 
    QgsCoordinateTransform, QgsProject, QgsWkbTypes, QgsRectangle,
    QgsPointXY, QgsJsonUtils
)
from qgis.PyQt.QtCore import QTextCodec
# Handle both plugin context (relative imports) and standalone testing (absolute imports)
try:
    from .util import epsg4326, tr
    from .settings import CoordOrder
except ImportError:
    # Fallback for standalone testing
    from util import epsg4326, tr
    from settings import CoordOrder


class SmartCoordinateParser:
    """
    Smart coordinate parser - handles any coordinate input format
    Supports WKT, EWKT, WKB, MGRS, Plus Codes, UTM, UPS, Geohash, 
    Maidenhead Grid, H3, GeoJSON, DMS, and decimal coordinates
    """
    
    # WKB geometry type constants
    WKB_POINT_TYPE = 1
    
    def __init__(self, settings_obj, iface):
        self.settings = settings_obj
        self.iface = iface
        
    def parse(self, text):
        """
        Main parsing entry point
        Returns: (lat, lon, bounds, source_crs) or None if parsing fails
        """
        from qgis.core import QgsMessageLog, Qgis
        
        original_text = text.strip()
        QgsMessageLog.logMessage(f"SmartParser.parse: STARTING PARSE for input: '{original_text}'", "LatLonTools", Qgis.Info)
        
        try:
            # Phase 1: Explicit formats (WKT, EWKT, WKB)
            QgsMessageLog.logMessage("SmartParser.parse: === PHASE 1: Trying explicit formats (WKT, EWKT, WKB) ===", "LatLonTools", Qgis.Info)
            result = self._try_explicit_formats(text)
            if result:
                lat, lon, source_crs, description = result
                QgsMessageLog.logMessage(f"SmartParser.parse: PHASE 1 SUCCESS - {description}: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                return (lat, lon, None, source_crs)
            else:
                QgsMessageLog.logMessage("SmartParser.parse: PHASE 1 FAILED - No explicit format match", "LatLonTools", Qgis.Warning)
            
            # Phase 2: Existing formats (MGRS, UTM, etc.)
            QgsMessageLog.logMessage("SmartParser.parse: === PHASE 2: Trying existing formats (MGRS, UTM, etc.) ===", "LatLonTools", Qgis.Info)
            result = self._try_existing_formats(text)
            if result:
                lat, lon, bounds, source_crs, description = result
                QgsMessageLog.logMessage(f"SmartParser.parse: PHASE 2 SUCCESS - {description}: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                return (lat, lon, bounds, source_crs)
            else:
                QgsMessageLog.logMessage("SmartParser.parse: PHASE 2 FAILED - No existing format match", "LatLonTools", Qgis.Warning)
            
            # Phase 3: Basic coordinate extraction
            QgsMessageLog.logMessage("SmartParser.parse: === PHASE 3: Trying basic coordinate extraction ===", "LatLonTools", Qgis.Info)
            result = self._extract_and_validate_coordinates(text)
            if result:
                lat, lon = result[0], result[1]
                QgsMessageLog.logMessage(f"SmartParser.parse: PHASE 3 SUCCESS - Basic coordinates: lat={lat}, lon={lon}", "LatLonTools", Qgis.Info)
                return (lat, lon, None, epsg4326)
            else:
                QgsMessageLog.logMessage("SmartParser.parse: PHASE 3 FAILED - No basic coordinate match", "LatLonTools", Qgis.Warning)
                
        except Exception as e:
            # Failed to parse - let caller handle fallback
            QgsMessageLog.logMessage(f"SmartParser.parse: EXCEPTION during parsing: {e}", "LatLonTools", Qgis.Critical)
            import traceback
            QgsMessageLog.logMessage(f"SmartParser.parse: Traceback: {traceback.format_exc()}", "LatLonTools", Qgis.Critical)
            return None
            
        QgsMessageLog.logMessage("SmartParser.parse: COMPLETE FAILURE - No format matched", "LatLonTools", Qgis.Critical)
        return None
            
    def _try_existing_formats(self, text):
        """
        Try existing coordinate formats
        Returns: (lat, lon, bounds, source_crs, description) or None
        """
        # Handle both plugin context (relative imports) and standalone testing (absolute imports)
        try:
            from .mgrs import toWgs
            from .pluscodes import olc
            from .utm import utm2Point, isUtm
            from .ups import ups2Point, isUps
            from .geohash import decode_exactly, decode_extent
            from . import georef
            from . import maidenhead
        except ImportError:
            from mgrs import toWgs
            from pluscodes import olc
            from utm import utm2Point, isUtm
            from ups import ups2Point, isUps
            from geohash import decode_exactly, decode_extent
            import georef
            import maidenhead
        
        # Import H3 with fallback
        try:
            try:
                from . import h3
            except ImportError:
                import h3
            has_h3 = True
        except ImportError:
            has_h3 = False
            
        text_upper = text.upper().strip()
        text_clean = re.sub(r'\s+', '', str(text))
        
        # Try MGRS coordinate
        mgrs_pattern = re.match(r'^\d{1,2}[A-Z]{3}\d+$', re.sub(r'\s+', '', text_upper))
        if mgrs_pattern:
            try:
                lat, lon = toWgs(text_clean)
                return (lat, lon, None, epsg4326, "MGRS")
            except Exception:
                pass
        
        # Try GEOREF coordinate
        georef_pattern = re.match(r'^[A-Z]{4}\d{2,}$', text_upper)
        if georef_pattern:
            try:
                (lat, lon, prec) = georef.decode(text, False)
                return (lat, lon, None, epsg4326, "GEOREF")
            except Exception:
                pass
        
        # Try Plus Codes
        plus_codes_patterns = [
            r'[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,}',
            r'[23456789CFGHJMPQRVWX]{6,8}\+[23456789CFGHJMPQRVWX]*',
            r'[23456789CFGHJMPQRVWX]{2,8}\+[23456789CFGHJMPQRVWX]{1,}'
        ]
        
        for pattern in plus_codes_patterns:
            if re.search(pattern, text_upper):
                try:
                    coord = olc.decode(text)
                    lat = coord.latitudeCenter
                    lon = coord.longitudeCenter
                    rect = QgsRectangle(coord.longitudeLo, coord.latitudeLo, coord.longitudeHi, coord.latitudeHi)
                    geom = QgsGeometry.fromRect(rect)
                    return (lat, lon, geom, epsg4326, "Plus Codes")
                except Exception:
                    continue
        
        # Try Maidenhead Grid
        maidenhead_pattern = re.match(r'^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$', text_upper)
        if maidenhead_pattern:
            try:
                (lat, lon, lat1, lon1, lat2, lon2) = maidenhead.maidenGrid(text)
                rect = QgsRectangle(lon1, lat1, lon2, lat2)
                geom = QgsGeometry.fromRect(rect)
                return (float(lat), float(lon), geom, epsg4326, "Maidenhead Grid")
            except Exception:
                pass
        
        # Try Geohash
        geohash_clean = re.sub(r'\s+', '', text.lower())
        geohash_pattern = re.match(r'^[0-9bcdefghjkmnpqrstuvwxyz]+$', geohash_clean)
        if (geohash_pattern and 
            3 <= len(geohash_clean) <= 12 and
            not mgrs_pattern and
            not georef_pattern and
            not maidenhead_pattern):
            try:
                (lat, lon, lat_err, lon_err) = decode_exactly(text)
                (lat1, lat2, lon1, lon2) = decode_extent(text)
                rect = QgsRectangle(lon1, lat1, lon2, lat2)
                geom = QgsGeometry.fromRect(rect)
                return (lat, lon, geom, epsg4326, "Geohash")
            except Exception:
                pass
            
        # Try UTM coordinate
        if isUtm(text):
            try:
                pt = utm2Point(text)
                lat, lon = pt.y(), pt.x()
                return (lat, lon, None, epsg4326, "Standard UTM")
            except Exception:
                # If UTM format is detected but parsing fails, reject it completely
                # Don't let it fall through to decimal parsing
                return None
                
        # Try UPS coordinate
        if isUps(text):
            try:
                pt = ups2Point(text)
                lat, lon = pt.y(), pt.x()
                return (lat, lon, None, epsg4326, "UPS")
            except Exception:
                # If UPS format is detected but parsing fails, reject it completely
                # Don't let it fall through to decimal parsing
                return None
            
        # Try H3 (if available)
        if has_h3:
            h3_pattern = re.match(r'^[0-9a-fA-F]{15}$', text_clean)
            if h3_pattern:
                try:
                    if h3.is_valid_cell(text):
                        (lat, lon) = h3.cell_to_latlng(text)
                        coords = h3.cell_to_boundary(text)
                        pts = []
                        for p in coords:
                            pt = QgsPointXY(p[1], p[0])
                            pts.append(pt)
                        pts.append(pts[0])
                        geom = QgsGeometry.fromPolylineXY(pts)
                        return (lat, lon, geom, epsg4326, "H3")
                except Exception:
                    pass
            
        # Try GeoJSON Point
        if text.strip().startswith('{'):
            try:
                if ('"type"' in text and '"coordinates"' in text) or '"Point"' in text:
                    codec = QTextCodec.codecForName("UTF-8")
                    fields = QgsJsonUtils.stringToFields(text, codec)
                    fet = QgsJsonUtils.stringToFeatureList(text, fields, codec)
                    if (len(fet) > 0) and fet[0].isValid():
                        geom = fet[0].geometry()
                        if not geom.isEmpty() and (geom.wkbType() == QgsWkbTypes.Point):
                            pt = geom.asPoint()
                            lat, lon = pt.y(), pt.x()
                            return (lat, lon, None, epsg4326, "GeoJSON Point")
            except Exception:
                pass
        
        # Try DMS format if it has indicators
        if self._has_dms_indicators(text):
            try:
                # Handle both plugin context and standalone testing
                try:
                    from .util import parseDMSString
                except ImportError:
                    from util import parseDMSString
                lat, lon = parseDMSString(text, self.settings.zoomToCoordOrder)
                return (lat, lon, None, epsg4326, "DMS")
            except Exception:
                pass
                
        return None
        
    def _extract_and_validate_coordinates(self, text):
        """Extract coordinates from text and validate"""
        # Extract all numbers from text
        numbers = self._extract_numbers(text)
        
        if len(numbers) < 2:
            raise ValueError(f"Need at least 2 numbers for coordinates, found {len(numbers)}")
        
        # Use first two coordinates
        coord1, coord2 = numbers[0], numbers[1]
        
        # Critical validation: Reject coordinates that look like UTM/projected values
        # that fell through format-specific parsing
        if self._looks_like_projected_coordinates(coord1, coord2, numbers):
            raise ValueError("Coordinates appear to be projected/UTM values, not geographic")
        
        # Validate coordinate order
        return self._validate_coordinate_order(coord1, coord2)
        
    def _looks_like_projected_coordinates(self, coord1, coord2, all_numbers):
        """Detect if coordinates look like UTM/projected values that shouldn't be treated as lat/lon"""
        
        def _is_valid_lat_lon_pair(c1, c2):
            """Check if coordinates could be a valid lat/lon pair in either order."""
            return ((-180 <= c1 <= 180 and -90 <= c2 <= 90) or 
                    (-180 <= c2 <= 180 and -90 <= c1 <= 90))
        
        # UTM coordinate detection logic
        # Note: This assumes typical patterns but doesn't rely on specific coordinate order
        # since we check both possible orientations
        
        # UTM easting: typically 100k-900k, northing: typically 0-10M
        # Check if either coordinate pair matches UTM ranges in either order
        utm_pattern_1 = (100000 <= abs(coord1) <= 900000 and 0 <= abs(coord2) <= 10000000)
        utm_pattern_2 = (100000 <= abs(coord2) <= 900000 and 0 <= abs(coord1) <= 10000000)
        
        # Check for UTM-like patterns in either coordinate order
        if utm_pattern_1 or utm_pattern_2:
            # Additional evidence: zone number (1-60) somewhere in the input
            has_zone_like_number = any(1 <= n <= 60 for n in all_numbers)
            if has_zone_like_number:
                return True
        
        # Large coordinate values that are clearly not geographic
        if abs(coord1) > 180 or abs(coord2) > 180:
            # Exception: allow obviously valid lat/lon in either order
            if _is_valid_lat_lon_pair(coord1, coord2):
                return False
            return True
            
        return False
        
    def _extract_numbers(self, text):
        """Extract all numeric values from text"""
        pattern = r'[-+]?\d*\.?\d+'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            if match and match not in ['.', '-', '+', '']:
                try:
                    num = float(match)
                    numbers.append(num)
                except ValueError:
                    continue
                    
        return numbers
        
    def _validate_coordinate_order(self, coord1, coord2):
        """Validate coordinates respecting user's X,Y button preference"""
        user_order = self.settings.zoomToCoordOrder
        
        # Check validity of both possible orders
        lat_lon_valid = self._is_valid_geographic(coord1, coord2)
        lon_lat_valid = self._is_valid_geographic(coord2, coord1)
        
        # If both orders are valid (ambiguous), use user preference
        if lat_lon_valid and lon_lat_valid:
            if user_order == CoordOrder.OrderYX:
                return (coord1, coord2)
            else:
                return (coord2, coord1)
        
        # Try user's preferred order first
        if user_order == CoordOrder.OrderYX:
            if lat_lon_valid:
                return (coord1, coord2)
        else:
            if lon_lat_valid:
                return (coord2, coord1)
        
        # Auto-correct: try opposite order
        if user_order == CoordOrder.OrderYX:
            if lon_lat_valid:
                return (coord2, coord1)
        else:
            if lat_lon_valid:
                return (coord1, coord2)
        
        # Both orders failed
        raise ValueError("Invalid coordinates in both Lat/Lon and Lon/Lat orders")
        
    def _is_valid_geographic(self, lat, lon):
        """Validate geographic coordinate ranges"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
    
    def _try_explicit_formats(self, text):
        """Parse WKT, EWKT, and WKB formats"""
        from qgis.core import QgsMessageLog, Qgis
        
        QgsMessageLog.logMessage(f"SmartParser._try_explicit_formats: Starting explicit format parsing", "LatLonTools", Qgis.Info)
        
        # Try EWKT first
        QgsMessageLog.logMessage("SmartParser._try_explicit_formats: Trying EWKT...", "LatLonTools", Qgis.Info)
        ewkt_result = self._try_ewkt(text)
        if ewkt_result:
            QgsMessageLog.logMessage(f"SmartParser._try_explicit_formats: EWKT SUCCESS: {ewkt_result}", "LatLonTools", Qgis.Info)
            return ewkt_result
        else:
            QgsMessageLog.logMessage("SmartParser._try_explicit_formats: EWKT failed", "LatLonTools", Qgis.Info)
            
        # Try WKB
        QgsMessageLog.logMessage("SmartParser._try_explicit_formats: Checking if input looks like WKB...", "LatLonTools", Qgis.Info)
        if self._is_potential_wkb(text):
            QgsMessageLog.logMessage("SmartParser._try_explicit_formats: Input looks like WKB, trying WKB parsing...", "LatLonTools", Qgis.Info)
            wkb_result = self._try_wkb(text)
            if wkb_result:
                QgsMessageLog.logMessage(f"SmartParser._try_explicit_formats: WKB SUCCESS: {wkb_result}", "LatLonTools", Qgis.Info)
                return wkb_result
            else:
                QgsMessageLog.logMessage("SmartParser._try_explicit_formats: WKB parsing failed despite looking like WKB!", "LatLonTools", Qgis.Critical)
        else:
            QgsMessageLog.logMessage("SmartParser._try_explicit_formats: Input does not look like WKB, skipping WKB parsing", "LatLonTools", Qgis.Info)
                
        # Try plain WKT
        QgsMessageLog.logMessage("SmartParser._try_explicit_formats: Trying plain WKT...", "LatLonTools", Qgis.Info)
        wkt_result = self._try_wkt(text)
        if wkt_result:
            QgsMessageLog.logMessage(f"SmartParser._try_explicit_formats: WKT SUCCESS: {wkt_result}", "LatLonTools", Qgis.Info)
            return wkt_result
        else:
            QgsMessageLog.logMessage("SmartParser._try_explicit_formats: WKT failed", "LatLonTools", Qgis.Info)
            
        QgsMessageLog.logMessage("SmartParser._try_explicit_formats: All explicit formats failed", "LatLonTools", Qgis.Warning)
        return None
        
    def _try_ewkt(self, text):
        """Parse EWKT format"""
        ewkt_match = re.match(r'SRID=(\d+);(.+)', text.strip(), re.IGNORECASE)
        if not ewkt_match:
            return None
            
        srid = int(ewkt_match.group(1))
        wkt_part = ewkt_match.group(2)
        
        source_crs = QgsCoordinateReferenceSystem.fromEpsgId(srid)
        if not source_crs.isValid():
            source_crs = epsg4326
        
        geom = QgsGeometry.fromWkt(wkt_part)
        if geom.isEmpty() or geom.isNull():
            return None
            
        return self._extract_point_from_geometry(geom, source_crs, f"EWKT (SRID={srid})")
        
    def _try_wkb(self, text):
        """Parse WKB format"""
        from qgis.core import QgsMessageLog, Qgis
        
        QgsMessageLog.logMessage(f"SmartParser._try_wkb: Starting WKB parsing for input: {text[:50]}...", "LatLonTools", Qgis.Info)
        
        try:
            hex_string = text.replace(' ', '').replace('\n', '').replace('\t', '')
            QgsMessageLog.logMessage(f"SmartParser._try_wkb: Cleaned hex string: {hex_string[:50]}...", "LatLonTools", Qgis.Info)
            
            wkb_bytes = bytes.fromhex(hex_string)
            QgsMessageLog.logMessage(f"SmartParser._try_wkb: Successfully converted to {len(wkb_bytes)} bytes", "LatLonTools", Qgis.Info)
            
            geom = QgsGeometry()
            geom.fromWkb(wkb_bytes)
            QgsMessageLog.logMessage(f"SmartParser._try_wkb: QGIS geometry created, isEmpty: {geom.isEmpty()}, isNull: {geom.isNull()}", "LatLonTools", Qgis.Info)
            
            # If QGIS parsing succeeded, use it
            if not (geom.isEmpty() or geom.isNull()):
                QgsMessageLog.logMessage("SmartParser._try_wkb: QGIS parsing succeeded, extracting SRID and coordinates", "LatLonTools", Qgis.Info)
                import struct
                byte_order = struct.unpack('<B' if wkb_bytes[0] == 1 else '>B', wkb_bytes[0:1])[0]
                endian = '<' if byte_order == 1 else '>'
                geom_type = struct.unpack(f'{endian}I', wkb_bytes[1:5])[0]
                QgsMessageLog.logMessage(f"SmartParser._try_wkb: Geometry type: 0x{geom_type:08X}", "LatLonTools", Qgis.Info)
                
                # Check if SRID flag is set (0x20000000 bit)
                has_srid = bool(geom_type & 0x20000000)
                QgsMessageLog.logMessage(f"SmartParser._try_wkb: Has SRID flag: {has_srid}", "LatLonTools", Qgis.Info)
                
                if has_srid:
                    # WKB contains SRID, extract it
                    srid = struct.unpack(f'{endian}I', wkb_bytes[5:9])[0]
                    QgsMessageLog.logMessage(f"SmartParser._try_wkb: Extracted SRID: {srid}", "LatLonTools", Qgis.Info)
                    try:
                        source_crs = QgsCoordinateReferenceSystem(f'EPSG:{srid}')
                        if not source_crs.isValid():
                            QgsMessageLog.logMessage(f"SmartParser._try_wkb: SRID {srid} not valid, using EPSG:4326", "LatLonTools", Qgis.Warning)
                            source_crs = epsg4326
                        else:
                            QgsMessageLog.logMessage(f"SmartParser._try_wkb: Valid CRS created for SRID {srid}", "LatLonTools", Qgis.Info)
                    except Exception as e:
                        QgsMessageLog.logMessage(f"SmartParser._try_wkb: Exception creating CRS for SRID {srid}: {e}", "LatLonTools", Qgis.Warning)
                        source_crs = epsg4326
                else:
                    QgsMessageLog.logMessage("SmartParser._try_wkb: No SRID flag, using EPSG:4326", "LatLonTools", Qgis.Info)
                    source_crs = epsg4326
                    
                result = self._extract_point_from_geometry(geom, source_crs, "WKB")
                QgsMessageLog.logMessage(f"SmartParser._try_wkb: QGIS path result: {result}", "LatLonTools", Qgis.Info)
                return result
            
            # QGIS parsing failed - try manual parsing for non-standard WKB
            QgsMessageLog.logMessage("SmartParser._try_wkb: QGIS parsing failed, trying manual parsing", "LatLonTools", Qgis.Warning)
            result = self._try_manual_wkb_parsing(wkb_bytes)
            QgsMessageLog.logMessage(f"SmartParser._try_wkb: Manual parsing result: {result}", "LatLonTools", Qgis.Info)
            return result
            
        except Exception as e:
            QgsMessageLog.logMessage(f"SmartParser._try_wkb: Exception during WKB parsing: {e}", "LatLonTools", Qgis.Critical)
            import traceback
            QgsMessageLog.logMessage(f"SmartParser._try_wkb: Traceback: {traceback.format_exc()}", "LatLonTools", Qgis.Critical)
            return None

    def _try_manual_wkb_parsing(self, wkb_bytes):
        """Manual WKB parsing for non-standard formats that QGIS can't handle"""
        from qgis.core import QgsMessageLog, Qgis
        
        QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Starting manual WKB parsing for {len(wkb_bytes)} bytes", "LatLonTools", Qgis.Info)
        
        try:
            import struct
            
            if len(wkb_bytes) < 21:  # Minimum for Point: 1+4+8+8 = 21 bytes
                QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Insufficient bytes: {len(wkb_bytes)} < 21", "LatLonTools", Qgis.Warning)
                return None
                
            # Parse endianness
            endian = '<' if wkb_bytes[0] == 1 else '>'
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Endianness: {endian}", "LatLonTools", Qgis.Info)
            
            # Parse geometry type (with potential flags)
            geom_type = struct.unpack(f'{endian}I', wkb_bytes[1:5])[0]
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Raw geometry type: 0x{geom_type:08X}", "LatLonTools", Qgis.Info)
            
            # Check flags
            has_srid = bool(geom_type & 0x20000000)
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Has SRID: {has_srid}", "LatLonTools", Qgis.Info)
            
            # Remove SRID flag to get actual geometry type
            actual_geom_type = geom_type & ~0x20000000
            has_z = bool(actual_geom_type & 0x80000000) 
            has_m = bool(actual_geom_type & 0x40000000)
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Has Z: {has_z}, Has M: {has_m}", "LatLonTools", Qgis.Info)
            
            # Get base geometry type
            base_type = actual_geom_type & 0xFF
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Base geometry type: {base_type} (expected: {self.WKB_POINT_TYPE})", "LatLonTools", Qgis.Info)
            
            if base_type != self.WKB_POINT_TYPE:  # Not a Point
                QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Not a point geometry: {base_type}", "LatLonTools", Qgis.Warning)
                return None
                
            offset = 5  # Start after geometry type
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Starting coordinate parsing at offset {offset}", "LatLonTools", Qgis.Info)
            
            # Parse SRID if present
            srid = None
            if has_srid:
                if len(wkb_bytes) < offset + 4:
                    QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Insufficient bytes for SRID at offset {offset}", "LatLonTools", Qgis.Warning)
                    return None
                srid = struct.unpack(f'{endian}I', wkb_bytes[offset:offset+4])[0]
                QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Parsed SRID: {srid}", "LatLonTools", Qgis.Info)
                offset += 4
            
            # Parse coordinates - need at least X, Y (16 bytes)
            coord_size = 16  # X, Y (8 bytes each)
            if has_z:
                coord_size += 8
                QgsMessageLog.logMessage("SmartParser._try_manual_wkb_parsing: Adding 8 bytes for Z coordinate", "LatLonTools", Qgis.Info)
            if has_m: 
                coord_size += 8
                QgsMessageLog.logMessage("SmartParser._try_manual_wkb_parsing: Adding 8 bytes for M coordinate", "LatLonTools", Qgis.Info)
                
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Need {coord_size} bytes for coordinates, have {len(wkb_bytes) - offset} remaining", "LatLonTools", Qgis.Info)
                
            if len(wkb_bytes) < offset + coord_size:
                QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Insufficient bytes for coordinates: need {coord_size}, have {len(wkb_bytes) - offset}", "LatLonTools", Qgis.Warning)
                return None
                
            # Extract coordinates
            x = struct.unpack(f'{endian}d', wkb_bytes[offset:offset+8])[0]
            y = struct.unpack(f'{endian}d', wkb_bytes[offset+8:offset+16])[0]
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Parsed X: {x}, Y: {y}", "LatLonTools", Qgis.Info)
            offset += 16
            
            z = None
            if has_z:
                z = struct.unpack(f'{endian}d', wkb_bytes[offset:offset+8])[0]
                QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Parsed Z: {z}", "LatLonTools", Qgis.Info)
                offset += 8
                
            # Skip M coordinate if present (we don't use it)
            
            # Create CRS - handle PROJ database issues gracefully
            source_crs = None
            if srid:
                QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Attempting to create CRS for SRID {srid}", "LatLonTools", Qgis.Info)
                try:
                    from qgis.core import QgsCoordinateReferenceSystem
                    source_crs = QgsCoordinateReferenceSystem(f'EPSG:{srid}')
                    if source_crs.isValid():
                        QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Valid CRS created for SRID {srid}: {source_crs.authid()}", "LatLonTools", Qgis.Info)
                    else:
                        QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: SRID {srid} not valid, will use None CRS", "LatLonTools", Qgis.Warning)
                        source_crs = None
                except Exception as e:
                    QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Exception creating CRS for SRID {srid}: {e}", "LatLonTools", Qgis.Warning)
                    source_crs = None
            
            if source_crs is None:
                QgsMessageLog.logMessage("SmartParser._try_manual_wkb_parsing: Using None CRS (fallback for PROJ issues)", "LatLonTools", Qgis.Info)
            
            # Return tuple format: (lat, lon, bounds, source_crs) to match other parsing methods
            # Use None for CRS if we can't create a valid one due to PROJ database issues
            result = (y, x, None, source_crs)
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: SUCCESS - Returning: lat={y}, lon={x}, CRS={source_crs.authid() if source_crs and source_crs.isValid() else 'None'}", "LatLonTools", Qgis.Info)
            return result
            
        except Exception as e:
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Exception during manual parsing: {e}", "LatLonTools", Qgis.Critical)
            import traceback
            QgsMessageLog.logMessage(f"SmartParser._try_manual_wkb_parsing: Traceback: {traceback.format_exc()}", "LatLonTools", Qgis.Critical)
            return None
            
    def _try_wkt(self, text):
        """Parse plain WKT format"""
        wkt_patterns = [
            r'POINT\s*Z?\s*M?\s*\(\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(?:\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)*\s*\)',
            r'MULTIPOINT\s*\(\s*\(\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(?:\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)*\s*\)\s*\)',
            r'POLYGON\s*\(\s*\(\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?(?:\s*,\s*[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?\s+[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)*\s*\)\s*\)'
        ]
        
        for pattern in wkt_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                wkt_geom = match.group(0)
                
                if not self._is_complete_wkt(wkt_geom):
                    continue
                
                geom = QgsGeometry.fromWkt(wkt_geom)
                if geom.isEmpty() or geom.isNull():
                    continue
                    
                return self._extract_point_from_geometry(geom, epsg4326, "WKT")
                
        return None
        
    def _extract_point_from_geometry(self, geom, source_crs, description):
        """Extract lat/lon from QGIS geometry"""
        # Convert to point if needed
        if geom.type() != QgsWkbTypes.PointGeometry:
            if geom.type() == QgsWkbTypes.LineGeometry or geom.type() == QgsWkbTypes.PolygonGeometry:
                geom = geom.centroid()
            else:
                return None
        
        point = geom.asPoint()
        source_x, source_y = point.x(), point.y()
        
        # Apply coordinate order validation for geographic CRS
        if source_crs.isGeographic():
            corrected_x, corrected_y = self._validate_geometry_coordinate_order(source_x, source_y, source_crs)
            point = QgsPointXY(corrected_x, corrected_y)
            source_x, source_y = corrected_x, corrected_y
        
        # Transform to WGS84 if needed
        if source_crs.authid() != 'EPSG:4326':
            try:
                transform = QgsCoordinateTransform(source_crs, epsg4326, QgsProject.instance())
                transformed_point = transform.transform(point)
                final_lat, final_lon = transformed_point.y(), transformed_point.x()
            except Exception:
                return None
        else:
            final_lat, final_lon = source_y, source_x
        
        return (final_lat, final_lon, epsg4326, description)
        
    def _validate_geometry_coordinate_order(self, x, y, source_crs):
        """Validate and potentially correct coordinate order for WKT/EWKT/WKB geometries"""
        if not source_crs.isGeographic():
            return x, y
            
        # For geographic CRS, standard WKT format is: POINT(longitude latitude)
        standard_valid = self._is_valid_geographic(y, x)  # Y=lat, X=lon
        flipped_valid = self._is_valid_geographic(x, y)   # X=lat, Y=lon
        
        # Use standard order if both are valid or only standard is valid
        if standard_valid and flipped_valid:
            return x, y
        if standard_valid and not flipped_valid:
            return x, y
            
        # Auto-correct if only flipped order is valid
        if not standard_valid and flipped_valid:
            return y, x
            
        # Both invalid - return original
        return x, y
    
    def _is_potential_wkb(self, text):
        """Check if text looks like WKB"""
        from qgis.core import QgsMessageLog, Qgis
        
        clean_text = text.replace(' ', '').replace('\n', '').replace('\t', '')
        QgsMessageLog.logMessage(f"SmartParser._is_potential_wkb: Checking if '{text[:50]}...' looks like WKB", "LatLonTools", Qgis.Info)
        QgsMessageLog.logMessage(f"SmartParser._is_potential_wkb: Clean text: '{clean_text[:50]}...', length: {len(clean_text)}", "LatLonTools", Qgis.Info)
        
        # Check if it's all hex characters
        hex_match = re.match(r'^[0-9A-Fa-f]+$', clean_text)
        is_hex = hex_match is not None
        QgsMessageLog.logMessage(f"SmartParser._is_potential_wkb: Is valid hex: {is_hex}", "LatLonTools", Qgis.Info)
        
        # Check minimum length
        min_length_ok = len(clean_text) >= 20
        QgsMessageLog.logMessage(f"SmartParser._is_potential_wkb: Meets minimum length (>= 20): {min_length_ok}", "LatLonTools", Qgis.Info)
        
        result = is_hex and min_length_ok
        QgsMessageLog.logMessage(f"SmartParser._is_potential_wkb: RESULT: {result}", "LatLonTools", Qgis.Info)
        return result
        
    def _is_complete_wkt(self, wkt_text):
        """Check if WKT geometry is syntactically complete"""
        if not wkt_text or not isinstance(wkt_text, str):
            return False
            
        wkt_upper = wkt_text.upper().strip()
        
        # Check balanced parentheses
        open_count = wkt_upper.count('(')
        close_count = wkt_upper.count(')')
        if open_count != close_count or open_count == 0:
            return False
            
        # Check for coordinates
        coord_pattern = r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?'
        coordinates = re.findall(coord_pattern, wkt_text)
        return len(coordinates) >= 2
        
    def _has_dms_indicators(self, text):
        """Check if text has DMS (Degrees Minutes Seconds) indicators"""
        # Strong DMS patterns
        strong_dms_patterns = [
            r'\d+\s*[°]\s*\d+\s*[′\']\s*[\d.]+\s*[″"]',  # Full DMS
            r'\d+\s*[°]\s*[\d.]+\s*[′\']',               # Degree-minute
            r'\d+\s*[°]\s*[\d.]+\s*[″"]',                # Degree-second
            r'[NSEW]\s*\d+[°′″\'"]',                     # Cardinal with symbols
            r'\d+[°′″\'"]\s*[NSEW]',                     # Symbols with cardinal
            r'\d+\s*[°′″\'"]\s*\d+\s*[°′″\'"]',         # Multiple symbols
            r'[\d.]+\s*[°]\s*[\d.-]+\s*[°]',            # Decimal with degrees
        ]
        
        for pattern in strong_dms_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for cardinal directions in coordinate context
        if re.search(r'[NSEW]', text):
            has_numbers = re.search(r'\d', text)
            has_coordinate_structure = (
                re.search(r'[NSEW]\s*\d', text) or
                re.search(r'\d\s*[NSEW]', text) or
                re.search(r'[NSEW]\d+\.\d+', text) or
                re.search(r'\d+\.\d+\s*[NSEW]', text)
            )
            
            if has_numbers and has_coordinate_structure:
                # Avoid false positives
                false_positive_patterns = [
                    r'^[a-z0-9]+$',           # Geohash
                    r'^[A-Z]{2}\d{2}[A-Z]*', # Maidenhead
                    r'POINT\s*\(',            # WKT
                    r'SRID=',                 # EWKT
                ]
                
                for false_pattern in false_positive_patterns:
                    if re.search(false_pattern, text, re.IGNORECASE):
                        return False
                
                return True
        
        return False
