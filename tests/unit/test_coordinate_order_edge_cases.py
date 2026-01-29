#!/usr/bin/env python3
"""
Coordinate Order Edge Cases Tests

Tests for coordinate order handling to verify OrderYX and OrderXY settings
work correctly with various coordinate formats and edge cases.
"""

import os
import sys
import unittest
from unittest.mock import Mock

# Add parent directory to path for imports
# File is at: tests/unit/test_coordinate_order_edge_cases.py
# Need to go up 3 levels to reach plugin root
plugin_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)


# Mock QGIS components for standalone testing
class MockQgsMessageLog:
    @staticmethod
    def logMessage(msg, source, level=None):
        pass  # Silence QGIS logging during tests


class MockQgis:
    Debug = 0
    Info = 1
    Warning = 2
    Critical = 3


class MockQgsGeometry:
    @staticmethod
    def fromWkt(wkt_string):
        return None


class MockQgsCoordinateReferenceSystem:
    def __init__(self, epsg_code):
        self.epsg_code = epsg_code


class MockQgsCoordinateTransform:
    def __init__(self, source, dest, project):
        pass


class MockQgsProject:
    @staticmethod
    def instance():
        return None


class MockQgsWkbTypes:
    Point = 1


class MockQgsRectangle:
    def __init__(self, xmin, ymin, xmax, ymax):
        pass


class MockQgsPointXY:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class MockQgsJsonUtils:
    @staticmethod
    def parseGeometry(geojson_string):
        return None


class MockQTextCodec:
    @staticmethod
    def codecForName(name):
        return None


class MockQCoreApplication:
    @staticmethod
    def translate(context, text, disambiguation=None, n=-1):
        return text


class MockQgsSettings:
    def __init__(self):
        self._values = {}

    def value(self, key, default=None):
        return self._values.get(key, default)

    def setValue(self, key, value):
        self._values[key] = value


class MockQColor:
    def __init__(self, color_str):
        self._color = color_str

    def setAlpha(self, alpha):
        pass  # Ignore alpha changes in tests

    def __repr__(self):
        return f"QColor({self._color})"


def mockLoadUiType(ui_file):
    """Mock loadUiType for testing"""
    return (type("MockUi", (), {}), type("MockUiBase", (), {}))


# Monkey-patch qgis modules (must be before importing smart_parser)
import sys  # noqa: E402

sys.modules["qgis"] = type(sys)("qgis")
sys.modules["qgis.core"] = type(sys)("qgis.core")
sys.modules["qgis.PyQt"] = type(sys)("qgis.PyQt")
sys.modules["qgis.PyQt.QtCore"] = type(sys)("qgis.PyQt.QtCore")
sys.modules["qgis.PyQt.uic"] = type(sys)("qgis.PyQt.uic")
sys.modules["qgis.PyQt.uic"].loadUiType = mockLoadUiType
sys.modules["qgis.PyQt.QtWidgets"] = type(sys)("qgis.PyQt.QtWidgets")
sys.modules["qgis.PyQt.QtWidgets"].QDialog = type("QDialog", (), {})
sys.modules["qgis.PyQt.QtWidgets"].QDialogButtonBox = type("QDialogButtonBox", (), {})
sys.modules["qgis.PyQt.QtWidgets"].QFileDialog = type("QFileDialog", (), {})
# Create Qt mock with common attributes
QtMock = type("Qt", (), {"Unchecked": 0, "Checked": 1})
sys.modules["qgis.PyQt.QtCore"].Qt = QtMock
sys.modules["qgis.PyQt.QtGui"] = type(sys)("qgis.PyQt.QtGui")
sys.modules["qgis.PyQt.QtGui"].QColor = MockQColor

