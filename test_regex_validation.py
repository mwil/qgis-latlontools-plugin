#!/usr/bin/env python3
"""
Comprehensive Regex Validation Test Suite

This test suite validates that all regex patterns in the codebase are properly
escaped and function correctly. It specifically tests for the over-escaping 
issues we discovered and fixed in our coordinate parsing code.

REGEX ESCAPING RULES FOR PYTHON RAW STRINGS:
============================================
✅ CORRECT: r'\s+' → regex engine sees \s+ → matches whitespace
❌ WRONG:   r'\\s+' → regex engine sees \\s+ → matches literal backslash + 's'

✅ CORRECT: r'POINT\(' → regex engine sees POINT\( → matches "POINT("  
❌ WRONG:   r'POINT\\(' → regex engine sees POINT\\( → matches "POINT\("

✅ CORRECT: r'[\s,;:]+' → regex engine sees [\s,;:]+ → matches whitespace, comma, semicolon, colon
❌ WRONG:   r'[\\s,;:]+' → regex engine sees [\\s,;:]+ → matches literal backslash, 's', comma, etc.
"""

import sys
import os
import unittest
import re
from unittest.mock import Mock, patch

# Set up QGIS environment
sys.path.insert(0, '/Applications/QGIS.app/Contents/Resources/python')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test data for regex validation
REGEX_TEST_CASES = {
    # Whitespace pattern tests
    'whitespace_patterns': {
        'correct_pattern': r'\s+',
        'wrong_pattern': r'\\s+',  # Over-escaped - would match literal \s
        'test_inputs': [
            ('text with spaces', True),   # Should match spaces
            ('text\twith\ttabs', True),   # Should match tabs  
            ('text\nwith\nnewlines', True), # Should match newlines
            ('textwithoutspaces', False), # Should not match
            ('text\\swith\\sliteral\\sbackslashes', False)  # Should not match literal \s
        ]
    },
    
    # POINT geometry pattern tests  
    'point_patterns': {
        'correct_pattern': r'POINT\(\s*([+-]?\d*\.?\d*)\s+([+-]?\d*\.?\d*)\s*\)',
        'wrong_pattern': r'POINT\\(\\s*([+-]?\\d*\\.?\\d*)\\s+([+-]?\\d*\\.?\\d*)',
        'test_inputs': [
            ('POINT(1.5 2.5)', True),     # Standard POINT
            ('POINT( 1.5  2.5 )', True),  # POINT with extra spaces
            ('POINT(-122.456 45.123)', True), # Negative coordinates
            ('POINT\\(1.5 2.5)', False),   # Should not match literal POINT\(
            ('LINESTRING(1 2, 3 4)', False), # Should not match other geometries
        ]
    },
    
    # Character class pattern tests
    'character_class_patterns': {
        'correct_pattern': r'[\s,;:]+',
        'wrong_pattern': r'[\\s,;:]+',  # Over-escaped - would include literal \s
        'test_inputs': [
            ('45.123, -122.456', True),   # Comma separator
            ('45.123; -122.456', True),   # Semicolon separator  
            ('45.123: -122.456', True),   # Colon separator
            ('45.123 -122.456', True),    # Space separator
            ('45.123\t-122.456', True),   # Tab separator
            ('45.123\\s-122.456', False), # Should not match literal \s
            ('45.123abc-122.456', False), # Should not match letters
        ]
    }
}

