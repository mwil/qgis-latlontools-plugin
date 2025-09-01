# Comprehensive Testing Guide for Lat Lon Tools Plugin

## Overview

This guide covers all aspects of testing the Lat Lon Tools QGIS plugin, including automated tests, manual testing procedures, and guidelines for writing new tests.

## Test Structure

### Current Test Coverage

The plugin has comprehensive test coverage across multiple categories:

#### 1. Validation Tests (`/tests/validation/`)
- **test_z_coordinate_handling.py** - Tests Z coordinate and elevation handling
- **test_regex_pattern_validation.py** - Validates regex patterns for coordinate format detection
- **test_comprehensive_edge_cases.py** - Edge cases and boundary conditions
- **test_coordinate_flipping_comprehensive.py** - Coordinate order detection and handling
- **test_smart_parser_validation.py** - Main parser validation tests
- **test_real_world_coordinate_scenarios.py** - Real-world coordinate examples

#### 2. Unit Tests (`/tests/unit/`)
- **test_pattern_detection.py** - Isolated pattern detection tests
- **test_smart_parser_simple.py** - Basic parser functionality tests

#### 3. Standalone Tests (Root directory)
- **test_z_coordinate_handling.py** - Standalone Z coordinate tests (current directory)
- **test_regex_pattern_validation.py** - Standalone regex validation tests (current directory)
- **test_wkb_standalone.py** - WKB parsing tests
- **test_wkb_only.py** - Focused WKB tests

#### 4. Test Runners
- **run_basic_tests.py** - Basic test execution
- Various specialized test runners for different scenarios

## Running Tests

### Option 1: With QGIS Environment (Recommended)

Tests require QGIS Python environment for full functionality:

```bash
# Run from plugin directory
cd "/Users/mwil/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/latlontools"

# Run individual test files
/Applications/QGIS.app/Contents/MacOS/bin/python3 test_regex_pattern_validation.py
/Applications/QGIS.app/Contents/MacOS/bin/python3 test_z_coordinate_handling.py

# Run specific test methods
/Applications/QGIS.app/Contents/MacOS/bin/python3 -m unittest test_regex_pattern_validation.TestRegexPatternValidation.test_mgrs_pattern_detection
```

**Note**: Some tests may show PROJ database warnings - these are harmless and don't affect test results.

### Option 2: Without QGIS (Limited)

Some basic tests can run without full QGIS environment:

```bash
# Standard Python 3 - limited functionality
python3 test_regex_pattern_validation.py

# Note: Tests requiring QGIS APIs will be skipped or fail
```

### Option 3: Using Test Runners

```bash
# Use available test runners for batch execution
/Applications/QGIS.app/Contents/MacOS/bin/python3 run_basic_tests.py
```

## Test Categories Explained

### 1. Regex Pattern Validation Tests

**Purpose**: Catch regex syntax bugs and pattern matching issues
**File**: `test_regex_pattern_validation.py`
**Key Features**:
- Tests regex pattern compilation
- Validates pattern matching for all coordinate formats
- Integration tests with actual parser
- Catches double backslash bugs in regex patterns

**Example Test**:
```python
def test_mgrs_pattern_detection(self):
    mgrs_pattern = re.match(r'^\d{1,2}[A-Z]{3}\d+$', text_clean)
    self.assertIsNotNone(mgrs_pattern, "MGRS pattern should match")
```

### 2. Z Coordinate Handling Tests

**Purpose**: Ensure proper handling of 3D coordinates and elevation values
**File**: `test_z_coordinate_handling.py`
**Key Features**:
- WKB with SRID and Z coordinates
- UTM coordinates with elevation rejection
- DMS coordinates with elevation suffixes
- Projected coordinate detection
- Validation of coordinate bounds

**Example Test**:
```python
def test_wkb_with_srid_and_z_coordinate(self):
    wkb_3d = "01010000A0281A00005396BF88FF9560405296C6D462D64040A857CA32C41D7240"
    result = self.parser.parse(wkb_3d)
    self.assertIsNotNone(result, "WKB with SRID and Z should parse successfully")
```

### 3. Comprehensive Edge Cases

**Purpose**: Test boundary conditions and unusual input scenarios
**Focus Areas**:
- Invalid coordinate ranges
- Malformed input strings
- Edge cases in coordinate conversions
- Error handling validation

### 4. Real-World Scenarios

**Purpose**: Test with actual coordinates from various global locations
**Focus Areas**:
- Coordinates from different geographic regions
- Various precision levels
- Mixed coordinate format handling
- Real-world data validation

## Writing New Tests

### Test File Structure

