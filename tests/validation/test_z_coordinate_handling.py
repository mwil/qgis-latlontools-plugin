#!/usr/bin/env python3
"""
Test suite for Z coordinate handling and elevation value edge cases
Prevents regressions in coordinate parsing when elevation/Z values are present
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsPointXY, QgsGeometry, 
    QgsWkbTypes, QgsProject, QgsCoordinateTransform
)
from qgis.PyQt.QtCore import QTextCodec
from qgis.core import QgsJsonUtils

# Import the smart parser
from smart_parser import SmartCoordinateParser
from settings import CoordOrder

# Mock QGIS globals
epsg4326 = QgsCoordinateReferenceSystem.fromEpsgId(4326)


class TestZCoordinateHandling(unittest.TestCase):
    """Test handling of Z coordinates and elevation values"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock settings object
        self.mock_settings = Mock()
        self.mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        
        # Mock iface with canvas
        self.mock_iface = Mock()
        self.mock_canvas = Mock()
        self.mock_map_settings = Mock()
        self.mock_map_settings.destinationCrs.return_value = epsg4326
        self.mock_canvas.mapSettings.return_value = self.mock_map_settings
        self.mock_iface.mapCanvas.return_value = self.mock_canvas
        
        # Create parser instance
        self.parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
        
    def test_wkb_with_srid_and_z_coordinate(self):
        """Test WKB with SRID and 3D coordinates (PointZ)"""
        # Your problematic WKB case: SRID=6696, PointZ with elevation
        wkb_3d = "01010000A0281A00005396BF88FF9560405296C6D462D64040A857CA32C41D7240"
        
        result = self.parser.parse(wkb_3d)
        
        # Should parse successfully and extract lat/lon, ignoring Z
        self.assertIsNotNone(result, "WKB with SRID and Z should parse successfully")
        self.assertEqual(len(result), 4, "Should return (lat, lon, bounds, crs)")
        
        lat, lon, bounds, crs = result
        
        # Coordinates should be reasonable geographic values
        self.assertTrue(-90 <= lat <= 90, f"Latitude {lat} should be valid geographic range")
        self.assertTrue(-180 <= lon <= 180, f"Longitude {lon} should be valid geographic range")
        
    def test_wkb_without_srid_2d(self):
        """Test WKB without SRID (2D Point)"""
        # Your original test case
        wkb_2d = "01010000009a99999999e960406666666666a64640"
        
        result = self.parser.parse(wkb_2d)
        
        self.assertIsNotNone(result, "WKB without SRID should parse successfully")
        lat, lon, bounds, crs = result
        
        # Should be interpreted as WGS84
        self.assertTrue(-90 <= lat <= 90, f"Latitude {lat} should be valid")
        self.assertTrue(-180 <= lon <= 180, f"Longitude {lon} should be valid")
        
    def test_geojson_with_z_coordinate(self):
        """Test GeoJSON with 3D coordinates"""
        geojson_3d = '{"type":"Point","coordinates":[132.69, 33.67, 289.86]}'
        
        result = self.parser.parse(geojson_3d)
        
        self.assertIsNotNone(result, "GeoJSON with Z coordinate should parse")
        lat, lon, bounds, crs = result
        
        # Should extract X,Y and ignore Z
        self.assertAlmostEqual(lon, 132.69, places=2, msg="Longitude should match")
        self.assertAlmostEqual(lat, 33.67, places=2, msg="Latitude should match")
        
    def test_wkt_with_z_coordinate(self):
        """Test WKT with Z coordinate"""
        test_cases = [
            "POINT Z (132.69 33.67 289.86)",
            "POINT(132.69 33.67 289.86)",  # Z implicit
            "POINT Z(132.69 33.67 289.86)"   # No space
        ]
        
        for wkt_3d in test_cases:
            with self.subTest(wkt=wkt_3d):
                result = self.parser.parse(wkt_3d)
                
                self.assertIsNotNone(result, f"WKT with Z should parse: {wkt_3d}")
                lat, lon, bounds, crs = result
                
                # Should extract X,Y and ignore Z
                self.assertAlmostEqual(lon, 132.69, places=2)
                self.assertAlmostEqual(lat, 33.67, places=2)
                
    def test_decimal_degrees_with_elevation(self):
        """Test decimal degrees with elevation values"""
        test_cases = [
            "40.7128, -74.0060, 100.5",     # Standard comma separation
            "40.7128 -74.0060 100.5",       # Space separation
            "40.7128; -74.0060; 100.5",     # Semicolon separation
        ]
        
        for coord_text in test_cases:
            with self.subTest(text=coord_text):
                result = self.parser.parse(coord_text)
                
                self.assertIsNotNone(result, f"Decimal with elevation should parse: {coord_text}")
                lat, lon, bounds, crs = result
                
                # Should use only first two numbers, ignore elevation
                self.assertAlmostEqual(lat, 40.7128, places=3)
                self.assertAlmostEqual(lon, -74.0060, places=3)
                
    def test_utm_with_elevation_rejection(self):
        """Test UTM coordinates with elevation are properly rejected"""
        utm_with_elevation_cases = [
            "33N 315428 5741324 1234",      # Standard UTM + elevation
            "315428 5741324 33N 1234",      # Easting/Northing/Zone + elevation
            "315428mE 5741324mN 33N 1234m", # With units + elevation
        ]
        
        for utm_text in utm_with_elevation_cases:
            with self.subTest(utm=utm_text):
                result = self.parser.parse(utm_text)
                
                # Should fail to parse rather than return wrong coordinates
                self.assertIsNone(result, 
                    f"UTM with elevation should be rejected, not misinterpreted: {utm_text}")
                
    def test_projected_coordinate_detection(self):
        """Test detection of projected coordinates that shouldn't be treated as lat/lon"""
        # These should all be rejected as they're clearly projected values
        projected_cases = [
            "315428 5741324",           # UTM-like values
            "500000 4500000",           # Large projected coordinates
            "1234567 987654",           # Obviously not geographic
            "33 315428",                # Zone + Easting (from broken UTM parsing)
        ]
        
        for proj_text in projected_cases:
            with self.subTest(coords=proj_text):
                result = self.parser.parse(proj_text)
                
                self.assertIsNone(result, 
                    f"Projected coordinates should be rejected: {proj_text}")
                
    def test_valid_large_coordinates_still_work(self):
        """Test that valid large longitude values still work"""
        valid_large_cases = [
            "45.5, 179.9",              # Valid near antimeridian
            "-89.9, -179.9",            # Valid near south pole/antimeridian
            "0, 150.123456",            # Valid precise longitude
        ]
        
        for coord_text in valid_large_cases:
            with self.subTest(coords=coord_text):
                result = self.parser.parse(coord_text)
                
                self.assertIsNotNone(result, 
                    f"Valid large coordinates should still work: {coord_text}")
                    
    def test_dms_with_elevation_suffix(self):
        """Test DMS coordinates with elevation suffixes"""
        dms_elevation_cases = [
            '40°42\'46"N 74°00\'22"W 1234m',    # Elevation with units
            '40°42\'46"N 74°00\'22"W 1234',     # Elevation without units
            'N40°42\'46" W74°00\'22" 1234ft',   # Cardinal first + elevation
        ]
        
        for dms_text in dms_elevation_cases:
            with self.subTest(dms=dms_text):
                result = self.parser.parse(dms_text)
                
                # Should either parse correctly (ignoring elevation) or fail gracefully
                if result is not None:
                    lat, lon, bounds, crs = result
                    # If it parses, coordinates should be reasonable
                    self.assertTrue(-90 <= lat <= 90, f"Parsed lat should be valid: {lat}")
                    self.assertTrue(-180 <= lon <= 180, f"Parsed lon should be valid: {lon}")
                    # Should be near New York area if parsed correctly
                    self.assertAlmostEqual(lat, 40.713, delta=1.0, msg="Should be near NYC latitude")
                    self.assertAlmostEqual(lon, -74.006, delta=1.0, msg="Should be near NYC longitude")
                    
    def test_mixed_format_elevation_cases(self):
        """Test various formats with elevation that could cause confusion"""
        mixed_cases = [
            # Cases that should be rejected
            ("UTM-like with elevation", "33 315428 5741324 1234", None),
            ("Large projected coords", "1000000 2000000 500", None),
            
            # Cases that should work (ignore elevation)
            ("Simple decimal + elev", "40.7, -74.0, 100", (40.7, -74.0)),
            ("Comma separated + elev", "40.7128, -74.0060, 100.5", (40.7128, -74.0060)),
        ]
        
        for description, text, expected in mixed_cases:
            with self.subTest(case=description):
                result = self.parser.parse(text)
                
                if expected is None:
                    self.assertIsNone(result, f"{description} should be rejected: {text}")
                else:
                    self.assertIsNotNone(result, f"{description} should parse: {text}")
                    lat, lon, bounds, crs = result
                    exp_lat, exp_lon = expected
                    self.assertAlmostEqual(lat, exp_lat, places=3)
                    self.assertAlmostEqual(lon, exp_lon, places=3)
                    
    def test_edge_case_number_patterns(self):
        """Test edge cases in number extraction with Z values"""
        edge_cases = [
            # Should work - valid coordinates with extra numbers
            ("Lat lon alt timestamp", "40.7128 -74.0060 100 1625097600", (40.7128, -74.0060)),
            
            # Should be rejected - looks like projected
            ("Zone easting northing alt", "33 315428 5741324 1234", None),
            ("Large values", "500000 4500000 1000", None),
            
            # Should work - coordinates in valid range despite extra values  
            ("Small coordinates + extra", "45.5 9.2 100 200", (45.5, 9.2)),
        ]
        
        for description, text, expected in edge_cases:
            with self.subTest(case=description):
                result = self.parser.parse(text)
                
                if expected is None:
                    self.assertIsNone(result, f"{description} should be rejected: {text}")
                else:
                    self.assertIsNotNone(result, f"{description} should parse: {text}")
                    lat, lon, bounds, crs = result
                    exp_lat, exp_lon = expected
                    self.assertAlmostEqual(lat, exp_lat, places=3)
                    self.assertAlmostEqual(lon, exp_lon, places=3)


