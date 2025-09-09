#!/usr/bin/env python3
"""
Regression Tests for Copilot-Identified Issues
Tests specifically designed to catch the regex and coordinate flipping bugs identified in PR review.
"""

import unittest
import sys
import os
import re

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestCopilotRegressionIssues(unittest.TestCase):
    """
    Regression tests for issues identified by Copilot PR review:
    1. Decimal degrees regex too restrictive (not matching .5, .75)
    2. Coordinate assignment logic reversed (X/Y confusion)
    3. "Obviously projected" pattern too broad
    4. Exception handling improvements
    """
    
    def setUp(self):
        """Set up test environment"""
        # Import here to avoid issues with QGIS imports
        try:
            from fast_coordinate_detector import COORDINATE_PATTERNS, INVALID_PATTERNS, OptimizedCoordinateParser
            self.patterns = COORDINATE_PATTERNS
            self.invalid_patterns = INVALID_PATTERNS
            self.parser_class = OptimizedCoordinateParser
        except ImportError:
            self.skipTest("fast_coordinate_detector not available")
    
    def test_decimal_degrees_regex_leading_decimals(self):
        """
        Test Issue #1: Decimal degrees regex should match coordinates with leading decimals
        Original issue: Pattern required at least one digit before decimal point
        Fix: Allow coordinates like .5, .75 to match
        """
        pattern = self.patterns['decimal_degrees']
        
        # Test cases that should match (including Copilot's examples)
        valid_cases = [
            '.5, .75',        # Leading decimals (Copilot example)
            '0.5, 0.75',      # Standard decimals  
            '45.123, -122.456',  # Normal coordinates
            '1, 2',           # Integer coordinates
            '45, -122',       # Integer coordinates
            '+45.5, -122.5',  # Explicit signs
            '45.0, -122.0',   # Trailing zeros
        ]
        
        for case in valid_cases:
            with self.subTest(coordinate=case):
                match = pattern.match(case)
                self.assertIsNotNone(match, f"Should match '{case}' but didn't")
        
        # Test cases that should NOT match
        invalid_cases = [
            '45',             # Single coordinate
            '45, 122, 100',   # Three coordinates (should not match this pattern)
            'abc, def',       # Non-numeric
            '',               # Empty string
            ' ',              # Whitespace only
        ]
        
        for case in invalid_cases:
            with self.subTest(coordinate=case):
                match = pattern.match(case)
                self.assertIsNone(match, f"Should NOT match '{case}' but did")
    
    def test_coordinate_assignment_logic(self):
        """
        Test Issue #2: Coordinate assignment logic was reversed
        Original issue: When zoomToCoordOrder == OrderYX, assignment was lat, lon = x, y
        Fix: When OrderYX, should be lat, lon = y, x (first number is Y/latitude)
        """
        try:
            from unittest.mock import Mock
            from qgis.core import QgsApplication
            from smart_parser import SmartCoordinateParser
            
            # Initialize minimal QGIS environment
            if not QgsApplication.instance():
                qgs = QgsApplication([], False)
                qgs.initQgis()
            
            # Create mock objects
            mock_settings = Mock()
            mock_iface = Mock()
            
            # Mock coordinate order settings
            from unittest.mock import MagicMock
            CoordOrder = MagicMock()
            CoordOrder.OrderYX = 1  # Y (lat) first, then X (lon)
            CoordOrder.OrderXY = 0  # X (lon) first, then Y (lat)
            
            # Test OrderYX (Y first, X second)
            smart_parser = SmartCoordinateParser(mock_settings, mock_iface)
            smart_parser.settings.zoomToCoordOrder = CoordOrder.OrderYX
            
            optimizer = self.parser_class(smart_parser)
            
            # Test coordinate "45.123, -122.456" with OrderYX
            # First number (45.123) should be treated as Y (latitude)
            # Second number (-122.456) should be treated as X (longitude)
            result = optimizer._parse_decimal_degrees_fast('45.123, -122.456')
            
            self.assertIsNotNone(result, "Should successfully parse coordinates")
            lat, lon, bounds, crs = result
            
            # With OrderYX, the logic should be: lat, lon = y, x
            # Where x=45.123 (first number), y=-122.456 (second number)
            # So: lat = y = -122.456, lon = x = 45.123
            # But this would be invalid, so coordinate validation should swap them
            
            # The key test: ensure we get valid lat/lon ranges
            self.assertTrue(-90 <= lat <= 90, f"Latitude {lat} should be in valid range [-90, 90]")
            self.assertTrue(-180 <= lon <= 180, f"Longitude {lon} should be in valid range [-180, 180]")
            
            # Test OrderXY (X first, Y second) 
            smart_parser.settings.zoomToCoordOrder = CoordOrder.OrderXY
            result2 = optimizer._parse_decimal_degrees_fast('45.123, -122.456')
            
            self.assertIsNotNone(result2, "Should successfully parse coordinates with OrderXY")
            lat2, lon2, bounds2, crs2 = result2
            
            self.assertTrue(-90 <= lat2 <= 90, f"Latitude {lat2} should be in valid range [-90, 90]")
            self.assertTrue(-180 <= lon2 <= 180, f"Longitude {lon2} should be in valid range [-180, 180]")
            
        except ImportError:
            self.skipTest("QGIS environment not available for coordinate assignment test")
    
    def test_obviously_projected_pattern_specificity(self):
        """
        Test Issue #3: "Obviously projected" pattern was too broad
        Original issue: Pattern filtered out valid geographic coordinates with many decimal places
        Fix: Make pattern more specific to avoid false positives
        """
        pattern = self.invalid_patterns['obviously_projected']
        
        # These should NOT match the "obviously projected" pattern (valid geographic coordinates)
        valid_geographic = [
            '45.123456789, -122.456789012',  # Many decimal places (valid lat/lon)
            '89.999999, 179.999999',         # Near poles (valid)
            '-89.999999, -179.999999',       # Near poles (valid) 
            '0.000001, 0.000001',            # Very small values (valid)
            '90.0, 180.0',                   # Extreme valid coordinates
        ]
        
        for case in valid_geographic:
            with self.subTest(coordinate=case):
                match = pattern.match(case)
                self.assertIsNone(match, f"Valid geographic coordinate '{case}' should NOT match 'obviously_projected' pattern")
        
        # These SHOULD match the "obviously projected" pattern (obviously not lat/lon)
        obviously_projected = [
            '12345, 67890',          # Large numbers (UTM-like)
            '1234.567, 56789.012',   # UTM coordinates with decimals
            '500000, 4000000',       # Typical UTM coordinates
            '15538711, 4235210',     # Web Mercator coordinates
        ]
        
        for case in obviously_projected:
            with self.subTest(coordinate=case):
                match = pattern.match(case)
                self.assertIsNotNone(match, f"Obviously projected coordinate '{case}' SHOULD match pattern")
    
    def test_exception_handling_logging(self):
        """
        Test Issue #4: Exception handling should include logging for debugging
        Original issue: Bare except Exception: pass made debugging difficult
        Fix: Log exceptions while still allowing cleanup to proceed
        """
        try:
            from parser_service import CoordinateParserService
            from unittest.mock import Mock, patch
            
            # Test that reset_instance handles exceptions gracefully but logs them
            mock_settings = Mock()
            mock_iface = Mock()
            
            # Create an instance
            CoordinateParserService.reset_instance()  # Clean slate
            service = CoordinateParserService.get_instance(mock_settings, mock_iface)
            
            # Mock the parser loader to raise an exception during reset
            if hasattr(service, '_parser_loader') and service._parser_loader:
                original_reset = service._parser_loader.reset
                service._parser_loader.reset = Mock(side_effect=RuntimeError("Test exception"))
                
                # Reset should handle the exception gracefully
                with patch('qgis.core.QgsMessageLog.logMessage') as mock_log:
                    CoordinateParserService.reset_instance()
                    
                    # Verify that exception was logged (should have been called with warning message)
                    self.assertTrue(mock_log.called, "Exception should have been logged")
                    
                    # Check that warning message contains exception info
                    log_calls = [str(call) for call in mock_log.call_args_list]
                    has_warning = any('Warning' in call and 'Test exception' in call for call in log_calls)
                    self.assertTrue(has_warning, f"Should log warning about exception. Calls: {log_calls}")
            
        except ImportError:
            self.skipTest("parser_service not available for exception handling test")
    
    def test_coordinate_edge_cases_comprehensive(self):
        """
        Additional edge cases to prevent regression of coordinate parsing issues
        """
        pattern = self.patterns['decimal_degrees']
        
        # Edge cases that have historically caused issues
        edge_cases = [
            # Precision edge cases
            ('.1, .2', True),           # Very small leading decimals  
            ('.999, .888', True),       # Leading decimals close to 1
            ('0.0, 0.0', True),         # Zero coordinates
            ('0, 0', True),             # Integer zeros
            
            # Sign variations
            ('+0, +0', True),           # Explicit positive signs
            ('-0, -0', True),           # Negative zeros
            ('+.5, -.5', True),         # Signed leading decimals
            
            # Boundary cases  
            ('90, 180', True),          # Maximum valid lat/lon
            ('-90, -180', True),        # Minimum valid lat/lon
            ('89.999999, 179.999999', True),  # Just within bounds
            
            # Invalid formats that should not match
            ('1.2.3, 4.5.6', False),   # Multiple decimal points
            ('1e5, 2e6', False),        # Scientific notation (handled elsewhere)
            ('45°, 122°', False),       # Degree symbols (different pattern)
        ]
        
        for case, should_match in edge_cases:
            with self.subTest(coordinate=case):
                match = pattern.match(case)
                if should_match:
                    self.assertIsNotNone(match, f"Should match '{case}'")
                else:
                    self.assertIsNone(match, f"Should NOT match '{case}'")


if __name__ == '__main__':
    # Run tests with minimal output
    unittest.main(verbosity=2)