# Add all QGIS classes to qgis.core module
sys.modules["qgis.core"].QgsMessageLog = MockQgsMessageLog
sys.modules["qgis.core"].Qgis = MockQgis
sys.modules["qgis.core"].QgsGeometry = MockQgsGeometry
sys.modules["qgis.core"].QgsCoordinateReferenceSystem = MockQgsCoordinateReferenceSystem
sys.modules["qgis.core"].QgsCoordinateTransform = MockQgsCoordinateTransform
sys.modules["qgis.core"].QgsProject = MockQgsProject
sys.modules["qgis.core"].QgsWkbTypes = MockQgsWkbTypes
sys.modules["qgis.core"].QgsRectangle = MockQgsRectangle
sys.modules["qgis.core"].QgsPointXY = MockQgsPointXY
sys.modules["qgis.core"].QgsJsonUtils = MockQgsJsonUtils
sys.modules["qgis.core"].QgsSettings = MockQgsSettings
sys.modules["qgis.PyQt.QtCore"].QTextCodec = MockQTextCodec
sys.modules["qgis.PyQt.QtCore"].QCoreApplication = MockQCoreApplication

from smart_parser import SmartCoordinateParser  # noqa: E402


class MockSettings:
    """Mock settings with configurable coordinate order"""

    def __init__(self, order="yx"):
        # OrderYX: Input format is "Lat, Lon" (value 0)
        # OrderXY: Input format is "Lon, Lat" (value 1)
        # Must match CoordOrder enum values from settings.py
        self.zoomToCoordOrder = 0 if order == "yx" else 1


