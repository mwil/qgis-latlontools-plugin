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
from .util import epsg4326, tr
from .settings import CoordOrder


class SmartCoordinateParser:
    """
    Smart coordinate parser - handles any coordinate input format
    Supports WKT, EWKT, WKB, MGRS, Plus Codes, UTM, UPS, Geohash, 
    Maidenhead Grid, H3, GeoJSON, DMS, and decimal coordinates
    """
    
    def __init__(self, settings_obj, iface):
        self.settings = settings_obj
        self.iface = iface
        
    def parse(self, text):
        """
        Main parsing entry point
        Returns: (lat, lon, bounds, source_crs) or None if parsing fails
        """
        original_text = text.strip()
        
        try:
            # Phase 1: Explicit formats (WKT, EWKT, WKB)
            result = self._try_explicit_formats(text)
            if result:
                lat, lon, source_crs, description = result
                return (lat, lon, None, source_crs)
            
            # Phase 2: Existing formats (MGRS, UTM, etc.)
            result = self._try_existing_formats(text)
            if result:
                lat, lon, bounds, source_crs, description = result
                return (lat, lon, bounds, source_crs)
            
            # Phase 3: Basic coordinate extraction
            result = self._extract_and_validate_coordinates(text)
            if result:
                lat, lon = result[0], result[1]
                return (lat, lon, None, epsg4326)
                
        except Exception:
            # Failed to parse - let caller handle fallback
            return None
            
    def _try_existing_formats(self, text):
        """
        Try existing coordinate formats
        Returns: (lat, lon, bounds, source_crs, description) or None
        """
        from .mgrs import toWgs
        from .pluscodes import olc
        from .utm import utm2Point, isUtm
        from .ups import ups2Point, isUps
        from .geohash import decode_exactly, decode_extent
        from . import georef
        from . import maidenhead
        
        # Import H3 with fallback
        try:
            from . import h3
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
                pass
                
        # Try UPS coordinate
        if isUps(text):
            try:
                pt = ups2Point(text)
                lat, lon = pt.y(), pt.x()
                return (lat, lon, None, epsg4326, "UPS")
            except Exception:
                pass
            
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
                from .util import parseDMSString
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
        
        # Validate coordinate order
        return self._validate_coordinate_order(coord1, coord2)
        
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
        # Try EWKT first
        ewkt_result = self._try_ewkt(text)
        if ewkt_result:
            return ewkt_result
            
        # Try WKB
        if self._is_potential_wkb(text):
            wkb_result = self._try_wkb(text)
            if wkb_result:
                return wkb_result
                
        # Try plain WKT
        wkt_result = self._try_wkt(text)
        if wkt_result:
            return wkt_result
            
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
        try:
            hex_string = text.replace(' ', '').replace('\n', '').replace('\t', '')
            wkb_bytes = bytes.fromhex(hex_string)
            
            geom = QgsGeometry()
            geom.fromWkb(wkb_bytes)
            
            if geom.isEmpty() or geom.isNull():
                return None
            
            # Check if WKB contains SRID by examining geometry type
            import struct
            byte_order = struct.unpack('<B' if wkb_bytes[0] == 1 else '>B', wkb_bytes[0:1])[0]
            endian = '<' if byte_order == 1 else '>'
            geom_type = struct.unpack(f'{endian}I', wkb_bytes[1:5])[0]
            
            # Check if SRID flag is set (0x20000000 bit)
            has_srid = bool(geom_type & 0x20000000)
            
            if has_srid:
                # WKB contains SRID, extract it
                srid = struct.unpack(f'{endian}I', wkb_bytes[5:9])[0]
                try:
                    source_crs = QgsCoordinateReferenceSystem(f'EPSG:{srid}')
                    if not source_crs.isValid():
                        # Invalid SRID, fall back to WGS84
                        source_crs = epsg4326
                except Exception:
                    source_crs = epsg4326
            else:
                # No SRID in WKB - assume WGS84 (standard convention)
                # Most WKB without SRID represents WGS84 lat/lon coordinates
                source_crs = epsg4326
                
            return self._extract_point_from_geometry(geom, source_crs, "WKB")
            
        except Exception:
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
        clean_text = text.replace(' ', '').replace('\n', '').replace('\t', '')
        return re.match(r'^[0-9A-Fa-f]+$', clean_text) and len(clean_text) >= 20
        
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