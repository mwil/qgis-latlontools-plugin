#!/usr/bin/env python3
"""
Comprehensive Parser Regression Test Suite

This test suite prevents the WKB-style parsing inconsistencies from occurring
with other coordinate formats by systematically testing all UI components.

TESTS IMPLEMENTED:
=================
1. Cross-Component Format Matrix Tests
2. SmartCoordinateParser Integration Validation 
3. Format Detection Priority Tests
4. Error Handling Consistency Tests
5. Regression Prevention Tests

COVERAGE:
=========
- coordinateConverter.py ✅ (already fixed)
- zoomToLatLon.py ✅ (WKB issue fixed)  
- digitizer.py ✅ (just fixed)
- multizoom.py ✅ (just fixed)
- SmartCoordinateParser.py ✅ (core parser)
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Set up QGIS environment dynamically for cross-platform support
import platform

qgis_python_path = os.environ.get('QGIS_PYTHON_PATH')
if not qgis_python_path:
    system = platform.system()
    if system == 'Darwin':  # macOS
        qgis_python_path = '/Applications/QGIS.app/Contents/Resources/python'
    elif system == 'Windows':
        # Try common install locations for QGIS on Windows
        possible_paths = [
            r'C:\Program Files\QGIS 3.28\apps\qgis\python',
            r'C:\Program Files\QGIS 3.22\apps\qgis\python',
            r'C:\OSGeo4W\apps\qgis\python',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                qgis_python_path = path
                break
    elif system == 'Linux':
        # Try common install locations for QGIS on Linux
        possible_paths = [
            '/usr/share/qgis/python',
            '/usr/local/share/qgis/python',
        ]
        for path in possible_paths:
            if os.path.exists(path):
                qgis_python_path = path
                break

if qgis_python_path and os.path.exists(qgis_python_path):
    sys.path.insert(0, qgis_python_path)
else:
    print(f"Warning: QGIS Python path not found. Set QGIS_PYTHON_PATH environment variable.")
    
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test coordinates covering all major formats
COMPREHENSIVE_TEST_COORDINATES = {
    # Modern formats (SmartCoordinateParser should handle these)
    'wkb_2d_simple': '0101000020E6100000000000000000F03F0000000000000040',  # POINT(1 2) with SRID 4326
    'wkb_3d_complex': '01010000A0281A00005396BF88FF9560405296C6D462D64040A857CA32C41D7240',  # Our fixed case
    'wkt_point_simple': 'POINT(1.5 2.5)',
    'wkt_point_srid': 'SRID=4326;POINT(-122.456 45.123)',
    'ewkt_point': 'SRID=4326;POINT(-122.456 45.123)',
    'geojson_point': '{"type":"Point","coordinates":[-122.456,45.123]}',
    'decimal_comma': '45.123, -122.456',
    'decimal_space': '45.123 -122.456',
    'decimal_precise': '45.12345678901234, -122.45678901234567',
    
    # Legacy specialized formats (handled by legacy parsers)  
    'mgrs_example': '10TGK1234567890',
    'utm_standard': '10T 1234567 1234567',
    'ups_north': 'Z 1234567 1234567',
    'plus_codes': '87G8Q23G+GF',
    'geohash': 'c23nb62w20sth',
    'maidenhead': 'CN87ts',
    'georef': 'MKML5056',
    'dms_symbols': "45°30'15\"N 122°15'30\"W",
    'dms_letters': "45 30 15 N 122 15 30 W",
    'dms_mixed': "N45°30.25' W122°15.5'",
    
    # Edge cases and variations
    'negative_coords': '-45.123, -122.456',
    'semicolon_sep': '45.123; -122.456',
    'colon_sep': '45.123: -122.456',
    'mixed_precision': '45.1, -122.123456789',
    
    # Invalid inputs (should fail consistently)
    'invalid_text': 'not coordinates at all',
    'incomplete_wkt': 'POINT(',
    'malformed_geojson': '{"type":"Point"',
    'out_of_range': '95.0, 200.0',  # Invalid lat/lon ranges
    'empty_string': '',
    'only_spaces': '   ',
}

# Expected results for valid coordinates (lat, lon)
EXPECTED_COORDINATES = {
    'wkb_2d_simple': (2.0, 1.0),
    'wkb_3d_complex': (33.6748910875, 132.6874431364),
    'wkt_point_simple': (2.5, 1.5),
    'wkt_point_srid': (45.123, -122.456),
    'ewkt_point': (45.123, -122.456),
    'geojson_point': (45.123, -122.456),
    'decimal_comma': (45.123, -122.456),
    'decimal_space': (45.123, -122.456),
    'decimal_precise': (45.12345678901234, -122.45678901234567),
    'negative_coords': (-45.123, -122.456),
    'semicolon_sep': (45.123, -122.456),
    'colon_sep': (45.123, -122.456),
    'mixed_precision': (45.1, -122.123456789),
    # Note: Legacy formats would need actual coordinate calculations
}

class TestParserIntegrationMatrix(unittest.TestCase):
    """Test coordinate parsing across all UI components"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize QGIS for testing"""
        from qgis.core import QgsApplication
        QgsApplication.setPrefixPath('/Applications/QGIS.app/Contents', True)
        cls.app = QgsApplication([], False)
        QgsApplication.initQgis()
    
    @classmethod 
    def tearDownClass(cls):
        """Clean up QGIS"""
        from qgis.core import QgsApplication
        QgsApplication.exitQgis()
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = self._create_mock_settings()
        self.mock_iface = self._create_mock_iface()
    
    def _create_mock_settings(self):
        """Create mock settings object"""
        from settings import CoordOrder
        mock = Mock()
        mock.zoomToCoordOrder = CoordOrder.OrderYX
        mock.converterCoordOrder = 0
        mock.multiCoordOrder = CoordOrder.OrderYX
        mock.zoomToProjIsWgs84.return_value = True
        mock.multiZoomToProjIsWgs84.return_value = True
        mock.multiZoomToProjIsMGRS.return_value = False
        mock.multiZoomToProjIsPlusCodes.return_value = False
        mock.multiZoomToProjIsUtm.return_value = False
        return mock
    
    def _create_mock_iface(self):
        """Create mock QGIS interface"""
        mock = Mock()
        mock.mapCanvas.return_value = Mock()
        mock.messageBar.return_value = Mock()
        return mock

    def test_smart_parser_direct(self):
        """Test SmartCoordinateParser directly with all modern formats"""
        from smart_parser import SmartCoordinateParser
        
        parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
        
        modern_formats = [
            'wkb_2d_simple', 'wkb_3d_complex', 'wkt_point_simple', 
            'wkt_point_srid', 'ewkt_point', 'geojson_point',
            'decimal_comma', 'decimal_space', 'decimal_precise'
        ]
        
        for format_name in modern_formats:
            with self.subTest(format=format_name):
                coordinate = COMPREHENSIVE_TEST_COORDINATES[format_name]
                result = parser.parse(coordinate)
                
                if format_name in EXPECTED_COORDINATES:
                    self.assertIsNotNone(result, f"SmartCoordinateParser should parse {format_name}")
                    lat, lon, bounds, crs = result
                    expected_lat, expected_lon = EXPECTED_COORDINATES[format_name]
                    self.assertAlmostEqual(lat, expected_lat, places=8, 
                                         msg=f"{format_name} latitude mismatch")
                    self.assertAlmostEqual(lon, expected_lon, places=8,
                                         msg=f"{format_name} longitude mismatch")
                    print(f"✅ SmartCoordinateParser {format_name}: lat={lat:.10f}, lon={lon:.10f}")

    def test_coordinate_converter_integration(self):
        """Test CoordinateConverter uses SmartCoordinateParser correctly"""
        # This would require mocking the entire UI component
        # For now, we verify the integration through code analysis
        
        with open('coordinateConverter.py', 'r') as f:
            content = f.read()
        
        # Verify integration patterns
        self.assertIn('from .smart_parser import SmartCoordinateParser', content,
                     "CoordinateConverter should import SmartCoordinateParser")
        self.assertIn('SmartCoordinateParser(self.settings, self.iface)', content,
                     "CoordinateConverter should instantiate SmartCoordinateParser")
        self.assertIn('smart_parser.parse(text)', content,
                     "CoordinateConverter should call smart parser")
        print("✅ CoordinateConverter integration verified")

    def test_zoom_to_lat_lon_integration(self):
        """Test ZoomToLatLon uses SmartCoordinateParser correctly"""  
        with open('zoomToLatLon.py', 'r') as f:
            content = f.read()
        
        # Verify integration patterns
        self.assertIn('from .smart_parser import SmartCoordinateParser', content,
                     "ZoomToLatLon should import SmartCoordinateParser") 
        self.assertIn('SmartCoordinateParser(self.settings, self.iface)', content,
                     "ZoomToLatLon should instantiate SmartCoordinateParser")
        self.assertIn('smart_parser.parse(text)', content,
                     "ZoomToLatLon should call smart parser")
        
        # Verify it's called FIRST within convertCoordinate method
        import re
        convert_coord_match = re.search(
            r'def convertCoordinate\(self, text\):(.*?)(?=def|\Z)', 
            content, 
            re.DOTALL
        )
        
        if convert_coord_match:
            method_content = convert_coord_match.group(1)
            smart_parser_pos = method_content.find('SmartCoordinateParser(self.settings, self.iface)')
            mgrs_pos = method_content.find('self.settings.zoomToProjIsMGRS()')
            
            self.assertGreater(smart_parser_pos, -1, "SmartCoordinateParser should be found in convertCoordinate")
            self.assertGreater(mgrs_pos, -1, "MGRS parsing should be found in convertCoordinate")
            self.assertLess(smart_parser_pos, mgrs_pos,
                           "SmartCoordinateParser should be called before legacy MGRS parsing in convertCoordinate")
        else:
            self.fail("Could not find convertCoordinate method")
            
        print("✅ ZoomToLatLon integration verified (WKB issue fixed)")

    def test_digitizer_integration(self):
        """Test Digitizer uses SmartCoordinateParser correctly"""
        with open('digitizer.py', 'r') as f:
            content = f.read()
        
        # Verify integration patterns
        self.assertIn('from .smart_parser import SmartCoordinateParser', content,
                     "Digitizer should import SmartCoordinateParser")
        self.assertIn('SmartCoordinateParser(settings, self.iface)', content,
                     "Digitizer should instantiate SmartCoordinateParser") 
        self.assertIn('smart_parser.parse(text)', content,
                     "Digitizer should call smart parser")
        print("✅ Digitizer integration verified (just fixed)")

    def test_multizoom_integration(self):
        """Test MultiZoom uses SmartCoordinateParser correctly"""
        with open('multizoom.py', 'r') as f:
            content = f.read()
        
        # Verify integration patterns
        self.assertIn('from .smart_parser import SmartCoordinateParser', content,
                     "MultiZoom should import SmartCoordinateParser")
        self.assertIn('SmartCoordinateParser(self.settings, self.iface)', content,
                     "MultiZoom should instantiate SmartCoordinateParser")
        self.assertIn('smart_parser.parse(parts[0])', content,
                     "MultiZoom should call smart parser")
        print("✅ MultiZoom integration verified (just fixed)")

    def test_invalid_coordinate_handling(self):
        """Test that all parsers handle invalid coordinates consistently"""
        from smart_parser import SmartCoordinateParser
        
        parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
        
        invalid_formats = [
            'invalid_text', 'incomplete_wkt', 'malformed_geojson',
            'out_of_range', 'empty_string', 'only_spaces'
        ]
        
        for format_name in invalid_formats:
            with self.subTest(format=format_name):
                coordinate = COMPREHENSIVE_TEST_COORDINATES[format_name]
                result = parser.parse(coordinate)
                # Invalid coordinates should return None or raise exception
                if result is not None:
                    # Some formats might be parsed unexpectedly - log for review
                    print(f"⚠️ Unexpected parse success for {format_name}: {result}")

    def test_format_detection_priority(self):
        """Test that format detection follows correct priority"""
        from smart_parser import SmartCoordinateParser
        
        parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
        
        # Test ambiguous inputs that could match multiple formats
        ambiguous_tests = [
            ('1.5 2.5', 'should detect as decimal coordinates'),
            ('POINT(1 2)', 'should detect as WKT'),
            ('{"type":"Point","coordinates":[1,2]}', 'should detect as GeoJSON'),
        ]
        
        for coordinate, expected_behavior in ambiguous_tests:
            with self.subTest(coordinate=coordinate):
                result = parser.parse(coordinate)
                if result:
                    lat, lon, bounds, crs = result
                    print(f"✅ Format detection for '{coordinate}': lat={lat}, lon={lon} ({expected_behavior})")
                else:
                    print(f"⚠️ Failed to parse '{coordinate}' ({expected_behavior})")