class TestCoordinateOrderEdgeCases(unittest.TestCase):
    """Test coordinate order handling with various edge cases"""

    def setUp(self):
        """Set up parser with OrderYX (Lat, Lon) as default"""
        self.parser_yx = SmartCoordinateParser(MockSettings(order="yx"), None)
        self.parser_xy = SmartCoordinateParser(MockSettings(order="xy"), None)

    def test_order_yx_lat_lon_format(self):
        """
        OrderYX: "45.0, -122.0" should parse as lat=45.0, lon=-122.0
        First number is latitude, second is longitude
        """
        test_input = "45.0, -122.0"
        result = self.parser_yx.parse(test_input)

        self.assertIsNotNone(result, "Failed to parse valid coordinates")
        lat, lon, bounds, source_crs = result

        # OrderYX means first number is lat, second is lon
        self.assertEqual(lat, 45.0, "Latitude should be first number in OrderYX")
        self.assertEqual(lon, -122.0, "Longitude should be second number in OrderYX")

    def test_order_xy_lon_lat_format(self):
        """
        OrderXY: "-122.0, 45.0" should parse as lon=-122.0, lat=45.0
        First number is longitude, second is latitude
        """
        test_input = "-122.0, 45.0"
        result = self.parser_xy.parse(test_input)

        self.assertIsNotNone(result, "Failed to parse valid coordinates")
        lat, lon, bounds, source_crs = result

        # OrderXY means first number is lon, second is lat
        self.assertEqual(lat, 45.0, "Latitude should be second number in OrderXY")
        self.assertEqual(lon, -122.0, "Longitude should be first number in OrderXY")

    def test_ambiguous_coordinates_both_valid(self):
        """
        Test ambiguous coordinates where both orders are valid
        (45.0, 45.0) could be interpreted as either order
        """
        test_input = "45.0, 45.0"

        # With OrderYX: lat=45.0, lon=45.0
        result_yx = self.parser_yx.parse(test_input)
        self.assertIsNotNone(
            result_yx, "Should parse ambiguous coordinates with OrderYX"
        )
        lat_yx, lon_yx, _, _ = result_yx
        self.assertEqual(lat_yx, 45.0)
        self.assertEqual(lon_yx, 45.0)

        # With OrderXY: lat=45.0, lon=45.0 (same result due to symmetry)
        result_xy = self.parser_xy.parse(test_input)
        self.assertIsNotNone(
            result_xy, "Should parse ambiguous coordinates with OrderXY"
        )
        lat_xy, lon_xy, _, _ = result_xy
        self.assertEqual(lat_xy, 45.0)
        self.assertEqual(lon_xy, 45.0)

    def test_boundary_values_maximum(self):
        """
        Test edge case with maximum valid coordinates
        (90.0, 180.0) - North Pole, International Date Line
        """
        test_input = "90.0, 180.0"

        result_yx = self.parser_yx.parse(test_input)
        self.assertIsNotNone(result_yx, "Should parse maximum coordinates")
        lat, lon, _, _ = result_yx
        self.assertEqual(lat, 90.0, "Latitude should be maximum (90)")
        self.assertEqual(lon, 180.0, "Longitude should be maximum (180)")

    def test_boundary_values_minimum(self):
        """
        Test edge case with minimum valid coordinates
        (-90.0, -180.0) - South Pole, International Date Line
        """
        test_input = "-90.0, -180.0"

        result_yx = self.parser_yx.parse(test_input)
        self.assertIsNotNone(result_yx, "Should parse minimum coordinates")
        lat, lon, _, _ = result_yx
        self.assertEqual(lat, -90.0, "Latitude should be minimum (-90)")
        self.assertEqual(lon, -180.0, "Longitude should be minimum (-180)")

    def test_negative_coordinates_order_yx(self):
        """
        Test negative coordinates with OrderYX
        "-33.8688, 151.2093" (Sydney, Australia)
        """
        test_input = "-33.8688, 151.2093"
        result = self.parser_yx.parse(test_input)

        self.assertIsNotNone(result)
        lat, lon, _, _ = result
        self.assertEqual(lat, -33.8688, "Should parse negative latitude correctly")
        self.assertEqual(lon, 151.2093, "Should parse positive longitude correctly")

    def test_negative_coordinates_order_xy(self):
        """
        Test negative coordinates with OrderXY
        "151.2093, -33.8688" (Sydney, Australia in lon,lat order)
        """
        test_input = "151.2093, -33.8688"
        result = self.parser_xy.parse(test_input)

        self.assertIsNotNone(result)
        lat, lon, _, _ = result
        self.assertEqual(lat, -33.8688, "Should parse negative latitude correctly")
        self.assertEqual(lon, 151.2093, "Should parse positive longitude correctly")

    def test_space_separated_coordinates(self):
        """
        Test space-separated coordinates with OrderYX
        "51.5074 -0.1278" (London, UK)
        """
        test_input = "51.5074 -0.1278"
        result = self.parser_yx.parse(test_input)

        self.assertIsNotNone(result)
        lat, lon, _, _ = result
        self.assertEqual(lat, 51.5074)
        self.assertEqual(lon, -0.1278)

    def test_invalid_coordinate_rejected(self):
        """
        Test that invalid coordinates are rejected
        (91.0, 181.0) - latitude exceeds maximum
        """
        test_input = "91.0, 181.0"
        result = self.parser_yx.parse(test_input)

        # Should be rejected because latitude > 90
        self.assertIsNone(result, "Invalid latitude should be rejected")

    def test_invalid_longitude_rejected(self):
        """
        Test that invalid longitude is rejected
        (0.0, 181.0) - longitude exceeds maximum
        """
        test_input = "0.0, 181.0"
        result = self.parser_yx.parse(test_input)

        # Should be rejected because longitude > 180
        self.assertIsNone(result, "Invalid longitude should be rejected")

    def test_both_coordinates_invalid(self):
        """
        Test that completely invalid coordinates are rejected
        (200.0, 300.0) - both exceed valid ranges
        """
        test_input = "200.0, 300.0"
        result = self.parser_yx.parse(test_input)

        self.assertIsNone(result, "Both invalid coordinates should be rejected")

    def test_origin_coordinates(self):
        """
        Test origin coordinates (0, 0) - Gulf of Guinea
        """
        test_input = "0.0, 0.0"
        result = self.parser_yx.parse(test_input)

        self.assertIsNotNone(result)
        lat, lon, _, _ = result
        self.assertEqual(lat, 0.0)
        self.assertEqual(lon, 0.0)


def run_tests():
    """Run the coordinate order edge case tests"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCoordinateOrderEdgeCases)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 80)
    print("COORDINATE ORDER EDGE CASES TEST")
    print("=" * 80)
    print()

    success = run_tests()

    print()
    if success:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
