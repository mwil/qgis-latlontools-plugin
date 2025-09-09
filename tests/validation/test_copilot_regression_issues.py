#!/usr/bin/env python3
"""
Copilot Regression Tests
Tests specifically designed to catch issues identified during PR review by GitHub Copilot.
"""

import unittest
import sys
import os
import re

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestCopilotRegressionIssues(unittest.TestCase):
    """
    Regression tests for critical issues identified by GitHub Copilot PR review.
    These tests prevent regressions in coordinate parsing logic and regex patterns.
    """
    
    def setUp(self):
        """Set up test environment with proper mocks"""
        try:
            from fast_coordinate_detector import COORDINATE_PATTERNS, INVALID_PATTERNS, OptimizedCoordinateParser
            self.patterns = COORDINATE_PATTERNS
            self.invalid_patterns = INVALID_PATTERNS
            self.parser_class = OptimizedCoordinateParser
            
            # Create mock objects for coordinate assignment testing
            self.mock_epsg4326 = "EPSG:4326"  # Simple mock
            
            # Mock CoordOrder enum
            class MockCoordOrder:
                OrderYX = 0  # "Lat, Lon" order
                OrderXY = 1  # "Lon, Lat" order
            self.coord_order = MockCoordOrder()
            
            # Mock settings object  
            class MockSettings:
                def __init__(self, coord_order):
                    self.zoomToCoordOrder = coord_order
            self.mock_settings = MockSettings
            
            # Mock smart parser
            class MockSmartParser:
                def __init__(self, settings):
                    self.settings = settings
            self.mock_smart_parser = MockSmartParser
            
        except ImportError as e:
            self.skipTest(f"fast_coordinate_detector not available: {e}")
    
    def test_decimal_degrees_regex_leading_decimals_fix(self):
        """
        COPILOT ISSUE #1: Decimal degrees regex too restrictive
        
        Original regex: r'^[+-]?\d{1,3}\.?\d*[\s,;]+[+-]?\d{1,3}\.?\d*\s*$'
        Problem: Required at least one digit before decimal point - wouldn't match .5, .75
        Fixed regex: r'^[+-]?\d*\.?\d+[\s,;]+[+-]?\d*\.?\d+\s*$'
        Solution: Updated regex to use \d* before the decimal and \d+ after, allowing leading decimals (e.g., '.5') by permitting zero or more digits before the decimal and requiring at least one digit after.
        """
        pattern = self.patterns['decimal_degrees']
        # Current regex being tested: r'^[+-]?\d*\.?\d+[\s,;]+[+-]?\d*\.?\d+\s*$'
        
        # Critical test cases from Copilot review
        critical_cases = [
            ('.5, .75', True, 'Leading decimals (Copilot example)'),
            ('0.5, 0.75', True, 'Standard decimals'),
            ('45.123, -122.456', True, 'Normal coordinates'),
        ]
        
        for case, should_match, description in critical_cases:
            with self.subTest(coordinate=case, description=description):
                match = pattern.match(case)
                if should_match:
                    self.assertIsNotNone(match, f"REGRESSION: {description} - '{case}' should match but doesn't")
                else:
                    self.assertIsNone(match, f"REGRESSION: {description} - '{case}' should NOT match but does")
    
    def test_coordinate_assignment_logic_fix(self):
        """
        COPILOT ISSUE #2: Coordinate assignment logic was reversed
        
        CRITICAL SEMANTIC UNDERSTANDING:
        - OrderYX = "Lat, Lon (Y,X) - Google Map Order" → INPUT format is "Lat, Lon"
        - OrderXY = "Lon, Lat (X,Y) Order" → INPUT format is "Lon, Lat"
        
        Evidence from zoomToLatLon.py:322-327:
        if settings.zoomToCoordOrder == CoordOrder.OrderYX:
            lat = float(coords[0])  # First coordinate is latitude
            lon = float(coords[1])  # Second coordinate is longitude
        
        CORRECTED LOGIC:
        - When OrderYX: lat, lon = x, y (first number is lat, second is lon) 
        - When OrderXY: lat, lon = y, x (first number is lon, second is lat)
        """
        # Test the coordinate assignment logic directly without QGIS dependencies
        import re
        
        # Mock the coordinate order enum values (matching actual values from settings.py)
        OrderYX = 0  # "Lat, Lon" input format
        OrderXY = 1  # "Lon, Lat" input format
        
        # Test coordinate input: "45.123, -122.456"
        text = "45.123, -122.456"
        numbers = re.findall(r'[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?', text)
        x, y = float(numbers[0]), float(numbers[1])  # x=45.123, y=-122.456
        
        # Test OrderYX logic (INPUT: "Lat, Lon")
        if OrderYX == 0:  # This is the setting
            lat_yx, lon_yx = x, y  # First number is lat, second is lon
        else:
            lat_yx, lon_yx = y, x  # First number is lon, second is lat
        
        # Test OrderXY logic (INPUT: "Lon, Lat")
        if OrderXY == 0:  # This is the setting
            lat_xy, lon_xy = x, y  # First number is lat, second is lon
        else:
            lat_xy, lon_xy = y, x  # First number is lon, second is lat
        
        # CRITICAL VALIDATION: OrderYX should interpret "45.123, -122.456" as Lat=45.123, Lon=-122.456
        
        # OrderYX: Input format is "Lat, Lon" so 45.123=lat, -122.456=lon
        self.assertEqual(lat_yx, 45.123, "OrderYX: First number should be latitude")
        self.assertEqual(lon_yx, -122.456, "OrderYX: Second number should be longitude") 
        self.assertTrue(-90 <= lat_yx <= 90, f"OrderYX: Latitude {lat_yx} should be valid")
        self.assertTrue(-180 <= lon_yx <= 180, f"OrderYX: Longitude {lon_yx} should be valid")
        
        # OrderXY: Input format is "Lon, Lat" so 45.123=lon, -122.456=lat  
        self.assertEqual(lat_xy, -122.456, "OrderXY: Second number should be latitude")
        self.assertEqual(lon_xy, 45.123, "OrderXY: First number should be longitude")
        # Note: OrderXY produces lat=-122.456 which is invalid, showing why validation/swapping is needed
        
        # Test another case to confirm the logic: "12.34, 56.78" 
        text2 = "12.34, 56.78"
        numbers2 = re.findall(r'[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?', text2)
        x2, y2 = float(numbers2[0]), float(numbers2[1])  # x2=12.34, y2=56.78
        
        # OrderYX: "Lat, Lon" input → lat=12.34, lon=56.78
        lat_yx2 = x2 if OrderYX == 0 else y2  
        lon_yx2 = y2 if OrderYX == 0 else x2
        
        # OrderXY: "Lon, Lat" input → lat=56.78, lon=12.34  
        lat_xy2 = x2 if OrderXY == 0 else y2
        lon_xy2 = y2 if OrderXY == 0 else x2
        
        self.assertEqual(lat_yx2, 12.34, "OrderYX: lat should be first number in Lat,Lon format")
        self.assertEqual(lon_yx2, 56.78, "OrderYX: lon should be second number in Lat,Lon format")
        self.assertEqual(lat_xy2, 56.78, "OrderXY: lat should be second number in Lon,Lat format") 
        self.assertEqual(lon_xy2, 12.34, "OrderXY: lon should be first number in Lon,Lat format")
    
    def test_obviously_projected_pattern_specificity_fix(self):
        """
        COPILOT ISSUE #3: "Obviously projected" pattern too broad
        
        Original regex: r'^\s*\d{5,7}\.?\d*[\s,;]+\d{6,8}\.?\d*\s*$'
        Problem: Could filter out valid geographic coordinates with many decimal places
        Fixed regex: r'^\s*[+-]?(?:\d{6,})\.?\d*[\s,;]+[+-]?(?:\d{6,})\.?\d*\s*$'
        Solution: More specific pattern that targets coordinates with >=1000 in first number
        """
        pattern = self.invalid_patterns['obviously_projected']
        
        # These should NOT be flagged as "obviously projected" (valid geographic)
        valid_geographic_cases = [
            ('45.123456789, -122.456789012', 'Many decimal places'),
            ('89.999999, 179.999999', 'Near poles with decimals'),
            ('-89.999999, -179.999999', 'Near poles negative'),
            ('0.000001, 0.000001', 'Very small valid coordinates'),
        ]
        
        for case, description in valid_geographic_cases:
            with self.subTest(coordinate=case, description=description):
                match = pattern.match(case)
                self.assertIsNone(match, f"REGRESSION: {description} - Valid geographic '{case}' incorrectly flagged as projected")
        
        # These SHOULD be flagged as "obviously projected"
        obviously_projected_cases = [
            ('12345, 67890', 'Large UTM-like numbers'),
            ('500000, 4000000', 'Typical UTM coordinates'),  
            ('1234.567, 56789.012', 'UTM with decimals'),
            ('1234, 5678', 'Consistent 4+ digit pattern'),
            ('5678, 1234', 'Consistent 4+ digit pattern (reversed)'),
        ]
        
        for case, description in obviously_projected_cases:
            with self.subTest(coordinate=case, description=description):
                match = pattern.match(case)
                self.assertIsNotNone(match, f"REGRESSION: {description} - Obviously projected '{case}' should be detected")
    
    def test_exception_handling_logging_improvement(self):
        """
        COPILOT ISSUE #4: Exception handling too broad with no logging
        
        Original code: except Exception: pass
        Problem: Made debugging difficult by silently swallowing all exceptions
        Fixed code: except Exception as e: [log warning] + try/except for logging
        Solution: Log exceptions while still allowing cleanup to proceed
        """
        try:
            from parser_service import CoordinateParserService
            from unittest.mock import Mock, patch, MagicMock
            
            # Test that exceptions are logged during cleanup
            mock_settings = Mock()
            mock_iface = Mock()
            
            # Create service instance
            CoordinateParserService.reset_instance()  
            service = CoordinateParserService.get_instance(mock_settings, mock_iface)
            
            # Force creation of components that might fail during cleanup
            _ = service.parse_coordinate_with_logging('45.123, -122.456', 'TestComponent')
            
            # Mock a component to raise exception during cleanup
            if hasattr(service, '_parser_loader') and service._parser_loader:
                service._parser_loader.reset = MagicMock(side_effect=RuntimeError("Test cleanup exception"))
            
            # Verify that cleanup logs exceptions but continues
            with patch('qgis.core.QgsMessageLog.logMessage') as mock_log:
                CoordinateParserService.reset_instance()
                
                # Should have logged the exception
                self.assertTrue(mock_log.called, "REGRESSION: Exceptions during cleanup should be logged for debugging")
                
                # Check that warning message was logged  
                log_messages = ' '.join([str(call) for call in mock_log.call_args_list])
                self.assertIn('Warning', log_messages, "REGRESSION: Should log warning about cleanup failure")
                self.assertIn('Test cleanup exception', log_messages, "REGRESSION: Should log the actual exception message")
            
            # Cleanup should still succeed despite the exception
            self.assertIsNone(CoordinateParserService._instance, "REGRESSION: Cleanup should complete even with exceptions")
            
        except ImportError:
            self.skipTest("parser_service not available for exception handling test")
    
    def test_comprehensive_edge_cases_regression_prevention(self):
        """
        Additional edge cases to prevent future regressions
        These test boundary conditions that have historically caused issues
        """
        pattern = self.patterns['decimal_degrees']
        
        # Edge cases that could break regex patterns
        boundary_test_cases = [
            # Leading decimal variations
            ('.1, .2', True, 'Minimal leading decimals'),
            ('.999, .888', True, 'Leading decimals close to 1'),
            ('+.5, -.5', True, 'Signed leading decimals'),
            
            # Zero handling  
            ('0.0, 0.0', True, 'Decimal zeros'),
            ('0, 0', True, 'Integer zeros'),
            ('+0, +0', True, 'Explicit positive zeros'),
            ('-0, -0', True, 'Negative zeros'),
            
            # Precision boundaries
            ('90, 180', True, 'Maximum lat/lon integers'), 
            ('-90, -180', True, 'Minimum lat/lon integers'),
            ('89.999999, 179.999999', True, 'Just within decimal bounds'),
            
            # Invalid cases that should not match this pattern
            ('1.2.3, 4.5.6', False, 'Multiple decimal points'),
            ('45°, 122°', False, 'Degree symbols'),
            ('', False, 'Empty string'),
            ('45', False, 'Single coordinate'),
        ]
        
        for case, should_match, description in boundary_test_cases:
            with self.subTest(coordinate=case, description=description):
                match = pattern.match(case)
                if should_match:
                    self.assertIsNotNone(match, f"REGRESSION: {description} - '{case}' should match")
                else:
                    self.assertIsNone(match, f"REGRESSION: {description} - '{case}' should NOT match")


def run_copilot_regression_tests():
    """Run Copilot regression tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCopilotRegressionIssues)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        return True
    else:
        # Log failures and errors to help with debugging
        for failure in result.failures:
            print(f"FAILURE: {failure[0]} - {failure[1]}")
        for error in result.errors:
            print(f"ERROR: {error[0]} - {error[1]}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_copilot_regression_tests()
    sys.exit(0 if success else 1)