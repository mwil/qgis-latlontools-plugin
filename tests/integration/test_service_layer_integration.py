#!/usr/bin/env python3
"""
Service Layer Integration Tests

Tests the parser service layer implementation introduced in Phase 2 refactoring.
Validates that the service layer properly centralizes coordinate parsing while
maintaining all existing functionality through fallback mechanisms.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestServiceLayerIntegration(unittest.TestCase):
    """Integration tests for the parser service layer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock QGIS components to avoid dependency
        self.mock_settings = Mock()
        self.mock_iface = Mock()
        
    def test_parser_service_import(self):
        """Test that parser service imports correctly"""
        try:
            from parser_service import CoordinateParserService, CoordinateParserMixin, parse_coordinate_with_service
            self.assertTrue(True, "Parser service imports successfully")
        except ImportError as e:
            self.fail(f"Parser service import failed: {e}")
    
    def test_singleton_pattern(self):
        """Test that CoordinateParserService implements singleton pattern correctly"""
        from parser_service import CoordinateParserService
        
        # Reset singleton for clean test
        CoordinateParserService.reset_instance()
        
        # First call should create instance
        service1 = CoordinateParserService.get_instance(self.mock_settings, self.mock_iface)
        self.assertIsNotNone(service1)
        
        # Second call should return same instance
        service2 = CoordinateParserService.get_instance()
        self.assertIs(service1, service2, "Singleton pattern should return same instance")
        
        # Reset for cleanup
        CoordinateParserService.reset_instance()
    
    def test_service_layer_coordination(self):
        """Test that service layer properly coordinates with smart parser"""
        from parser_service import parse_coordinate_with_service
        
        # Test coordinate that should be parsed by smart parser
        test_coordinate = "POINT(1.5 2.5)"
        
        with patch('smart_parser.SmartCoordinateParser') as mock_smart_parser:
            # Mock smart parser to return expected result
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = (2.5, 1.5, None, Mock())
            mock_smart_parser.return_value = mock_parser_instance
            
            result = parse_coordinate_with_service(
                test_coordinate, "TestComponent", self.mock_settings, self.mock_iface
            )
            
            # Verify service layer called smart parser
            mock_smart_parser.assert_called_once_with(self.mock_settings, self.mock_iface)
            mock_parser_instance.parse.assert_called_once_with(test_coordinate)
            
            # Verify result
            self.assertIsNotNone(result)
            lat, lon, bounds, source_crs = result
            self.assertEqual(lat, 2.5)
            self.assertEqual(lon, 1.5)
    
    def test_fallback_mechanism(self):
        """Test that fallback mechanism works when smart parser fails"""
        from parser_service import parse_coordinate_with_service
        
        test_coordinate = "45.123, -122.456"
        expected_fallback_result = (45.123, -122.456, None, Mock())
        
        def mock_fallback(text):
            return expected_fallback_result
        
        with patch('smart_parser.SmartCoordinateParser') as mock_smart_parser:
            # Mock smart parser to return None (failure)
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = None
            mock_smart_parser.return_value = mock_parser_instance
            
            result = parse_coordinate_with_service(
                test_coordinate, "TestComponent", self.mock_settings, self.mock_iface, mock_fallback
            )
            
            # Verify fallback was used
            self.assertIsNotNone(result)
            self.assertEqual(result, expected_fallback_result)
    
    def test_logging_integration(self):
        """Test that service layer provides consistent logging"""
        from parser_service import parse_coordinate_with_service
        
        test_coordinate = "POINT(0 0)"
        
        with patch('parser_service.SmartCoordinateParser') as mock_smart_parser, \
             patch('parser_service.QgsMessageLog') as mock_log:
            
            # Mock smart parser success
            mock_parser_instance = Mock()
            mock_parser_instance.parse.return_value = (0, 0, None, Mock())
            mock_smart_parser.return_value = mock_parser_instance
            
            parse_coordinate_with_service(
                test_coordinate, "TestComponent", self.mock_settings, self.mock_iface
            )
            
            # Verify logging was called
            self.assertTrue(mock_log.logMessage.called)
            
            # Check that component name is in log messages
            log_calls = mock_log.logMessage.call_args_list
            component_mentioned = any('TestComponent' in str(call) for call in log_calls)
            self.assertTrue(component_mentioned, "Component name should be mentioned in logs")
    
    def test_error_handling(self):
        """Test that service layer handles errors gracefully"""
        from parser_service import parse_coordinate_with_service
        
        test_coordinate = "invalid coordinate"
        
        with patch('smart_parser.SmartCoordinateParser') as mock_smart_parser:
            # Mock smart parser to raise exception
            mock_parser_instance = Mock()
            mock_parser_instance.parse.side_effect = Exception("Parsing failed")
            mock_smart_parser.return_value = mock_parser_instance
            
            result = parse_coordinate_with_service(
                test_coordinate, "TestComponent", self.mock_settings, self.mock_iface
            )
            
            # Should return None on error
            self.assertIsNone(result)

