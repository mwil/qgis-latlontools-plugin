"""
Smart coordinate parser module - Refactored using Strategy Pattern
Implements intelligent coordinate detection and parsing for any input format
"""

import re
from abc import ABC, abstractmethod
from qgis.core import (
    QgsGeometry,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsWkbTypes,
    QgsRectangle,
    QgsPointXY,
    QgsJsonUtils,
    QgsMessageLog,
    Qgis,
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


class CoordinateParserStrategy(ABC):
    """Base strategy for coordinate parsing - try-parse architecture"""

    @abstractmethod
    def parse(self, text: str) -> tuple:
        """
        Parse coordinate, return (lat, lon, bounds, crs, description) or None

        Should attempt parsing and return None if parsing fails.
        Let underlying parsing libraries handle their own validation.
        No pre-validation with regex - just try to parse and catch exceptions.
        """
        pass

    def can_parse(self, text: str) -> bool:
        """
        Fast-path check if this strategy can potentially parse the text.
        Returns True if the text matches the expected format pattern.
        Default implementation returns True (try parsing).
        """
        return True

    def _log_debug(self, message: str):
        """Helper for consistent logging"""
        QgsMessageLog.logMessage(
            f"{self.__class__.__name__}: {message}", "LatLonTools", Qgis.Info
        )


class WktParserStrategy(CoordinateParserStrategy):
    """WKT (Well-Known Text) coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like WKT geometry"""
        text_upper = text.upper().strip()
        # Check for WKT geometry type keywords
        wkt_keywords = [
            "POINT",
            "LINESTRING",
            "POLYGON",
            "MULTIPOINT",
            "MULTILINESTRING",
            "MULTIPOLYGON",
            "GEOMETRYCOLLECTION",
            "CIRCULARSTRING",
            "COMPOUNDCURVE",
            "CURVEPOLYGON",
            "MULTICURVE",
            "MULTISURFACE",
            "CURVE",
            "SURFACE",
            "POLYHEDRALSURFACE",
            "TIN",
            "TRIANGLE",
        ]
        return any(keyword in text_upper for keyword in wkt_keywords)

    def parse(self, text: str) -> tuple:
        """Parse WKT coordinate - let QGIS library handle validation"""
        try:
            # Handle SRID=xxx;POINT(...) format
            source_crs = epsg4326
            wkt_text = text

            if text.upper().startswith("SRID=") and ";" in text:
                parts = text.split(";", 1)
                srid_part = parts[0].strip()
                wkt_text = parts[1].strip()

                # Extract SRID
                srid_match = re.search(r"SRID=(\d+)", srid_part.upper())
                if srid_match:
                    srid = int(srid_match.group(1))
                    source_crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")

            # Let QGIS handle WKT validation
            geom = QgsGeometry.fromWkt(wkt_text)
            if not geom.isEmpty():
                if geom.type() == QgsWkbTypes.PointGeometry:
                    pt = geom.asPoint()
                    lat, lon = pt.y(), pt.x()
                else:
                    # For non-point geometries, use centroid
                    centroid = geom.centroid()
                    if not centroid.isEmpty():
                        pt = centroid.asPoint()
                        lat, lon = pt.y(), pt.x()
                    else:
                        return None

                # Transform to WGS84 if needed
                if source_crs.isValid() and source_crs != epsg4326:
                    try:
                        transform = QgsCoordinateTransform(
                            source_crs, epsg4326, QgsProject.instance()
                        )
                        wgs84_point = transform.transform(pt)
                        lat, lon = wgs84_point.y(), wgs84_point.x()
                    except Exception as e:
                        self._log_debug(f"CRS transformation failed: {e}")

                self._log_debug(f"WKT parsed: {text} → lat={lat}, lon={lon}")
                return (lat, lon, None, epsg4326, "WKT")
        except Exception as e:
            self._log_debug(f"WKT parsing failed: {e}")
        return None


class EwktParserStrategy(CoordinateParserStrategy):
    """EWKT (Extended Well-Known Text) coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like EWKT with SRID"""
        text_upper = text.upper().strip()
        return text_upper.startswith("SRID=") and ";" in text_upper

    def parse(self, text: str) -> tuple:
        """Parse EWKT coordinate"""
        try:
            # Split SRID and WKT parts
            if "SRID=" in text.upper() and ";" in text:
                parts = text.split(";", 1)
                srid_part = parts[0].strip()
                wkt_part = parts[1].strip()

                # Extract SRID
                srid_match = re.search(r"SRID=(\d+)", srid_part.upper())
                if srid_match:
                    srid = int(srid_match.group(1))
                    source_crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")

                    # Parse WKT geometry
                    geom = QgsGeometry.fromWkt(wkt_part)
                    if not geom.isEmpty() and geom.type() == QgsWkbTypes.PointGeometry:
                        pt = geom.asPoint()
                        lat, lon = pt.y(), pt.x()

                        # Transform to WGS84 if needed
                        if source_crs.isValid() and source_crs != epsg4326:
                            try:
                                transform = QgsCoordinateTransform(
                                    source_crs, epsg4326, QgsProject.instance()
                                )
                                wgs84_point = transform.transform(pt)
                                lat, lon = wgs84_point.y(), wgs84_point.x()
                            except Exception as e:
                                self._log_debug(f"CRS transformation failed: {e}")

                        self._log_debug(f"EWKT parsed: {text} → lat={lat}, lon={lon}")
                        return (lat, lon, None, epsg4326, "EWKT")

            # Also try parsing as regular WKT with SRID prefix
            geom = QgsGeometry.fromWkt(text)
            if not geom.isEmpty() and geom.type() == QgsWkbTypes.PointGeometry:
                pt = geom.asPoint()
                lat, lon = pt.y(), pt.x()
                self._log_debug(f"EWKT (as WKT) parsed: {text} → lat={lat}, lon={lon}")
                return (lat, lon, None, epsg4326, "EWKT")

        except Exception as e:
            self._log_debug(f"EWKT parsing failed: {e}")
        return None


class WkbParserStrategy(CoordinateParserStrategy):
    """WKB (Well-Known Binary) coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like WKB hex string"""
        text_clean = text.strip().replace(" ", "")
        return (
            len(text_clean) >= 20
            and len(text_clean) % 2 == 0
            and all(c in "0123456789ABCDEFabcdef" for c in text_clean)
        )

    def parse(self, text: str) -> tuple:
        """Parse WKB coordinate"""
        try:
            # First try QGIS built-in WKB parsing
            geom = QgsGeometry()
            geom.fromWkb(bytes.fromhex(text.strip()))

            if not geom.isEmpty() and geom.type() == QgsWkbTypes.PointGeometry:
                pt = geom.asPoint()
                lat, lon = pt.y(), pt.x()
                self._log_debug(
                    f"WKB parsed with QGIS: {text[:20]}... → lat={lat}, lon={lon}"
                )
                return (lat, lon, None, epsg4326, "WKB")
        except Exception:
            pass

        # Fall back to manual parsing
        try:
            return self._manual_wkb_parsing(text)
        except Exception as e:
            self._log_debug(f"WKB parsing failed: {e}")
        return None

    def _manual_wkb_parsing(self, hex_string: str) -> tuple:
        """Manual WKB parsing with SRID and Z coordinate support"""
        hex_clean = hex_string.strip().replace(" ", "").upper()

        if len(hex_clean) < 40:  # Minimum for Point hex: 20 bytes = 40 hex chars
            return None

        # Convert hex to bytes
        try:
            wkb_bytes = bytes.fromhex(hex_clean)
        except ValueError:
            return None

        try:
            import struct

            if len(wkb_bytes) < 21:  # Minimum for Point: 1+4+8+8 = 21 bytes
                self._log_debug(f"Insufficient bytes: {len(wkb_bytes)} < 21")
                return None

            # Parse endianness
            endian = "<" if wkb_bytes[0] == 1 else ">"
            self._log_debug(f"Endianness: {endian}")

            # Parse geometry type (with potential flags)
            geom_type = struct.unpack(f"{endian}I", wkb_bytes[1:5])[0]
            self._log_debug(f"Raw geometry type: 0x{geom_type:08X}")

            # Check flags
            has_srid = bool(geom_type & 0x20000000)
            self._log_debug(f"Has SRID: {has_srid}")

            # Remove SRID flag to get actual geometry type
            actual_geom_type = geom_type & ~0x20000000
            has_z = bool(actual_geom_type & 0x80000000)
            has_m = bool(actual_geom_type & 0x40000000)
            self._log_debug(f"Has Z: {has_z}, Has M: {has_m}")

            # Get base geometry type
            base_type = actual_geom_type & 0xFF
            self._log_debug(f"Base geometry type: {base_type} (expected: 1 for Point)")

            if base_type != 1:  # Not a Point
                self._log_debug(f"Not a point geometry: {base_type}")
                return None

            offset = 5  # Start after geometry type
            self._log_debug(f"Starting coordinate parsing at offset {offset}")

            # Parse SRID if present
            srid = None
            source_crs = epsg4326
            if has_srid:
                if len(wkb_bytes) < offset + 4:
                    self._log_debug(f"Insufficient bytes for SRID at offset {offset}")
                    return None
                srid = struct.unpack(f"{endian}I", wkb_bytes[offset : offset + 4])[0]
                self._log_debug(f"Parsed SRID: {srid}")
                offset += 4

                # Create CRS - handle PROJ database issues gracefully
                try:
                    source_crs = QgsCoordinateReferenceSystem(f"EPSG:{srid}")
                    if not source_crs.isValid():
                        self._log_debug(f"SRID {srid} not valid, using WGS84 fallback")
                        source_crs = epsg4326
                except Exception as e:
                    self._log_debug(f"Exception creating CRS for SRID {srid}: {e}")
                    source_crs = epsg4326

            # Parse coordinates - need at least X, Y (16 bytes)
            coord_size = 16  # X, Y (8 bytes each)
            if has_z:
                coord_size += 8
                self._log_debug("Adding 8 bytes for Z coordinate")
            if has_m:
                coord_size += 8
                self._log_debug("Adding 8 bytes for M coordinate")

            self._log_debug(
                f"Need {coord_size} bytes for coordinates, have {len(wkb_bytes) - offset} remaining"
            )

            if len(wkb_bytes) < offset + coord_size:
                self._log_debug(
                    f"Insufficient bytes for coordinates: need {coord_size}, have {len(wkb_bytes) - offset}"
                )
                return None

            # Extract coordinates
            x = struct.unpack(f"{endian}d", wkb_bytes[offset : offset + 8])[0]
            y = struct.unpack(f"{endian}d", wkb_bytes[offset + 8 : offset + 16])[0]
            self._log_debug(f"Parsed X: {x}, Y: {y}")
            offset += 16

            z = None
            if has_z:
                z = struct.unpack(f"{endian}d", wkb_bytes[offset : offset + 8])[0]
                self._log_debug(f"Parsed Z: {z}")
                offset += 8

            # Skip M coordinate if present (we don't use it)

            # Return coordinates in lat, lon order (y, x)
            self._log_debug(f"WKB manual parsing SUCCESS: lat={y}, lon={x}")
            return (y, x, None, source_crs, "WKB")

        except Exception as e:
            self._log_debug(f"Manual WKB parsing exception: {e}")
            return None


class MgrsParserStrategy(CoordinateParserStrategy):
    """MGRS coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like MGRS coordinate"""
        # MGRS format: Zone (1-2 digits) + Grid letter (A-Z, excluding I, O) + grid letters/digits
        # Examples: 4QFJ12345678, 4Q FJ 12345 67890
        text_clean = re.sub(r"\s+", "", text.upper())
        # Pattern: 1-2 digit zone + letter + 2-3 grid letters + even number of digits
        mgrs_pattern = r"^\d{1,2}[C-HJ-NP-X][A-HJ-NP-Z]{2,}\d{2,}$"
        return bool(re.match(mgrs_pattern, text_clean))

    def parse(self, text: str) -> tuple:
        """Parse MGRS coordinate - let mature MGRS library handle validation"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from .mgrs import toWgs
            except ImportError:
                from mgrs import toWgs

            # Clean input and let library validate format
            text_clean = re.sub(r"\s+", "", text)
            lat, lon = toWgs(text_clean)
            self._log_debug(f"MGRS parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, None, epsg4326, "MGRS")
        except Exception as e:
            self._log_debug(f"MGRS parsing failed: {e}")
        return None


class GeorefParserStrategy(CoordinateParserStrategy):
    """GEOREF coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like GEOREF"""
        return bool(re.match(r"^[A-Z]{4}\d{2,}$", text.upper()))

    def parse(self, text: str) -> tuple:
        """Parse GEOREF coordinate"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from . import georef
            except ImportError:
                import georef

            lat, lon, prec = georef.decode(text, False)
            self._log_debug(f"GEOREF parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, None, epsg4326, "GEOREF")
        except Exception as e:
            self._log_debug(f"GEOREF parsing failed: {e}")
        return None


class PlusCodesParserStrategy(CoordinateParserStrategy):
    """Plus Codes (Open Location Code) parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like Plus Codes"""
        text_upper = text.upper()
        patterns = [
            r"[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,}",
            r"[23456789CFGHJMPQRVWX]{6,8}\+[23456789CFGHJMPQRVWX]*",
            r"[23456789CFGHJMPQRVWX]{2,8}\+[23456789CFGHJMPQRVWX]{1,}",
        ]
        return any(re.search(pattern, text_upper) for pattern in patterns)

    def parse(self, text: str) -> tuple:
        """Parse Plus Codes coordinate"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from .pluscodes import olc
            except ImportError:
                from pluscodes import olc

            coord = olc.decode(text)
            lat = coord.latitudeCenter
            lon = coord.longitudeCenter
            rect = QgsRectangle(
                coord.longitudeLo, coord.latitudeLo, coord.longitudeHi, coord.latitudeHi
            )
            geom = QgsGeometry.fromRect(rect)
            self._log_debug(f"Plus Codes parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, geom, epsg4326, "Plus Codes")
        except Exception as e:
            self._log_debug(f"Plus Codes parsing failed: {e}")
        return None


class MaidenheadParserStrategy(CoordinateParserStrategy):
    """Maidenhead Grid parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like Maidenhead Grid"""
        return bool(re.match(r"^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$", text.upper()))

    def parse(self, text: str) -> tuple:
        """Parse Maidenhead Grid coordinate"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from . import maidenhead
            except ImportError:
                import maidenhead

            lat, lon, lat1, lon1, lat2, lon2 = maidenhead.maidenGrid(text)
            rect = QgsRectangle(lon1, lat1, lon2, lat2)
            geom = QgsGeometry.fromRect(rect)
            self._log_debug(f"Maidenhead parsed: {text} → lat={lat}, lon={lon}")
            return (float(lat), float(lon), geom, epsg4326, "Maidenhead Grid")
        except Exception as e:
            self._log_debug(f"Maidenhead parsing failed: {e}")
        return None


class GeohashParserStrategy(CoordinateParserStrategy):
    """Geohash coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like Geohash"""
        text_clean = re.sub(r"\s+", "", text.lower())
        return (
            bool(re.match(r"^[0-9bcdefghjkmnpqrstuvwxyz]+$", text_clean))
            and 3 <= len(text_clean) <= 12
        )

    def parse(self, text: str) -> tuple:
        """Parse Geohash coordinate"""
        # Additional validation to avoid conflicts
        text_upper = text.upper().strip()

        # Skip if it matches other format patterns
        if (
            re.match(r"^\d{1,2}[A-Z]{3}\d+$", re.sub(r"\s+", "", text_upper))  # MGRS
            or re.match(r"^[A-Z]{4}\d{2,}$", text_upper)  # GEOREF
            or re.match(r"^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$", text_upper)
        ):  # Maidenhead
            return None

        try:
            # Handle both plugin context and standalone testing
            try:
                from .geohash import decode_exactly, decode_extent
            except ImportError:
                from geohash import decode_exactly, decode_extent

            lat, lon, lat_err, lon_err = decode_exactly(text)
            lat1, lat2, lon1, lon2 = decode_extent(text)
            rect = QgsRectangle(lon1, lat1, lon2, lat2)
            geom = QgsGeometry.fromRect(rect)
            self._log_debug(f"Geohash parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, geom, epsg4326, "Geohash")
        except Exception as e:
            self._log_debug(f"Geohash parsing failed: {e}")
        return None


class UtmParserStrategy(CoordinateParserStrategy):
    """UTM coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like UTM coordinate"""
        # UTM format: Zone (1-2 digits) + Hemisphere (N/S) + Easting + Northing
        # Examples: 10T 500000 4500000, 10T 500000.00 4500000.00
        text_upper = text.upper()
        # Pattern: 1-2 digit zone + letter + large numbers (easting 6-7 digits, northing 7-8 digits)
        utm_pattern = r"^\d{1,2}[A-Z]\s+\d{6,8}[\.,]?\d*\s+\d{7,9}[\.,]?\d*"
        return bool(re.match(utm_pattern, text_upper.strip()))

    def parse(self, text: str) -> tuple:
        """Parse UTM coordinate - let mature UTM library handle validation"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from .utm import utm_to_point
            except ImportError:
                from utm import utm_to_point

            # Let mature UTM library handle validation and parsing
            pt = utm_to_point(text)
            lat, lon = pt.y(), pt.x()
            self._log_debug(f"UTM parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, None, epsg4326, "UTM")
        except Exception as e:
            self._log_debug(f"UTM parsing failed: {e}")
        return None


class UpsParserStrategy(CoordinateParserStrategy):
    """UPS coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like UPS"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from .ups import isUps
            except ImportError:
                from ups import isUps
            return isUps(text)
        except Exception:
            return False

    def parse(self, text: str) -> tuple:
        """Parse UPS coordinate"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from .ups import ups2Point
            except ImportError:
                from ups import ups2Point

            pt = ups2Point(text)
            lat, lon = pt.y(), pt.x()
            self._log_debug(f"UPS parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, None, epsg4326, "UPS")
        except Exception as e:
            self._log_debug(f"UPS parsing failed: {e}")
        return None


class H3ParserStrategy(CoordinateParserStrategy):
    """H3 coordinate parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like H3 and H3 is available"""
        try:
            # Check if H3 library is available
            try:
                from . import h3
            except ImportError:
                import h3

            text_clean = re.sub(r"\s+", "", text)
            return bool(re.match(r"^[0-9a-fA-F]{15}$", text_clean))
        except ImportError:
            return False
        except Exception:
            return False

    def parse(self, text: str) -> tuple:
        """Parse H3 coordinate"""
        try:
            # Handle both plugin context and standalone testing
            try:
                from . import h3
            except ImportError:
                import h3

            if h3.is_valid_cell(text):
                lat, lon = h3.cell_to_latlng(text)
                coords = h3.cell_to_boundary(text)
                pts = []
                for p in coords:
                    pt = QgsPointXY(p[1], p[0])
                    pts.append(pt)
                pts.append(pts[0])
                geom = QgsGeometry.fromPolylineXY(pts)
                self._log_debug(f"H3 parsed: {text} → lat={lat}, lon={lon}")
                return (lat, lon, geom, epsg4326, "H3")
        except Exception as e:
            self._log_debug(f"H3 parsing failed: {e}")
        return None


class GeoJsonParserStrategy(CoordinateParserStrategy):
    """GeoJSON Point parsing strategy"""

    def can_parse(self, text: str) -> bool:
        """Check if text looks like GeoJSON"""
        text_stripped = text.strip()
        return (
            text_stripped.startswith("{")
            and ('"type"' in text and '"coordinates"' in text)
            or '"Point"' in text
        )

    def parse(self, text: str) -> tuple:
        """Parse GeoJSON Point coordinate"""
        try:
            codec = QTextCodec.codecForName("UTF-8")
            fields = QgsJsonUtils.stringToFields(text, codec)
            fet = QgsJsonUtils.stringToFeatureList(text, fields, codec)
            if (len(fet) > 0) and fet[0].isValid():
                geom = fet[0].geometry()
                if not geom.isEmpty() and (geom.wkbType() == QgsWkbTypes.Point):
                    pt = geom.asPoint()
                    lat, lon = pt.y(), pt.x()
                    self._log_debug(f"GeoJSON parsed: {text} → lat={lat}, lon={lon}")
                    return (lat, lon, None, epsg4326, "GeoJSON Point")
        except Exception as e:
            self._log_debug(f"GeoJSON parsing failed: {e}")
        return None


class DmsParserStrategy(CoordinateParserStrategy):
    """DMS (Degrees Minutes Seconds) parsing strategy - most ambiguous, so last"""

    def __init__(self, settings):
        self.settings = settings

    def parse(self, text: str) -> tuple:
        """Parse DMS coordinate - with enhanced validation to prevent false positives"""
        try:
            # Pre-filter obviously non-DMS inputs before calling parseDMSString
            if self._is_obviously_not_dms(text):
                return None

            # Handle both plugin context and standalone testing
            try:
                from .util import parseDMSString
            except ImportError:
                from util import parseDMSString

            # Let mature parseDMSString function handle validation
            # It will throw an exception if the input is not valid DMS
            lat, lon = parseDMSString(text, self.settings.zoomToCoordOrder)
            self._log_debug(f"DMS parsed: {text} → lat={lat}, lon={lon}")
            return (lat, lon, None, epsg4326, "DMS")
        except Exception as e:
            self._log_debug(f"DMS parsing failed: {e}")
        return None

    def _is_obviously_not_dms(self, text: str) -> bool:
        """
        Pre-filter obviously non-DMS coordinates that parseDMSString incorrectly accepts

        DMS coordinates should have:
        - Degree symbols, cardinal directions, or minute/second indicators
        - Numbers in reasonable degree ranges (not UTM-scale numbers)
        """
        text_upper = text.upper().strip()

        # Extract numbers to check ranges
        import re

        numbers = re.findall(r"\d+\.?\d*", text)
        if len(numbers) >= 2:
            try:
                first_num = float(numbers[0])
                second_num = float(numbers[1])

                # Reject if numbers are way too large for degrees
                # UTM coordinates, state plane coordinates, etc.
                if first_num > 360 or second_num > 360:
                    return True

                # Reject obvious UTM patterns (large integer coordinates)
                if first_num > 1000 and second_num > 1000:
                    return True

                # If no DMS indicators and numbers are suspiciously large
                has_dms_indicators = any(
                    indicator in text_upper
                    for indicator in [
                        "°",
                        "'",
                        '"',
                        "DEG",
                        "MIN",
                        "SEC",
                        "N",
                        "S",
                        "E",
                        "W",
                    ]
                )
                if not has_dms_indicators and (first_num > 180 or second_num > 90):
                    return True

            except ValueError:
                pass

        return False


# ASCII whitelist for fast-path filtering - valid coordinate characters
# Letters, digits, common coordinate symbols, whitespace, and basic punctuation
WHITELIST = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "°'\"+-.,;:|/()[]{} "
    "\t\n\r"
)


class SmartCoordinateParser:
    """
    Smart coordinate parser using Strategy Pattern with fast-path triage
    Supports WKT, EWKT, WKB, MGRS, Plus Codes, UTM, UPS, Geohash,
    Maidenhead Grid, H3, GeoJSON, DMS, and decimal coordinates

    Performance optimizations:
    1. ASCII whitelist filtering to reject invalid input early
    2. O(1) fast-path classification for unambiguous formats
    3. can_parse() pre-checks to avoid expensive parsing attempts
    4. Maximum 1-2 strategy parse attempts per input
    """

    def __init__(self, settings_obj, iface):
        self.settings = settings_obj
        self.iface = iface
        self.strategies = self._create_parsing_strategies()

    def preprocess_input(self, text: str) -> str:
        """
        Preprocess input with ASCII whitelist filtering and whitespace normalization.
        Returns None if input contains invalid characters, otherwise cleaned text.

        This provides an early rejection path for obviously invalid input,
        avoiding expensive parsing attempts on garbage data.
        """
        if not text or not isinstance(text, str):
            return None

        # Fast ASCII whitelist check
        # If any character is outside the whitelist, reject immediately
        for char in text:
            if char not in WHITELIST:
                QgsMessageLog.logMessage(
                    f"SmartParser.preprocess: Rejected input with invalid character '{char}' (ord={ord(char)})",
                    "LatLonTools",
                    Qgis.Info,
                )
                return None

        # Normalize whitespace: replace all whitespace sequences with single space
        # and strip leading/trailing whitespace
        text_clean = re.sub(r"\s+", " ", text.strip())

        QgsMessageLog.logMessage(
            f"SmartParser.preprocess: Cleaned input from '{text}' to '{text_clean}'",
            "LatLonTools",
            Qgis.Info,
        )

        return text_clean

    def classify_format_fast(self, text: str) -> str:
        """
        O(1) fast-path classification for zero-ambiguity coordinate formats.
        Returns the format name if uniquely identified, None if ambiguous.

        This provides instant dispatch for formats with unmistakable signatures,
        bypassing the strategy loop entirely for common cases.
        """
        text_upper = text.upper().strip()
        text_clean = re.sub(r"\s+", "", text_upper)

        # Tier 1: Ultra-specific signatures (unmistakable, zero collision risk)
        # Check these first as they're O(1) and cover common cases

        # WKB hex string: long, even-length hex-only strings
        if len(text_clean) >= 20 and len(text_clean) % 2 == 0:
            if all(c in "0123456789ABCDEFabcdef" for c in text_clean):
                return "WKB"

        # GeoJSON: starts with '{' and has JSON structure
        if text.strip().startswith("{") and (
            '"type"' in text and '"coordinates"' in text
        ):
            return "GeoJSON"

        # EWKT: SRID= prefix with semicolon
        if text_upper.startswith("SRID=") and ";" in text_upper:
            return "EWKT"

        # Plus Codes: contains '+' separator with base20 characters
        if "+" in text_upper:
            # Check for Plus Codes pattern: base20 chars around '+'
            plus_code_parts = text_upper.split("+")
            if len(plus_code_parts) == 2:
                before_plus = plus_code_parts[0]
                after_plus = plus_code_parts[1]
                if (
                    all(c in "23456789CFGHJMPQRVWX" for c in before_plus)
                    and len(before_plus) >= 2
                    and len(before_plus) <= 8
                    and all(
                        c in "23456789CFGHJMPQRVWX" for c in after_plus if c.isalpha()
                    )
                ):
                    return "PlusCodes"

        # H3: exactly 15 hex characters (if H3 library available)
        if len(text_clean) == 15:
            if all(c in "0123456789ABCDEFabcdef" for c in text_clean):
                try:
                    # Check if H3 library is available
                    try:
                        from . import h3
                    except ImportError:
                        import h3
                    return "H3"
                except ImportError:
                    pass  # H3 not available, don't classify

        # GEOREF: exactly 4 letters followed by digits
        if bool(re.match(r"^[A-Z]{4}\d{2,}$", text_clean)):
            return "GEOREF"

        # Maidenhead: 2 letters + 2 digits + optional pairs
        if bool(re.match(r"^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$", text_clean)):
            return "Maidenhead"

        # Tier 2: High-signature formats (very low collision risk but not O(1))
        # These still benefit from can_parse() checks

        # WKT: geometry keywords (multiple possibilities)
        wkt_keywords = [
            "POINT",
            "LINESTRING",
            "POLYGON",
            "MULTIPOINT",
            "MULTILINESTRING",
            "MULTIPOLYGON",
            "GEOMETRYCOLLECTION",
        ]
        if any(keyword in text_upper for keyword in wkt_keywords):
            return "WKT"

        # MGRS: zone + grid pattern
        if bool(re.match(r"^\d{1,2}[C-HJ-NP-X][A-HJ-NP-Z]{2,}\d{2,}$", text_clean)):
            return "MGRS"

        # UTM: zone + hemisphere + large numbers
        if bool(
            re.match(
                r"^\d{1,2}[A-Z]\s+\d{6,8}[\.,]?\d*\s+\d{7,9}[\.,]?\d*",
                text_upper.strip(),
            )
        ):
            return "UTM"

        # If we get here, format is ambiguous (Geohash, DMS, decimal degrees)
        # Return None to trigger full strategy search with can_parse() checks
        return None

    def _create_parsing_strategies(self):
        """
        Factory method to create coordinate parsing strategies in optimal order

        Ordered by format signature strength (most specific → most ambiguous):
        - Strong signatures (WKB hex, JSON structure, keywords) come first
        - Structured formats (grids, codes) in middle
        - Ambiguous number patterns (DMS, decimal) come last
        """
        return [
            # Tier 1: Ultra-specific format signatures (extremely low collision risk)
            WkbParserStrategy(),  # Long hex strings - unmistakable
            GeoJsonParserStrategy(),  # JSON structure - unmistakable
            EwktParserStrategy(),  # "SRID=" prefix - unique signature
            WktParserStrategy(),  # "GEOMETRY(" keywords - distinctive
            # Tier 2: Very specific structured formats (low collision risk)
            H3ParserStrategy(),  # Exactly 15 hex chars - precise
            PlusCodesParserStrategy(),  # Base20 + "+" separator - unique
            MgrsParserStrategy(),  # Military grid structure - well-defined
            GeorefParserStrategy(),  # Letter/digit pattern - structured
            # Tier 3: Medium specificity (medium collision risk)
            MaidenheadParserStrategy(),  # Ham radio grid - structured
            UtmParserStrategy(),  # Large numbers - uses mature isUtm()
            UpsParserStrategy(),  # Polar coordinates - uses mature isUps()
            # Tier 4: Ambiguous patterns (higher collision risk)
            GeohashParserStrategy(),  # Base32 - needs conflict detection
            DmsParserStrategy(self.settings),  # Most ambiguous - must be last
        ]

    def parse(self, text):
        """
        Main parsing entry point using fast-path triage with strategy pattern
        Returns: (lat, lon, bounds, source_crs) or None if parsing fails

        Performance optimizations:
        1. Preprocess with ASCII whitelist (early rejection)
        2. Fast-path classification for zero-ambiguity formats (O(1))
        3. can_parse() checks to avoid expensive parse() calls
        4. Maximum 1-2 strategy parse() attempts per input
        """
        if not text or not isinstance(text, str):
            QgsMessageLog.logMessage(
                f"SmartParser.parse: REJECTED - Invalid input type or empty",
                "LatLonTools",
                Qgis.Warning,
            )
            return None

        original_text = text
        QgsMessageLog.logMessage(
            f"SmartParser.parse: STARTING PARSE for input: '{original_text}'",
            "LatLonTools",
            Qgis.Info,
        )

        try:
            # Step 1: Preprocess input with ASCII whitelist
            text_clean = self.preprocess_input(text)
            if text_clean is None:
                QgsMessageLog.logMessage(
                    f"SmartParser.parse: REJECTED - Input contains invalid characters: '{original_text}'",
                    "LatLonTools",
                    Qgis.Warning,
                )
                return None

            # Step 2: Fast-path classification for zero-ambiguity formats
            fast_format = self.classify_format_fast(text_clean)
            if fast_format:
                QgsMessageLog.logMessage(
                    f"SmartParser.parse: FAST-PATH - Classified as '{fast_format}'",
                    "LatLonTools",
                    Qgis.Info,
                )

                # Find the matching strategy and parse directly
                for strategy in self.strategies:
                    strategy_name = strategy.__class__.__name__.replace(
                        "ParserStrategy", ""
                    ).upper()
                    if (
                        fast_format.upper() == strategy_name
                        or fast_format.upper() in strategy_name
                    ):
                        QgsMessageLog.logMessage(
                            f"SmartParser.parse: FAST-PATH - Trying {strategy.__class__.__name__}",
                            "LatLonTools",
                            Qgis.Info,
                        )
                        result = strategy.parse(text_clean)
                        if result is not None:
                            lat, lon, bounds, source_crs, description = result
                            QgsMessageLog.logMessage(
                                f"SmartParser.parse: FAST-PATH SUCCESS with {strategy.__class__.__name__} - {description}: lat={lat}, lon={lon}",
                                "LatLonTools",
                                Qgis.Info,
                            )
                            return (lat, lon, bounds, source_crs)
                        else:
                            QgsMessageLog.logMessage(
                                f"SmartParser.parse: FAST-PATH FAILED - {strategy.__class__.__name__} parse returned None",
                                "LatLonTools",
                                Qgis.Warning,
                            )
                            break  # Fast-path match failed, don't try other strategies

            # Step 3: Ambiguous format - use can_parse() to narrow candidates
            QgsMessageLog.logMessage(
                "SmartParser.parse: AMBIGUOUS - Using can_parse() triage",
                "LatLonTools",
                Qgis.Info,
            )

            candidates = []
            for strategy in self.strategies:
                QgsMessageLog.logMessage(
                    f"SmartParser.parse: Checking can_parse for {strategy.__class__.__name__}",
                    "LatLonTools",
                    Qgis.Info,
                )
                if strategy.can_parse(text_clean):
                    candidates.append(strategy)
                    QgsMessageLog.logMessage(
                        f"SmartParser.parse: CANDIDATE - {strategy.__class__.__name__}",
                        "LatLonTools",
                        Qgis.Info,
                    )

            # Try candidates, max 2 parse attempts
            parse_attempts = 0
            for strategy in candidates[:2]:  # Limit to first 2 candidates
                QgsMessageLog.logMessage(
                    f"SmartParser.parse: Trying {strategy.__class__.__name__}",
                    "LatLonTools",
                    Qgis.Info,
                )
                result = strategy.parse(text_clean)
                parse_attempts += 1
                if result is not None:
                    lat, lon, bounds, source_crs, description = result
                    QgsMessageLog.logMessage(
                        f"SmartParser.parse: SUCCESS with {strategy.__class__.__name__} - {description}: lat={lat}, lon={lon} (after {parse_attempts} attempts)",
                        "LatLonTools",
                        Qgis.Info,
                    )
                    return (lat, lon, bounds, source_crs)

            QgsMessageLog.logMessage(
                f"SmartParser.parse: STRATEGIES FAILED after {parse_attempts} attempts",
                "LatLonTools",
                Qgis.Info,
            )

            # Step 4: Fall back to existing coordinate parsing if no strategy matches
            QgsMessageLog.logMessage(
                "SmartParser.parse: === FALLBACK: Trying existing coordinate formats ===",
                "LatLonTools",
                Qgis.Info,
            )
            result = self._extract_and_validate_coordinates(text_clean)
            if result:
                lat, lon, bounds, source_crs = result
                QgsMessageLog.logMessage(
                    f"SmartParser.parse: SUCCESS with existing formats: lat={lat}, lon={lon}",
                    "LatLonTools",
                    Qgis.Info,
                )
                return result

            QgsMessageLog.logMessage(
                f"SmartParser.parse: FAILED - No parser could handle input: '{original_text}'",
                "LatLonTools",
                Qgis.Warning,
            )
            return None

        except Exception as e:
            QgsMessageLog.logMessage(
                f"SmartParser.parse: ERROR - {e}", "LatLonTools", Qgis.Critical
            )
            return None

    def _extract_and_validate_coordinates(self, text):
        """
        Extract and validate coordinates from text (fallback method)
        Returns: (lat, lon, bounds, source_crs) or None

        Enhanced validation to reject obvious UTM/projected coordinates
        """
        # Try to extract numbers from text
        numbers = self._extract_numbers(text)
        if len(numbers) < 2:
            return None

        # Pre-filter obviously non-geographic coordinates
        if self._is_obviously_projected(numbers):
            return None

        # Test coordinate order preference
        result = self._validate_coordinate_order(numbers)
        if result:
            lat, lon = result
            # Basic validation
            if self._is_valid_geographic(lat, lon):
                return (lat, lon, None, epsg4326)

        return None

    def _extract_numbers(self, text):
        """Extract floating point numbers from text"""
        # Remove common separators and get numbers
        text_clean = re.sub(r"[,;:|]", " ", text)
        number_pattern = r"[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?"
        matches = re.findall(number_pattern, text_clean)
        try:
            return [float(match) for match in matches]
        except ValueError:
            return []

    def _validate_coordinate_order(self, numbers):
        """Validate and determine coordinate order"""
        if len(numbers) < 2:
            return None

        x, y = numbers[0], numbers[1]

        # Apply coordinate order preference
        if self.settings.zoomToCoordOrder == CoordOrder.OrderYX:
            lat, lon = x, y  # First number is latitude
        else:
            lat, lon = y, x  # First number is longitude

        # Validate ranges
        if self._is_valid_geographic(lat, lon):
            return (lat, lon)

        # Try swapping if first attempt failed
        if self._is_valid_geographic(lon, lat):
            return (lon, lat)

        return None

    def _is_valid_geographic(self, lat, lon):
        """Check if coordinates are in valid geographic ranges"""
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def _is_obviously_projected(self, numbers):
        """
        Check if coordinates are obviously projected/UTM coordinates that should be rejected

        Args:
            numbers: List of extracted numbers from input text

        Returns:
            True if coordinates appear to be projected (UTM/state plane/etc), False otherwise
        """
        if len(numbers) < 2:
            return False

        # Get first two numbers (potential coordinates)
        first_num = abs(float(numbers[0]))
        second_num = abs(float(numbers[1]))

        # UTM eastings are typically > 100,000, northings > 1,000,000
        # State plane coordinates are often even larger
        # Geographic coordinates are always <= 180 for longitude, <= 90 for latitude

        # If both numbers are very large, it's almost certainly projected
        if first_num > 1000 and second_num > 1000:
            return True

        # If either number is larger than possible geographic coordinates
        if first_num > 360 or second_num > 360:
            return True

        # Typical UTM patterns: eastings 100,000-999,999, northings 1,000,000-10,000,000
        utm_easting_range = 100000 <= first_num <= 999999
        utm_northing_range = 1000000 <= second_num <= 10000000
        if utm_easting_range and utm_northing_range:
            return True

        # Reverse order UTM check
        utm_easting_range_rev = 100000 <= second_num <= 999999
        utm_northing_range_rev = 1000000 <= first_num <= 10000000
        if utm_easting_range_rev and utm_northing_range_rev:
            return True

        return False