class TestProjectedCoordinateDetection(unittest.TestCase):
    """Test the projected coordinate detection logic specifically"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = Mock()
        self.mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        
        self.mock_iface = Mock()
        self.mock_canvas = Mock()
        self.mock_map_settings = Mock()
        self.mock_map_settings.destinationCrs.return_value = epsg4326
        self.mock_canvas.mapSettings.return_value = self.mock_map_settings
        self.mock_iface.mapCanvas.return_value = self.mock_canvas
        
        self.parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
        
    def test_utm_like_detection(self):
        """Test that UTM-like coordinate values are properly rejected through public interface."""
        # Test cases that should be rejected as UTM-like patterns
        utm_test_cases = [
            "33 315428 5741324",        # Zone, Easting, Northing
            "55 600000 4500000",        # Different zone  
            "12 500000 3000000 100",    # With elevation
        ]
        
        for test_input in utm_test_cases:
            with self.subTest(test_input=test_input):
                result = self.parser.parse(test_input)
                # Should be rejected (return None) rather than misinterpreted
                self.assertIsNone(result, 
                    f"UTM-like pattern '{test_input}' should be rejected")
                
    def test_valid_geographic_coordinates(self):
        """Test that valid geographic coordinates are correctly parsed (not rejected)"""
        # These should be parsed successfully as valid geographic coordinates
        valid_coordinate_cases = [
            ("40.7128, -74.0060", (40.7128, -74.0060)),        # NYC
            ("51.5074, -0.1278", (51.5074, -0.1278)),          # London  
            ("-33.8688, 151.2093", (-33.8688, 151.2093)),      # Sydney
            ("35.6762, 139.6503", (35.6762, 139.6503)),        # Tokyo
            ("89.9, 179.9", (89.9, 179.9)),                    # Near poles/antimeridian
            ("-89.9, -179.9", (-89.9, -179.9)),                # Other extreme
        ]
        
        for coord_text, expected in valid_coordinate_cases:
            with self.subTest(coords=coord_text):
                result = self.parser.parse(coord_text)
                self.assertIsNotNone(result, 
                    f"Valid coordinates should parse: {coord_text}")
                lat, lon, bounds, crs = result
                exp_lat, exp_lon = expected
                self.assertAlmostEqual(lat, exp_lat, places=3)
                self.assertAlmostEqual(lon, exp_lon, places=3)
                    
    def test_large_invalid_coordinates(self):
        """Test that obviously invalid large coordinates are rejected"""
        # These should be rejected as invalid/projected coordinates  
        invalid_coordinate_cases = [
            "1000 2000",                # Clearly not geographic
            "315428 5741324",           # UTM-like without zone
            "500000 4500000",           # Large projected values
            "200 300",                  # Over geographic limits
        ]
        
        for coord_text in invalid_coordinate_cases:
            with self.subTest(coords=coord_text):
                result = self.parser.parse(coord_text)
                self.assertIsNone(result, 
                    f"Invalid large coordinates should be rejected: {coord_text}")


class TestSpecificZValueBugCases(unittest.TestCase):
    """Test specific bug cases with Z values that caused issues"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = Mock()
        self.mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        
        self.mock_iface = Mock()
        self.mock_canvas = Mock()
        self.mock_map_settings = Mock()
        self.mock_map_settings.destinationCrs.return_value = epsg4326
        self.mock_canvas.mapSettings.return_value = self.mock_map_settings
        self.mock_iface.mapCanvas.return_value = self.mock_canvas
        
        self.parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
        
    def test_original_failing_wkb(self):
        """Test the original WKB that gave 'Invalid Coordinate' error"""
        # This was the failing case from the user
        failing_wkb = "01010000A0281A00005396BF88FF9560405296C6D462D64040A857CA32C41D7240"
        
        result = self.parser.parse(failing_wkb)
        
        # Should now parse successfully instead of giving "Invalid Coordinate"
        self.assertIsNotNone(result, 
            "Original failing WKB should now parse successfully")
            
        lat, lon, bounds, crs = result
        
        # Verify reasonable coordinates (Japan area based on analysis)
        self.assertTrue(30 <= lat <= 40, f"Latitude {lat} should be in Japan region") 
        self.assertTrue(130 <= lon <= 140, f"Longitude {lon} should be in Japan region")
        
    def test_utm_elevation_fallback_prevention(self):
        """Test that UTM with elevation doesn't fall to wrong number extraction"""
        # This was the critical issue - UTM with elevation falling to number extraction
        utm_elevation = "33N 315428 5741324 1234"
        
        result = self.parser.parse(utm_elevation)
        
        # Should be rejected completely rather than misinterpreting zone as latitude
        self.assertIsNone(result, 
            "UTM with elevation should be rejected, not misinterpreted")
        
        # Additional verification: ensure parse does not misinterpret UTM with elevation
        # The parser should reject this pattern, as asserted above.
            
    def test_similar_problematic_patterns(self):
        """Test similar patterns that could cause the same issue"""
        problematic_patterns = [
            "12S 234567 8901234 567",        # Different UTM zone with elevation
            "45N 678901 2345678 890",        # Another UTM variant
            "1 500000 4000000 100",          # Zone-like + large coordinates
        ]
        
        for pattern in problematic_patterns:
            with self.subTest(pattern=pattern):
                result = self.parser.parse(pattern)
                
                # All should be rejected to prevent misinterpretation
                self.assertIsNone(result, 
                    f"Problematic pattern should be rejected: {pattern}")


