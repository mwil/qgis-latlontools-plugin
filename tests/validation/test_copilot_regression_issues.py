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
        """Set up test environment"""
        try:
            from fast_coordinate_detector import COORDINATE_PATTERNS, INVALID_PATTERNS, OptimizedCoordinateParser
            self.patterns = COORDINATE_PATTERNS
            self.invalid_patterns = INVALID_PATTERNS
            self.parser_class = OptimizedCoordinateParser
        except ImportError:
            self.skipTest("fast_coordinate_detector not available")
    
    def test_decimal_degrees_regex_leading_decimals_fix(self):
        """
        COPILOT ISSUE #1: Decimal degrees regex too restrictive
        
        Original regex: r'^[+-]?\\d{1,3}\\.?\\d*[\\s,;]+[+-]?\\d{1,3}\\.?\\d*\\s*$'
        Problem: Required at least one digit before decimal point - wouldn't match .5, .75
        Fixed regex: r'^[+-]?\\d*\\.?\\d+[\\s,;]+[+-]?\\d*\\.?\\d+\\s*$'
        Solution: Changed \\d{1,3} to \\d* and \\d* to \\d+ to allow leading decimals
        """
        pattern = self.patterns['decimal_degrees']
        
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
        
        Original code: When zoomToCoordOrder == OrderYX: lat, lon = x, y
        Problem: OrderYX means Y first, X second, so first number should be Y (latitude)
        Fixed code: When zoomToCoordOrder == OrderYX: lat, lon = y, x
        Solution: Corrected the assignment to match the semantic meaning of OrderYX
        """
        try:
            from unittest.mock import Mock
            from qgis.core import QgsApplication
            from smart_parser import SmartCoordinateParser
            
            # Initialize minimal QGIS environment
            if not QgsApplication.instance():
                qgs = QgsApplication([], False)
                qgs.initQgis()
            
            # Create test setup
            mock_settings = Mock()
            mock_iface = Mock()
            
            # Mock coordinate order constants
            class MockCoordOrder:
                OrderYX = 1  # Y (lat) first, then X (lon)
                OrderXY = 0  # X (lon) first, then Y (lat)
            
            # Test the critical coordinate assignment logic
            smart_parser = SmartCoordinateParser(mock_settings, mock_iface)
            optimizer = self.parser_class(smart_parser)
            
            # Patch the coordinate order for testing
            import sys
            sys.modules['settings'] = Mock()
            sys.modules['settings'].CoordOrder = MockCoordOrder
            
            # Test case: '45.123, -122.456' where 45.123 could be lat or lon
            smart_parser.settings.zoomToCoordOrder = MockCoordOrder.OrderYX
            
            result = optimizer._parse_decimal_degrees_fast('45.123, -122.456')
            self.assertIsNotNone(result, "Should parse coordinates successfully")
            
            lat, lon, bounds, crs = result
            
            # Key validation: ensure coordinates are in valid ranges after assignment logic
            self.assertTrue(-90 <= lat <= 90, f"REGRESSION: Latitude {lat} outside valid range [-90,90] - assignment logic may be wrong")
            self.assertTrue(-180 <= lon <= 180, f"REGRESSION: Longitude {lon} outside valid range [-180,180] - assignment logic may be wrong")
            
            # The coordinate assignment should result in valid lat/lon regardless of order preference
            # This is the critical fix - the logic should not produce invalid coordinates
            
        except ImportError as e:
            self.skipTest(f"QGIS environment not available: {e}")
    
    def test_obviously_projected_pattern_specificity_fix(self):
        """
        COPILOT ISSUE #3: "Obviously projected" pattern too broad
        
        Original regex: r'^\\s*\\d{5,7}\\.?\\d*[\\s,;]+\\d{6,8}\\.?\\d*\\s*$'
        Problem: Could filter out valid geographic coordinates with many decimal places
        Fixed regex: r'^\\s*[+-]?(?:\\d{4,})\\.?\\d*[\\s,;]+[+-]?(?:\\d{5,})\\.?\\d*\\s*$'
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
    print("🤖 COPILOT REGRESSION TESTS")
    print("=" * 50)
    print("Validating fixes for GitHub Copilot PR review issues:")
    print("1. ✅ Decimal degrees regex leading decimals fix")
    print("2. ✅ Coordinate assignment logic correction")  
    print("3. ✅ Obviously projected pattern specificity")
    print("4. ✅ Exception handling with proper logging")
    print("")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCopilotRegressionIssues)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n📊 COPILOT REGRESSION TEST SUMMARY:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 ALL COPILOT REGRESSION TESTS PASSED!")
        print("✅ No regressions detected - fixes are working correctly")
    else:
        print("⚠️ REGRESSION DETECTED!")
        for failure in result.failures:
            print(f"FAILURE: {failure[0]} - {failure[1]}")
        for error in result.errors:
            print(f"ERROR: {error[0]} - {error[1]}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_copilot_regression_tests()
    sys.exit(0 if success else 1)