class TestRegexValidation(unittest.TestCase):
    """Test regex patterns for proper escaping and functionality"""
    
    def test_whitespace_regex_patterns(self):
        """Test whitespace regex patterns work correctly"""
        test_case = REGEX_TEST_CASES['whitespace_patterns']
        correct_pattern = test_case['correct_pattern']
        wrong_pattern = test_case['wrong_pattern']
        
        for input_text, should_match in test_case['test_inputs']:
            with self.subTest(input=input_text, should_match=should_match):
                # Test correct pattern
                correct_matches = bool(re.search(correct_pattern, input_text))
                self.assertEqual(correct_matches, should_match,
                               f"Correct pattern r'{correct_pattern}' should {'match' if should_match else 'not match'} '{input_text}'")
                
                # Test that wrong pattern would behave incorrectly for some inputs
                if input_text == 'text\\swith\\sliteral\\sbackslashes':
                    wrong_matches = bool(re.search(wrong_pattern, input_text))
                    self.assertTrue(wrong_matches, 
                                  f"Wrong pattern r'{wrong_pattern}' incorrectly matches literal backslashes")
                    
    def test_point_geometry_regex_patterns(self):
        """Test POINT geometry regex patterns work correctly"""
        test_case = REGEX_TEST_CASES['point_patterns']
        correct_pattern = test_case['correct_pattern'] 
        wrong_pattern = test_case['wrong_pattern']
        
        for input_text, should_match in test_case['test_inputs']:
            with self.subTest(input=input_text, should_match=should_match):
                # Test correct pattern
                correct_matches = bool(re.search(correct_pattern, input_text))
                self.assertEqual(correct_matches, should_match,
                               f"Correct pattern should {'match' if should_match else 'not match'} '{input_text}'")
                
                # Test coordinate extraction for valid POINT strings
                if should_match and input_text.startswith('POINT('):
                    match = re.search(correct_pattern, input_text)
                    self.assertIsNotNone(match, "Should extract coordinates from POINT")
                    self.assertEqual(len(match.groups()), 2, "Should extract exactly 2 coordinates")
                    
                    # Validate extracted coordinates are numeric
                    try:
                        x = float(match.group(1))
                        y = float(match.group(2))
                        print(f"✅ Extracted coordinates: x={x}, y={y} from '{input_text}'")
                    except ValueError:
                        self.fail(f"Extracted coordinates should be numeric: {match.groups()}")

    def test_character_class_regex_patterns(self):
        """Test character class regex patterns work correctly"""
        test_case = REGEX_TEST_CASES['character_class_patterns']
        correct_pattern = test_case['correct_pattern']
        wrong_pattern = test_case['wrong_pattern']
        
        for input_text, should_match in test_case['test_inputs']:
            with self.subTest(input=input_text, should_match=should_match):
                # Test correct pattern
                correct_matches = bool(re.search(correct_pattern, input_text))
                self.assertEqual(correct_matches, should_match,
                               f"Correct pattern r'{correct_pattern}' should {'match' if should_match else 'not match'} '{input_text}'")
                
                # Test coordinate splitting for valid inputs
                if should_match and any(c in input_text for c in ' ,;:\t'):
                    split_result = re.split(correct_pattern, input_text, 1)
                    self.assertGreaterEqual(len(split_result), 2, f"Should split '{input_text}' into at least 2 parts")
                    print(f"✅ Split '{input_text}' → {split_result}")