class TestUIComponentIntegration(unittest.TestCase):
    """Test that UI components properly use the service layer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_settings = Mock()
        self.mock_iface = Mock()
    
    def test_coordinate_converter_integration(self):
        """Test that coordinateConverter uses service layer"""
        # Read the coordinate converter file
        try:
            with open('coordinateConverter.py', 'r') as f:
                content = f.read()
            
            # Check for service layer usage
            self.assertIn('parse_coordinate_with_service', content, 
                         "coordinateConverter should use parse_coordinate_with_service")
            self.assertIn('from .parser_service import', content,
                         "coordinateConverter should import parser service")
            
        except FileNotFoundError:
            self.skipTest("coordinateConverter.py not found")
    
    def test_digitizer_integration(self):
        """Test that digitizer uses service layer"""
        try:
            with open('digitizer.py', 'r') as f:
                content = f.read()
            
            # Check for service layer usage
            self.assertIn('parse_coordinate_with_service', content, 
                         "digitizer should use parse_coordinate_with_service")
            self.assertIn('from .parser_service import', content,
                         "digitizer should import parser service")
            
        except FileNotFoundError:
            self.skipTest("digitizer.py not found")
    
    def test_zoomToLatLon_integration(self):
        """Test that zoomToLatLon uses service layer"""
        try:
            with open('zoomToLatLon.py', 'r') as f:
                content = f.read()
            
            # Check for service layer usage
            self.assertIn('parse_coordinate_with_service', content, 
                         "zoomToLatLon should use parse_coordinate_with_service")
            self.assertIn('from .parser_service import', content,
                         "zoomToLatLon should import parser service")
            
        except FileNotFoundError:
            self.skipTest("zoomToLatLon.py not found")
    
    def test_multizoom_integration(self):
        """Test that multizoom uses service layer"""
        try:
            with open('multizoom.py', 'r') as f:
                content = f.read()
            
            # Check for service layer usage
            self.assertIn('parse_coordinate_with_service', content, 
                         "multizoom should use parse_coordinate_with_service")
            self.assertIn('from .parser_service import', content,
                         "multizoom should import parser service")
            
        except FileNotFoundError:
            self.skipTest("multizoom.py not found")

class TestServiceLayerCompatibility(unittest.TestCase):
    """Test that service layer maintains compatibility with existing functionality"""
    
    def test_coordinates_still_parse(self):
        """Test that various coordinate formats still parse through service layer"""
        from parser_service import parse_coordinate_with_service
        
        mock_settings = Mock()
        mock_iface = Mock()
        
        # Test cases that should work
        test_cases = [
            ("45.123, -122.456", "Basic lat/lon"),
            ("POINT(1.5 2.5)", "WKT POINT"),
            ("45° 30' N, 122° 30' W", "DMS format"),
        ]
        
        with patch('smart_parser.SmartCoordinateParser') as mock_smart_parser:
            for test_input, description in test_cases:
                with self.subTest(coordinate=test_input):
                    # Mock successful parsing
                    mock_parser_instance = Mock()
                    mock_parser_instance.parse.return_value = (45.0, -122.0, None, Mock())
                    mock_smart_parser.return_value = mock_parser_instance
                    
                    result = parse_coordinate_with_service(
                        test_input, "Test", mock_settings, mock_iface
                    )
                    
                    self.assertIsNotNone(result, f"Should parse {description}: {test_input}")

def run_service_layer_tests():
    """Run all service layer tests"""
    print("🔧 RUNNING SERVICE LAYER INTEGRATION TESTS")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestServiceLayerIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestUIComponentIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestServiceLayerCompatibility))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\n📊 SERVICE LAYER TEST SUMMARY:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("🎉 ALL SERVICE LAYER TESTS PASSED!")
    else:
        print("⚠️ SOME SERVICE LAYER TESTS FAILED!")
        
        if result.failures:
            print("\nFAILURES:")
            for test, traceback in result.failures:
                print(f"- {test}")
        
        if result.errors:
            print("\nERRORS:")
            for test, traceback in result.errors:
                print(f"- {test}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_service_layer_tests()
    sys.exit(0 if success else 1)