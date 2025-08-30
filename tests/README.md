# QGIS Lat Lon Tools - Test Suite

Comprehensive testing infrastructure for the Smart Coordinate Parser and plugin functionality.

## 🧪 Test Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_pattern_detection.py      # Basic pattern matching tests
│   └── test_smart_parser_full.py      # Complete parser with QGIS mocks
├── validation/              # End-to-end validation tests
│   ├── test_smart_parser_validation.py    # Final validation suite
│   └── test_comprehensive_edge_cases.py   # Comprehensive edge cases
└── debug/                   # Debug utilities and tools
    ├── debug_maidenhead.py    # Maidenhead pattern debugging
    ├── debug_dms.py           # DMS detection debugging
    └── debug_format_flow.py   # Format detection flow analysis
```

## 🚀 Running Tests

### Quick Start
```bash
# Run all tests
make test

# Run specific test type
make test-unit           # Unit tests only
make test-validation     # Validation tests only
make test-verbose        # Verbose output
```

### Direct Runner
```bash
# Using test runner directly
./run_tests.py                    # All tests
./run_tests.py --type unit        # Unit tests
./run_tests.py --type validation  # Validation tests
./run_tests.py --verbose          # Verbose mode
```

### Individual Tests
```bash
# Run specific test files
python tests/validation/test_smart_parser_validation.py
python tests/unit/test_pattern_detection.py
```

## 📊 Test Coverage

### ✅ Smart Coordinate Parser Tests
- **100% validation success** on 23 critical edge cases
- **Pattern detection accuracy** for all coordinate formats
- **Coordinate order handling** with user preferences
- **Error handling** and edge case management

### 🧪 Test Categories

#### Validation Tests
- Final refinement validation (100% success rate)
- Comprehensive edge case testing (65+ test cases)
- Real-world coordinate format scenarios
- Boundary condition testing

#### Unit Tests  
- Pattern detection logic testing
- Individual format parser testing
- Coordinate validation testing  
- Mock QGIS environment testing

#### Debug Utilities
- Interactive debugging tools
- Format detection flow analysis
- Pattern matching diagnostics
- Development troubleshooting aids

## 🔧 Development Workflow

### Adding New Tests
1. Create test files in appropriate directory (`unit/` or `validation/`)
2. Follow naming convention: `test_*.py`
3. Run tests with `make test` to validate

### Test Structure
```python
def test_coordinate_format():
    """Test description"""
    # Arrange
    test_input = "coordinate string"
    
    # Act
    result = parser.parse(test_input)
    
    # Assert
    assert result.format == "Expected Format"
    assert result.coordinates == (lat, lon)
```

### Debugging Failed Tests
```bash
# Use debug utilities
python tests/debug/debug_format_flow.py
python tests/debug/debug_maidenhead.py
python tests/debug/debug_dms.py
```

## 🎯 Test Philosophy

Our testing approach focuses on:

1. **Production Readiness** - Tests validate real-world usage scenarios
2. **Edge Case Coverage** - Comprehensive testing of boundary conditions  
3. **Pattern Validation** - Ensuring coordinate format detection accuracy
4. **Regression Prevention** - Catching issues before they reach users
5. **Development Support** - Tools to aid debugging and development

## 🚀 Continuous Integration Ready

The test suite is designed to work:
- ✅ **Without QGIS installation** (uses mocks)
- ✅ **In automated environments** (CI/CD compatible)  
- ✅ **With minimal dependencies** (standard library focused)
- ✅ **Fast execution** (optimized for developer workflow)

## 📈 Test Results History

- **Smart Parser Validation**: 23/23 (100% success)
- **Comprehensive Edge Cases**: Production-ready accuracy
- **Pattern Detection**: All coordinate formats validated
- **Coordinate Order Handling**: Full user preference support

This testing infrastructure ensures the Smart Coordinate Parser maintains its production-ready quality while supporting ongoing development and enhancement.
