# GitHub Actions Testing Guide for QGIS Plugins

## Overview

This document outlines approaches for running QGIS plugin tests in GitHub Actions using official QGIS Docker images. Based on research from 2024-2025, there are robust solutions available for automated QGIS plugin testing in CI/CD pipelines.

## Available QGIS Docker Images

### Official Images (qgis/qgis)
- **qgis/qgis:latest** - Latest development build (daily updates)
- **qgis/qgis:release-3_28** - QGIS 3.28 LTR
- **qgis/qgis:release-3_30** - QGIS 3.30 LTR
- **qgis/qgis:release-3_34** - QGIS 3.34 LTR

### Key Features
- **Headless Environment**: Includes xvfb for display simulation
- **Full QGIS API**: Complete Python API access
- **Plugin Testing**: Designed for automated plugin testing
- **Daily Builds**: Automatically updated with latest QGIS code

## GitHub Actions Workflow Approaches

### Approach 1: Direct Container Execution

```yaml
name: QGIS Plugin Tests
on: 
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    container: qgis/qgis:latest
    
    steps:
      - name: Checkout Plugin Code
        uses: actions/checkout@v4
        
      - name: Setup QGIS Environment
        run: |
          export QT_QPA_PLATFORM=offscreen
          export QGIS_PREFIX_PATH=/usr
          
      - name: Run Regex Pattern Tests
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_regex_pattern_validation.py
          
      - name: Run Z Coordinate Tests
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_z_coordinate_handling.py
          
      - name: Run Comprehensive Tests
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_smart_parser_validation.py
```

### Approach 2: Matrix Testing (Multiple QGIS Versions)

```yaml
name: QGIS Plugin Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        qgis_version: [release-3_28, release-3_30, latest]
        
    container: qgis/qgis:${{ matrix.qgis_version }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Test Plugin on QGIS ${{ matrix.qgis_version }}
        run: |
          export QT_QPA_PLATFORM=offscreen
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 -m unittest discover tests/validation/ -v
```

### Approach 3: External Docker Run

```yaml
name: QGIS Plugin Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Pull QGIS Docker Image
        run: docker pull qgis/qgis:latest
        
      - name: Run Tests in QGIS Container
        run: |
          docker run --rm \
            -v ${{ github.workspace }}:/plugin \
            -w /plugin \
            -e DISPLAY=:99 \
            qgis/qgis:latest \
            sh -c "xvfb-run -s '+extension GLX -screen 0 1024x768x24' python3 tests/validation/test_regex_pattern_validation.py"
```

### Approach 4: Using QGIS Plugin CI Tool

```yaml
name: Plugin CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install QGIS Plugin CI
        run: pip install qgis-plugin-ci
        
      - name: Run Plugin Tests
        run: |
          qgis-plugin-ci test \
            --docker-image qgis/qgis:latest \
            --tests-directory tests/validation
```

## Configuration for This Project

### Recommended Workflow for Lat Lon Tools Plugin

```yaml
name: Lat Lon Tools Tests
on:
  push:
    branches: [ main, feature/* ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        qgis_version: [release-3_28, release-3_30, latest]
      fail-fast: false
      
    container: qgis/qgis:${{ matrix.qgis_version }}
    
    steps:
      - name: Checkout Plugin
        uses: actions/checkout@v4
        
      - name: Setup QGIS Testing Environment
        run: |
          export QT_QPA_PLATFORM=offscreen
          export QGIS_PREFIX_PATH=/usr
          export PYTHONPATH=/usr/share/qgis/python/plugins:$PYTHONPATH
          
      - name: Test Regex Pattern Validation
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_regex_pattern_validation.py -v
          
      - name: Test Z Coordinate Handling
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_z_coordinate_handling.py -v
          
      - name: Test Comprehensive Edge Cases
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_comprehensive_edge_cases.py -v
          
      - name: Test Real World Scenarios
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_real_world_coordinate_scenarios.py -v
          
      - name: Test Coordinate Flipping
        run: |
          xvfb-run -s '+extension GLX -screen 0 1024x768x24' \
          python3 tests/validation/test_coordinate_flipping_comprehensive.py -v
          
      - name: Generate Test Summary
        if: always()
        run: |
          echo "## Test Results for QGIS ${{ matrix.qgis_version }}" >> $GITHUB_STEP_SUMMARY
          echo "All validation tests completed" >> $GITHUB_STEP_SUMMARY
```

## Implementation Benefits

### For Lat Lon Tools Plugin

1. **Automated Validation**
   - Catches regex pattern bugs automatically
   - Validates coordinate parsing across QGIS versions
   - Tests WKB, UTM, DMS, and other format handling

2. **Multi-Version Support**
   - Test against QGIS 3.28 LTR, 3.30, and latest
   - Ensures compatibility across QGIS releases
   - Early detection of API changes

3. **Comprehensive Coverage**
   - All 5 validation test files can run automatically
   - Real QGIS environment (not mocked)
   - Full coordinate transformation and CRS support

4. **Development Workflow**
   - Run on every push and pull request
   - Catch issues before manual testing
   - Maintain code quality automatically

## Technical Requirements

### Environment Setup
```bash
# Required for headless QGIS
export QT_QPA_PLATFORM=offscreen
export DISPLAY=:99

# QGIS Python path
export PYTHONPATH=/usr/share/qgis/python/plugins:$PYTHONPATH

# Run with xvfb for display simulation
xvfb-run -s '+extension GLX -screen 0 1024x768x24' python3 test_file.py
```

### Test Compatibility
- Tests must handle both plugin and standalone import contexts
- QGIS initialization required for coordinate transformations
- Mock objects needed for iface and settings in unit tests
- Graceful handling of missing optional dependencies (MGRS, H3, etc.)

## Alternative Solutions

### 1. Custom Docker Images
- Build custom images with specific plugin dependencies
- Pre-install required Python packages
- Optimized for faster CI execution

### 2. QGIS Testing Framework
- Use `qgis.testing` module for unit tests
- Lighter weight than full QGIS container
- Limited to non-UI functionality

### 3. Hybrid Approach
- Unit tests with qgis.testing
- Integration tests with full Docker container
- Manual UI testing still required

## Implementation Timeline

### Phase 1: Basic Setup
- Single QGIS version (latest)
- Core validation tests only
- Basic workflow configuration

### Phase 2: Enhanced Coverage
- Matrix testing across QGIS versions
- All validation test files
- Test result reporting

### Phase 3: Advanced Features
- Coverage reporting
- Artifact generation
- Integration with existing workflows

## Conclusion

**Recommendation**: Use Approach 2 (Matrix Testing) for comprehensive coverage across QGIS versions. The official QGIS Docker images provide robust, actively maintained testing infrastructure that's perfect for the Lat Lon Tools plugin's comprehensive test suite.

The combination of:
- Daily updated Docker images
- Headless testing with xvfb
- Full QGIS Python API access
- Matrix testing across versions

Makes this an ideal solution for automated testing of coordinate parsing functionality, regex patterns, and QGIS-specific features like coordinate transformations and CRS handling.