class TestWKBPointZMGeometries(unittest.TestCase):
    """Test WKB parsing with PointZM (4D) geometries to ensure base type detection works."""
    
    def setUp(self):
        """Set up test parser with mocked QGIS environment."""
        self.mock_settings = Mock()
        self.mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        
        self.mock_iface = Mock()
        self.mock_canvas = Mock()
        self.mock_map_settings = Mock()
        self.mock_map_settings.destinationCrs.return_value = epsg4326
        self.mock_canvas.mapSettings.return_value = self.mock_map_settings
        self.mock_iface.mapCanvas.return_value = self.mock_canvas
        
        self.parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
    
    def test_pointzm_geometry_detection(self):
        """Test that PointZM geometries are properly detected and parsed through public interface."""
        # PointZM geometry type: Point (1) + Z flag (0x80000000) + M flag (0x40000000) = 0xC0000001
        # WKB structure breakdown:
        # 01 - Little endian byte order
        # C0000001 - Geometry type (PointZM = 0xC0000001)
        # 0000000000002440 - X coordinate (10.0 as IEEE 754 double)
        # 0000000000003440 - Y coordinate (20.0 as IEEE 754 double) 
        # 0000000000003440 - Z coordinate (30.0 as IEEE 754 double)
        # 0000000000004440 - M coordinate (40.0 as IEEE 754 double)
        pointzm_wkb = "01C000000100000000000024400000000000003440000000000000344000000000000044400"
        
        # Test through public parse method rather than private _try_wkb
        result = self.parser.parse(pointzm_wkb)
        
        self.assertIsNotNone(result, "PointZM WKB should be successfully parsed")
        lat, lon, bounds, crs = result
        
        # Verify coordinates are extracted correctly (ignoring Z and M dimensions)
        self.assertAlmostEqual(lat, 20.0, places=1)
        self.assertAlmostEqual(lon, 10.0, places=1)
    
    def test_pointm_geometry_detection(self):
        """Test that PointM geometries are properly detected and parsed through public interface."""
        # PointM geometry type: Point (1) + M flag (0x40000000) = 0x40000001
        # WKB structure breakdown:
        # 01 - Little endian byte order
        # 01000040 - Geometry type (PointM = 0x40000001)
        # 0000000000002E40 - X coordinate (15.0 as IEEE 754 double)
        # 0000000000003940 - Y coordinate (25.0 as IEEE 754 double)
        # 0000000000004940 - M coordinate (50.0 as IEEE 754 double)
        pointm_wkb = "01010000400000000000000000002E4000000000000039400000000000004940"
        
        # Test through public parse method rather than private _try_wkb
        result = self.parser.parse(pointm_wkb)
        
        self.assertIsNotNone(result, "PointM WKB should be successfully parsed")
        lat, lon, bounds, crs = result
        
        # Verify coordinates are extracted correctly (ignoring M dimension)
        self.assertAlmostEqual(lat, 25.0, places=1)
        self.assertAlmostEqual(lon, 15.0, places=1)


if __name__ == "__main__":
    # Run all test classes
    test_classes = [
        TestZCoordinateHandling,
        TestProjectedCoordinateDetection, 
        TestSpecificZValueBugCases,
        TestWKBPointZMGeometries
    ]
    
    total_tests = 0
    total_failures = 0
    
    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        total_failures += len(result.failures) + len(result.errors)
    
    print("\n" + "=" * 70)
    print(f"🏁 Total Tests: {total_tests}")
    print(f"{'✅ All Passed!' if total_failures == 0 else f'❌ {total_failures} Failed'}")
    
    if total_failures > 0:
        sys.exit(1)
    else:
        print("🎉 All Z coordinate handling tests passed!")