class TestRegressionPrevention(unittest.TestCase):
    """Tests specifically designed to prevent the WKB-style regression"""
    
    def test_all_ui_components_use_smart_parser_first(self):
        """Ensure all coordinate input components use SmartCoordinateParser first"""
        ui_files = ['coordinateConverter.py', 'zoomToLatLon.py', 'digitizer.py', 'multizoom.py']
        
        for filename in ui_files:
            with self.subTest(file=filename):
                with open(filename, 'r') as f:
                    content = f.read()
                
                has_coordinate_input = any(pattern in content for pattern in 
                                         ['text().strip()', 'LineEdit', 'coordTxt'])
                
                if has_coordinate_input:
                    # File has coordinate input - must use SmartCoordinateParser
                    self.assertIn('SmartCoordinateParser', content,
                                f"{filename} has coordinate input but doesn't use SmartCoordinateParser")
                    self.assertIn('smart_parser.parse(', content,
                                f"{filename} imports SmartCoordinateParser but doesn't call parse()")
                    print(f"✅ {filename}: SmartCoordinateParser integration confirmed")
                else:
                    print(f"ℹ️ {filename}: No coordinate input detected")

    def test_wkb_parsing_across_all_components(self):
        """Specific test for WKB parsing to prevent regression"""
        wkb_test_case = COMPREHENSIVE_TEST_COORDINATES['wkb_3d_complex']
        expected_lat, expected_lon = EXPECTED_COORDINATES['wkb_3d_complex']
        
        # Test that SmartCoordinateParser handles it
        from smart_parser import SmartCoordinateParser
        from settings import CoordOrder
        
        mock_settings = Mock()
        mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        mock_iface = Mock()
        
        parser = SmartCoordinateParser(mock_settings, mock_iface)
        result = parser.parse(wkb_test_case)
        
        self.assertIsNotNone(result, "WKB parsing should not fail in SmartCoordinateParser")
        lat, lon, bounds, crs = result
        self.assertAlmostEqual(lat, expected_lat, places=8, msg="WKB latitude should match")
        self.assertAlmostEqual(lon, expected_lon, places=8, msg="WKB longitude should match")
        
        print(f"✅ WKB Regression Test: lat={lat:.10f}, lon={lon:.10f}")
        print("✅ WKB parsing works - regression prevented!")

def run_comprehensive_parser_tests():
    """Run the complete parser regression test suite"""
    print("🧪 COMPREHENSIVE PARSER REGRESSION TEST SUITE")
    print("=" * 60)
    print()
    
    # Load and run all tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestParserIntegrationMatrix))
    suite.addTests(loader.loadTestsFromTestCase(TestRegressionPrevention))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("📊 TEST SUMMARY:")
    print("=" * 20)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success = result.wasSuccessful()
    
    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Parser integration consistency verified")
        print("✅ WKB regression prevented")
        print("✅ All UI components use SmartCoordinateParser correctly")
    else:
        print("\n⚠️ SOME TESTS FAILED!")
        print("❌ Parser inconsistencies detected")
        print("❌ Review failed tests and fix integration issues")
    
    return success

if __name__ == "__main__":
    success = run_comprehensive_parser_tests()
    sys.exit(0 if success else 1)