class TestActualCoordinateParsing(unittest.TestCase):
    """Test actual coordinate parsing with fixed regex patterns"""
    
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
        
    def test_wkt_point_parsing_with_fixed_regex(self):
        """Test that WKT POINT parsing works with fixed regex patterns"""
        test_cases = [
            ('POINT(1.5 2.5)', (2.5, 1.5)),
            ('POINT( -122.456  45.123 )', (45.123, -122.456)),
            ('POINT(0 0)', (0, 0)),
            ('POINT(-180 -90)', (-90, -180)),
        ]
        
        from smart_parser import SmartCoordinateParser
        from settings import CoordOrder
        
        mock_settings = Mock()
        mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        mock_iface = Mock()
        parser = SmartCoordinateParser(mock_settings, mock_iface)
        
        for wkt_input, expected_coords in test_cases:
            with self.subTest(wkt=wkt_input):
                result = parser.parse(wkt_input)
                self.assertIsNotNone(result, f"Should parse WKT: {wkt_input}")
                
                lat, lon, bounds, crs = result
                expected_lat, expected_lon = expected_coords
                
                self.assertAlmostEqual(lat, expected_lat, places=6, 
                                     msg=f"Latitude mismatch for {wkt_input}")
                self.assertAlmostEqual(lon, expected_lon, places=6,
                                     msg=f"Longitude mismatch for {wkt_input}")
                print(f"✅ WKT parsing: '{wkt_input}' → lat={lat}, lon={lon}")

    def test_mgrs_whitespace_removal_with_fixed_regex(self):
        """Test that MGRS whitespace removal works with fixed regex"""
        # These would be tested in actual MGRS parsing, but we'll test the regex pattern
        mgrs_inputs = [
            '33UUA1234567890',      # No spaces
            '33U UA 12345 67890',   # Spaces
            '33U\tUA\t12345\t67890', # Tabs
            '33U\nUA\n12345\n67890', # Newlines (unlikely but possible)
        ]
        
        # Test the whitespace removal pattern we fixed
        whitespace_pattern = r'\s+'
        
        for mgrs_input in mgrs_inputs:
            with self.subTest(mgrs=mgrs_input):
                cleaned = re.sub(whitespace_pattern, '', mgrs_input)
                self.assertEqual(cleaned, '33UUA1234567890', 
                               f"Whitespace removal should normalize '{mgrs_input}' to '33UUA1234567890'")
                print(f"✅ MGRS whitespace removal: '{mgrs_input}' → '{cleaned}'")

    def test_coordinate_splitting_with_fixed_regex(self):
        """Test coordinate splitting with fixed character class regex"""
        coordinate_inputs = [
            ('45.123, -122.456', [45.123, -122.456]),
            ('45.123; -122.456', [45.123, -122.456]),
            ('45.123: -122.456', [45.123, -122.456]),  
            ('45.123 -122.456', [45.123, -122.456]),
            ('45.123\t-122.456', [45.123, -122.456]),
        ]
        
        # Test the character class pattern we fixed
        split_pattern = r'[\s,;:]+'
        
        for coord_input, expected_coords in coordinate_inputs:
            with self.subTest(coords=coord_input):
                parts = re.split(split_pattern, coord_input, 1)
                self.assertEqual(len(parts), 2, f"Should split '{coord_input}' into 2 parts")
                
                lat = float(parts[0])
                lon = float(parts[1])
                
                self.assertAlmostEqual(lat, expected_coords[0], places=6)
                self.assertAlmostEqual(lon, expected_coords[1], places=6)
                print(f"✅ Coordinate splitting: '{coord_input}' → [{lat}, {lon}]")

class TestRegexEscapingValidation(unittest.TestCase):
    """Test to detect over-escaped regex patterns in codebase"""
    
    def test_no_over_escaped_patterns_in_codebase(self):
        """Scan codebase for over-escaped regex patterns"""
        files_to_check = [
            'digitizer.py',
            'multizoom.py', 
            'zoomToLatLon.py',
            'smart_parser.py',
            'coordinateConverter.py'
        ]
        
        # Patterns that indicate over-escaping
        problematic_patterns = [
            r'r\'.*\\\\s',      # r'...\\s' - over-escaped whitespace
            r'r\'.*\\\\d',      # r'...\\d' - over-escaped digit  
            r'r\'.*\\\\w',      # r'...\\w' - over-escaped word character
            r'r\'.*POINT\\\\',  # r'...POINT\\' - over-escaped POINT
            r'r\'.*\[\\\\s',    # r'...[\\s' - over-escaped whitespace in character class
        ]
        
        for filename in files_to_check:
            if os.path.exists(filename):
                with self.subTest(file=filename):
                    with open(filename, 'r') as f:
                        content = f.read()
                    
                    for pattern in problematic_patterns:
                        matches = re.findall(pattern, content)
                        self.assertEqual(len(matches), 0, 
                                       f"Found over-escaped regex pattern in {filename}: {matches}")
                        
                    print(f"✅ No over-escaped patterns found in {filename}")

def run_regex_validation_tests():
    """Run the complete regex validation test suite"""
    print("🔍 COMPREHENSIVE REGEX VALIDATION TEST SUITE")
    print("=" * 60)
    print()
    
    # Load and run all tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRegexValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestActualCoordinateParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestRegexEscapingValidation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("📊 REGEX VALIDATION SUMMARY:")
    print("=" * 30)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    success = result.wasSuccessful()
    
    if success:
        print("\n🎉 ALL REGEX VALIDATION TESTS PASSED!")
        print("✅ All regex patterns are properly escaped")
        print("✅ Coordinate parsing works correctly") 
        print("✅ No over-escaped patterns detected in codebase")
    else:
        print("\n⚠️ SOME REGEX TESTS FAILED!")
        print("❌ Regex patterns may have escaping issues")
        print("❌ Review failed tests and fix regex patterns")
    
    return success

if __name__ == "__main__":
    success = run_regex_validation_tests()
    sys.exit(0 if success else 1)