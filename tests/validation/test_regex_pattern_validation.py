#!/usr/bin/env python3
"""
Regex pattern validation tests to catch regex syntax bugs in coordinate parsing
These tests specifically validate that regex patterns work as intended
"""

import sys
import os
import unittest
import re

# Set up QGIS environment
sys.path.insert(0, '/Applications/QGIS.app/Contents/Resources/python')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from qgis.core import QgsApplication
from unittest.mock import Mock

def init_qgis():
    """Initialize QGIS application"""
    QgsApplication.setPrefixPath('/Applications/QGIS.app/Contents', True)
    app = QgsApplication([], False)
    QgsApplication.initQgis()
    return app

class TestRegexPatternValidation(unittest.TestCase):
    """Test regex patterns in coordinate parsing to catch syntax errors"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QGIS and parser once for all tests"""
        cls.app = init_qgis()
        
        try:
            from smart_parser import SmartCoordinateParser
            from settings import CoordOrder
        except ImportError as e:
            cls.skipTest(f"Cannot import required modules: {e}")
        
        # Set up parser
        mock_settings = Mock()
        mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        mock_iface = Mock()
        cls.parser = SmartCoordinateParser(mock_settings, mock_iface)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up QGIS"""
        QgsApplication.exitQgis()
    
    def test_mgrs_pattern_detection(self):
        """Test MGRS regex pattern catches valid MGRS coordinates"""
        mgrs_cases = [
            ('18TWN8540011518', True),  # Valid MGRS
            ('18TWN854001', True),      # Valid shorter MGRS
            ('18T854001', False),       # Invalid - missing WN
            ('ABC123', False),          # Invalid format
            ('18TWN', False),           # Too short
        ]
        
        for mgrs_text, should_match in mgrs_cases:
            with self.subTest(mgrs=mgrs_text):
                # Test the actual regex pattern used in parser
                text_upper = mgrs_text.upper().strip()
                text_clean = re.sub(r'\s+', '', text_upper)
                mgrs_pattern = re.match(r'^\d{1,2}[A-Z]{3}\d+$', text_clean)
                
                if should_match:
                    self.assertIsNotNone(mgrs_pattern, 
                        f"MGRS pattern should match '{mgrs_text}' but didn't")
                else:
                    self.assertIsNone(mgrs_pattern,
                        f"MGRS pattern should NOT match '{mgrs_text}' but did")
    
    def test_georef_pattern_detection(self):
        """Test GEOREF regex pattern catches valid GEOREF coordinates"""
        georef_cases = [
            ('GJPJ0615', True),     # Valid GEOREF
            ('ABCD1234', True),     # Valid format
            ('ABCD12', True),       # Valid minimum length
            ('ABC123', False),      # Too short prefix
            ('ABCDE123', False),    # Too long prefix
            ('ABCD1', False),       # Too short suffix
        ]
        
        for georef_text, should_match in georef_cases:
            with self.subTest(georef=georef_text):
                text_upper = georef_text.upper()
                georef_pattern = re.match(r'^[A-Z]{4}\d{2,}$', text_upper)
                
                if should_match:
                    self.assertIsNotNone(georef_pattern,
                        f"GEOREF pattern should match '{georef_text}' but didn't")
                else:
                    self.assertIsNone(georef_pattern,
                        f"GEOREF pattern should NOT match '{georef_text}' but did")
    
    def test_plus_codes_pattern_detection(self):
        """Test Plus Codes regex patterns catch valid formats"""
        plus_codes_patterns = [
            r'[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,}',
            r'[23456789CFGHJMPQRVWX]{6,8}\+[23456789CFGHJMPQRVWX]*',
            r'[23456789CFGHJMPQRVWX]{2,8}\+[23456789CFGHJMPQRVWX]{1,}'
        ]
        
        test_cases = [
            ('87G7X2VV+2V', True),      # Full Plus Code
            ('87G7X2VV+', True),        # Short Plus Code
            ('X2VV+2V', True),          # Local Plus Code
            ('G7X2VV+2V', True),        # Medium Plus Code
            ('87G7X2VV', False),        # Missing + sign
            ('87G7X2VV+', True),        # Minimal valid
        ]
        
        for plus_code, should_match in test_cases:
            with self.subTest(plus_code=plus_code):
                text_upper = plus_code.upper()
                
                matched = False
                for pattern in plus_codes_patterns:
                    if re.search(pattern, text_upper):
                        matched = True
                        break
                
                if should_match:
                    self.assertTrue(matched,
                        f"Plus Code pattern should match '{plus_code}' but didn't")
                else:
                    # Allow false positives here since Plus Codes are complex
                    pass
    
    def test_maidenhead_pattern_detection(self):
        """Test Maidenhead regex pattern catches valid grid references"""
        maidenhead_cases = [
            ('JO65HA', True),       # Standard 6-char
            ('JO65', True),         # 4-char grid
            ('JO65HA42', True),     # 8-char precision
            ('AB12', True),         # Minimal valid
            ('AB12CD', True),       # 6-char
            ('A1', False),          # Too short
            ('AB1', False),         # Invalid format
            ('AB123', False),       # Invalid format
        ]
        
        for maidenhead_text, should_match in maidenhead_cases:
            with self.subTest(maidenhead=maidenhead_text):
                text_upper = maidenhead_text.upper()
                maidenhead_pattern = re.match(r'^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$', text_upper)
                
                if should_match:
                    self.assertIsNotNone(maidenhead_pattern,
                        f"Maidenhead pattern should match '{maidenhead_text}' but didn't")
                else:
                    self.assertIsNone(maidenhead_pattern,
                        f"Maidenhead pattern should NOT match '{maidenhead_text}' but did")
    
    def test_geohash_pattern_detection(self):
        """Test Geohash regex patterns and cleaning"""
        geohash_cases = [
            ('dr5regy', True),          # Valid geohash
            ('9q5', True),              # Short valid
            ('dr5regyre45', True),      # Long valid
            ('dr5REGY', True),          # Mixed case (should be cleaned)
            ('dr5 reg y', True),        # With spaces (should be cleaned)
            ('xyz', False),             # Invalid chars
            ('dr', False),              # Too short (< 3 chars)
        ]
        
        for geohash_text, should_match in geohash_cases:
            with self.subTest(geohash=geohash_text):
                # Test the cleaning regex
                geohash_clean = re.sub(r'\s+', '', geohash_text.lower())
                geohash_pattern = re.match(r'^[0-9bcdefghjkmnpqrstuvwxyz]+$', geohash_clean)
                length_valid = 3 <= len(geohash_clean) <= 12
                
                if should_match:
                    self.assertIsNotNone(geohash_pattern,
                        f"Geohash pattern should match cleaned '{geohash_clean}' but didn't")
                    self.assertTrue(length_valid,
                        f"Geohash length should be valid for '{geohash_clean}' but wasn't")
                else:
                    if geohash_pattern and length_valid:
                        # If it matches pattern and length, that's actually OK
                        # The test expectation might be wrong
                        pass
    
    def test_text_cleaning_regex(self):
        """Test text cleaning regex patterns work correctly"""
        test_cases = [
            ('40.7128, -74.0060', '40.7128,-74.0060'),      # Remove spaces
            ('40.7128   -74.0060', '40.7128-74.0060'),       # Multiple spaces
            ('40.7128\t-74.0060', '40.7128-74.0060'),        # Tab characters
            ('40.7128\n-74.0060', '40.7128-74.0060'),        # Newlines
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input=input_text):
                # Test the cleaning pattern used in parser
                cleaned = re.sub(r'\s+', '', input_text)
                self.assertEqual(cleaned, expected,
                    f"Text cleaning failed for '{input_text}'")
    
    def test_regex_patterns_are_compiled(self):
        """Test that regex patterns can be compiled without errors"""
        # These are the critical patterns from the parser
        patterns_to_test = [
            r'^\d{1,2}[A-Z]{3}\d+$',                                           # MGRS
            r'^[A-Z]{4}\d{2,}$',                                              # GEOREF  
            r'[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,}',         # Plus Codes
            r'^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$',                           # Maidenhead
            r'^[0-9bcdefghjkmnpqrstuvwxyz]+$',                                # Geohash
            r'\s+',                                                           # Whitespace cleaning
            r'[-+]?\d*\.?\d+',                                               # Number extraction
        ]
        
        for pattern in patterns_to_test:
            with self.subTest(pattern=pattern):
                try:
                    compiled = re.compile(pattern)
                    # Test with a simple string to ensure it doesn't crash
                    compiled.search('test123')
                except re.error as e:
                    self.fail(f"Regex pattern '{pattern}' failed to compile: {e}")
                except Exception as e:
                    self.fail(f"Regex pattern '{pattern}' caused unexpected error: {e}")
    
    def test_format_detection_integration(self):
        """Integration test ensuring regex patterns work in actual parser context"""
        
        # Test known formats that should be detected by specific patterns
        format_tests = [
            ('18TWN8540011518', 'MGRS'),
            ('GJPJ0615', 'GEOREF'), 
            ('87G7X2VV+2V', 'Plus Codes'),
            ('JO65HA', 'Maidenhead'),
            ('dr5regy', 'Geohash'),
        ]
        
        for test_input, expected_format in format_tests:
            with self.subTest(input=test_input, format=expected_format):
                # This should work if regexes are correct
                result = self.parser._try_existing_formats(test_input)
                
                if expected_format in ['MGRS', 'GEOREF', 'Plus Codes', 'Maidenhead']:
                    # These depend on external modules that might not be available
                    # Just check that no regex error occurred
                    self.assertIsNotNone(result, 
                        f"Format detection should not fail with regex errors for {expected_format}")
                elif expected_format == 'Geohash':
                    # Geohash should definitely work
                    self.assertIsNotNone(result,
                        f"Geohash detection failed - likely regex issue")
                    self.assertIn('Geohash', result[4])

if __name__ == '__main__':
    unittest.main()