```python
#!/usr/bin/env python3
"""
Test description and purpose
"""

import sys
import os
import unittest
from unittest.mock import Mock

# QGIS environment setup
sys.path.insert(0, '/Applications/QGIS.app/Contents/Resources/python')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qgis.core import QgsApplication
from smart_parser import SmartCoordinateParser
from settings import CoordOrder

def init_qgis():
    """Initialize QGIS application for testing"""
    QgsApplication.setPrefixPath('/Applications/QGIS.app/Contents', True)
    app = QgsApplication([], False)
    QgsApplication.initQgis()
    return app

class TestYourFeature(unittest.TestCase):
    """Test description"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QGIS once for all tests"""
        cls.app = init_qgis()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up QGIS"""
        QgsApplication.exitQgis()
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.zoomToCoordOrder = CoordOrder.OrderYX
        
        # Mock iface
        self.mock_iface = Mock()
        
        # Create parser
        self.parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)
    
    def test_your_functionality(self):
        """Test specific functionality"""
        # Your test code here
        result = self.parser.parse("test input")
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
```

### Test Categories to Consider

#### 1. Format Detection Tests
- Test regex patterns for new coordinate formats
- Validate pattern compilation
- Test edge cases and invalid inputs

#### 2. Coordinate Conversion Tests  
- Test conversion accuracy
- Test error handling for invalid inputs
- Test coordinate system transformations

#### 3. Parser Integration Tests
- Test end-to-end parsing workflow
- Test format precedence and fallback behavior
- Test error propagation

#### 4. Import Compatibility Tests
- Test both plugin and standalone import paths
- Test missing dependency handling
- Test graceful degradation

### Best Practices for New Tests

1. **Use descriptive test names** - `test_utm_with_elevation_rejection` vs `test_utm_1`
2. **Use subTests for multiple cases** - Test multiple similar inputs in one test
3. **Mock external dependencies** - Use Mock objects for QGIS interfaces
4. **Test both success and failure cases** - Verify proper error handling
5. **Include documentation** - Explain what the test validates and why
6. **Follow import patterns** - Use try/except for both plugin and standalone contexts

### Common Test Patterns

#### Testing Coordinate Parsing
```python
def test_coordinate_format(self):
    test_cases = [
        ('valid_input', True, (expected_lat, expected_lon)),
        ('invalid_input', False, None),
    ]
    
    for input_text, should_succeed, expected in test_cases:
        with self.subTest(input=input_text):
            result = self.parser.parse(input_text)
            
            if should_succeed:
                self.assertIsNotNone(result)
                lat, lon, bounds, crs = result
                exp_lat, exp_lon = expected
                self.assertAlmostEqual(lat, exp_lat, places=3)
                self.assertAlmostEqual(lon, exp_lon, places=3)
            else:
                self.assertIsNone(result)
```

#### Testing Regex Patterns
```python
def test_regex_pattern(self):
    pattern = r'^your_pattern_here$'
    test_cases = [
        ('valid_match', True),
        ('invalid_input', False),
    ]
    
    for test_input, should_match in test_cases:
        with self.subTest(input=test_input):
            match = re.match(pattern, test_input)
            if should_match:
                self.assertIsNotNone(match)
            else:
                self.assertIsNone(match)
```

## Manual Testing Requirements

### QGIS Plugin Testing

Since this is a QGIS plugin, manual testing is required for:

1. **GUI Components**
   - Coordinate converter dialog
   - Settings dialog
   - Multi-zoom dialog
   - Digitizer dialog

2. **Map Tools**
   - Zoom to coordinates tool
   - Copy coordinates tool
   - Digitizing tools

3. **Processing Algorithms**
   - All algorithms in QGIS Processing toolbox
   - Parameter validation
   - Output layer generation

### Manual Testing Workflow

1. **Deploy Plugin**:
   ```bash
   make deploy  # Deploys to QGIS plugins directory
   ```

2. **Use Plugin Reloader** (recommended for development):
   - Install Plugin Reloader from QGIS Plugin Repository
   - Use to reload plugin changes without restarting QGIS

3. **Test Core Functionality**:
   - Open coordinate converter dialog
   - Test various coordinate format inputs
   - Verify coordinate conversions
   - Test map tools and zoom functionality

## Test Execution Environment

### QGIS Python Path Setup

Tests require proper QGIS Python environment:

```python
# Required for all tests
sys.path.insert(0, '/Applications/QGIS.app/Contents/Resources/python')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize QGIS
from qgis.core import QgsApplication
QgsApplication.setPrefixPath('/Applications/QGIS.app/Contents', True)
app = QgsApplication([], False)
QgsApplication.initQgis()
```

### Import Compatibility

Tests handle both plugin and standalone contexts:

```python
# Import pattern for plugin compatibility
try:
    from .smart_parser import SmartCoordinateParser  # Plugin context
except ImportError:
    from smart_parser import SmartCoordinateParser   # Standalone context
```

## Troubleshooting Tests

### Common Issues

1. **PROJ Database Warnings**:
   ```
   ERROR 1: PROJ: proj_create_from_database: Cannot find proj.db
   ```
   - **Solution**: These are warnings, not errors. Tests still run correctly.

2. **Import Errors**:
   ```
   ImportError: No module named 'qgis'
   ```
   - **Solution**: Use QGIS Python executable: `/Applications/QGIS.app/Contents/MacOS/bin/python3`

3. **Missing Dependencies**:
   ```
   ImportError: No module named 'mgrs'
   ```
   - **Solution**: Some tests gracefully handle missing optional dependencies

4. **Test Isolation Issues**:
   - **Solution**: Use separate test classes with proper setUp/tearDown methods

### Debugging Test Failures

1. **Run individual tests**:
   ```bash
   /Applications/QGIS.app/Contents/MacOS/bin/python3 -m unittest test_file.TestClass.test_method -v
   ```

2. **Add debug output**:
   ```python
   def test_debug_example(self):
       result = self.parser.parse("test input")
       print(f"Debug: result = {result}")  # Add debug output
       self.assertIsNotNone(result)
   ```

3. **Test regex patterns individually**:
   ```python
   import re
   pattern = r'your_pattern'
   test_input = "test string"
   match = re.match(pattern, test_input)
   print(f"Pattern: {pattern}")
   print(f"Input: {test_input}")
   print(f"Match: {match}")
   ```

## Test Quality Guidelines

### What Makes a Good Test

1. **Focused and Specific** - Test one thing at a time
2. **Predictable** - Same input always produces same result
3. **Fast** - Minimal setup and execution time
4. **Independent** - Tests don't depend on each other
5. **Readable** - Clear intent and good documentation

### Test Naming Conventions

- `test_[feature]_[scenario]` - e.g., `test_utm_with_elevation_rejection`
- `test_[format]_pattern_detection` - e.g., `test_mgrs_pattern_detection`
- `test_[error_condition]` - e.g., `test_invalid_coordinate_rejection`

### Assertion Guidelines

- Use specific assertions: `assertAlmostEqual` for coordinates, `assertIsNotNone` for objects
- Include helpful failure messages
- Test both positive and negative cases
- Use `subTest` for multiple similar test cases

## Continuous Integration

### Current Status
- Tests are designed to run in QGIS environment
- Manual execution required (no automated CI/CD for QGIS plugins)
- Focus on comprehensive local testing before deployment

### Future CI/CD Considerations
- Tests could be adapted for headless QGIS execution
- Docker containers with QGIS could enable automated testing
- Consider GitHub Actions with QGIS Docker images

## Contributing New Tests

### Before Adding Tests

1. **Identify the gap** - What functionality isn't covered?
2. **Choose test category** - Validation, unit, integration, or manual
3. **Review existing patterns** - Follow established conventions
4. **Consider dependencies** - Handle missing modules gracefully

### Test Review Checklist

- [ ] Test follows naming conventions
- [ ] Proper QGIS environment setup
- [ ] Both plugin and standalone import compatibility
- [ ] Comprehensive test cases (positive and negative)
- [ ] Good documentation and comments
- [ ] Proper error handling and assertions
- [ ] Integration with existing test structure

## Test Maintenance

### When to Update Tests

1. **Adding new coordinate formats** - Add pattern detection and conversion tests
2. **Changing parsing logic** - Update affected validation tests
3. **Fixing bugs** - Add regression tests to prevent reoccurrence
4. **Refactoring code** - Ensure tests still validate behavior

### Test Debugging Workflow

1. Run individual failing test with verbose output
2. Add debug prints to understand failure point
3. Test regex patterns in isolation if needed
4. Verify QGIS environment setup
5. Check import compatibility for both contexts

## Example Test Scenarios

### Testing New Coordinate Format

```python
def test_new_coordinate_format(self):
    """Test detection and parsing of new coordinate format"""
    test_cases = [
        ('VALID_FORMAT_EXAMPLE', True, (expected_lat, expected_lon)),
        ('INVALID_FORMAT', False, None),
    ]
    
    for coord_text, should_parse, expected in test_cases:
        with self.subTest(coord=coord_text):
            result = self.parser.parse(coord_text)
            
            if should_parse:
                self.assertIsNotNone(result, f"Should parse: {coord_text}")
                lat, lon, bounds, crs = result
                exp_lat, exp_lon = expected
                self.assertAlmostEqual(lat, exp_lat, places=3)
                self.assertAlmostEqual(lon, exp_lon, places=3)
            else:
                self.assertIsNone(result, f"Should reject: {coord_text}")
```

### Testing Error Conditions

```python
def test_error_handling(self):
    """Test proper error handling for invalid inputs"""
    invalid_inputs = [
        "",                    # Empty string
        "not_a_coordinate",    # Invalid text
        "999 999",            # Out of range
        None,                 # None input
    ]
    
    for invalid_input in invalid_inputs:
        with self.subTest(input=invalid_input):
            result = self.parser.parse(invalid_input)
            self.assertIsNone(result, f"Should reject invalid input: {invalid_input}")
```

## Summary

The Lat Lon Tools plugin has comprehensive test coverage focusing on:
- **Regex pattern validation** to catch syntax bugs
- **Coordinate format detection** across all supported formats  
- **Z coordinate and elevation handling** for 3D data
- **Error handling and edge cases** for robust parsing
- **Real-world scenarios** for practical validation

All tests are designed to work with QGIS Python environment and handle both plugin and standalone execution contexts. The testing infrastructure provides confidence in the parser's ability to handle diverse coordinate formats while properly rejecting invalid inputs.