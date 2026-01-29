# Changelog

All notable changes to the QGIS Lat Lon Tools plugin will be documented in this
file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Noise Character Sanitization**: Added support for parsing coordinates from
  markdown tables by sanitizing pipe (`|`) separators and other noise characters
- **Lazy Loader Import Fixes**: Fixed import mechanism to use
  `importlib.import_module()` for compatibility with QGIS Python environment
  (older Python versions)
- **ECEF Dependency Removed**: Replaced pyproj hard dependency with QGIS
  built-in coordinate transformation (EPSG:4978/4979)
- **H3 Optional Dependency**: Added proper error handling for missing H3 library
  in legacy fallback functions
- **QGIS Log Level Fixes**: Fixed `Qgis.Debug` references (doesn't exist in QGIS
  API) to use `Qgis.Info` instead
- **Release Workflow**: Updated branch protection bypass to include Maintain
  role for GitHub Actions

### Changed

- **Makefile**: Fixed Linux OS detection for plugin deployment path
- **Test Coverage**: Added end-to-end tests for legacy grid coordinate formats

## [3.14.0] - 2026-01-29

### Added

- **Fast-Path Coordinate Parser**: Performance optimization reducing parsing
  attempts from 13+ to 1-3 for common cases
- **ASCII Whitelist Filtering**: Early rejection of invalid characters before
  expensive parsing operations
- **O(1) Format Classification**: Fast-path triage for zero-ambiguity formats
  (WKB, GeoJSON, EWKT, Plus Codes, etc.)
- **Strategy Pre-Filtering**: `can_parse()` methods to avoid expensive parse()
  calls on non-matching strategies
- **Comprehensive Test Coverage**: Coordinate order edge case tests (12 tests)
  and pattern collision tests
- **Performance Benchmarking**: New benchmark_parser.py for measuring parser
  performance improvements

### Fixed

- **Critical Coordinate Parsing Bug**: Fixed DMS parser pre-filter that
  incorrectly rejected valid decimal coordinates with longitude > 90°
- **GeoJSON Boolean Logic**: Fixed precedence issue with compound boolean
  expressions
- **Plus Codes Validation**: Fixed validation for empty strings and invalid
  character sets
- **MGRS Pattern**: Corrected pattern to match specification (2 grid letters,
  not 2-3)
- **Strategy Selection**: Removed artificial candidates[:2] limit that could
  skip valid formats

### Performance

- **85.5% reduction** in strategy attempts overall
- **4.3x faster** for typical decimal lat/long input (90%+ of real usage)
- **0.0035ms overhead** for preprocessing and classification

### Documentation

- Enhanced thread safety documentation in parser_service.py
- Added fork-safe cleanup procedures
- Fixed bare except clauses to except Exception: with proper error handling

## [3.13.0] - 2025-09-26

### Fixed

- **Emergency Shutdown System**: Implemented comprehensive emergency cleanup to
  prevent QGIS hanging during plugin unload
- **Canvas Resource Management**: Added aggressive cleanup of QgsRubberBand
  objects and markers that could cause shutdown hanging
- **Signal Management**: Fixed signal disconnection to specify exact slots,
  preventing interference with other plugins
- **Singleton Cleanup**: Enhanced CoordinateParserService reset with fallback
  mechanisms for shutdown scenarios
- **Widget Cleanup**: Improved dock widget cleanup with priority-based emergency
  strategies
- **Processing Provider**: Added emergency removal of processing providers that
  could block shutdown

## [3.12.0] - 2025-01-09

### Added

- **High-Performance Coordinate Detection**: FastCoordinateDetector with up to
  10x faster format detection using pre-compiled regex patterns
- **Optimized Coordinate Parser**: OptimizedCoordinateParser with smart routing
  to appropriate parsers and performance monitoring
- **Comprehensive Regex Test Coverage**: Copilot regression tests preventing
  coordinate parsing regressions
- **UI Input Preservation**: Coordinate input is now preserved when toggling
  coordinate order preferences
- **Repository Cleanup**: Comprehensive .gitignore preventing Python cache files
  and IDE artifacts from being committed

### Fixed

- **Regex Pattern Consistency**: Fixed asymmetric digit requirements in
  obviously_projected pattern for consistent UTM coordinate detection
- **GitHub Copilot Issues**: Addressed 5 code quality issues including regex
  documentation, performance optimizations, and error handling
- **Coordinate Assignment Logic**: Corrected coordinate order interpretation for
  OrderYX/OrderXY preferences
- **Plugin Reload Issues**: Fixed duplicate panel creation and AttributeError
  exceptions during plugin unload/reload cycles
- **Resource Leaks**: Enhanced signal disconnection and Qt widget lifecycle
  management to prevent orphaned resources

### Changed

- **Performance Architecture**: Service layer now uses OptimizedCoordinateParser
  with fast format detection and lazy loading
- **Error Handling**: Refactored nested try-except blocks into separate helper
  methods for better maintainability
- **Code Quality**: Improved regex readability with re.VERBOSE patterns and
  removed print statements from unit tests
- **Import Organization**: Moved imports out of performance-critical parsing
  loops to module level

---

## [3.10.0] - 2025-09-01

### Added

- **Service Layer Architecture**: Centralized coordinate parsing service with
  singleton pattern eliminating 15+ line code duplication across UI components
- **Try-Parse Architecture**: Exception-based parsing using mature coordinate
  libraries instead of error-prone regex pre-validation
- **Comprehensive Test Infrastructure**: Unified test runner with cross-platform
  QGIS detection supporting standalone, service, validation, and integration
  tests
- **Enhanced Coordinate Format Support**: Optimal strategy ordering by format
  signature strength to minimize collision risk

### Fixed

- **Critical UTM Misclassification Bug**: UTM coordinates like
  `500000 4500000 1000` are no longer incorrectly parsed as DMS coordinates
- **Service Layer Integration**: All UI components (coordinateConverter,
  digitizer, multizoom, zoomToLatLon) now use centralized parser service
- **Python Syntax Errors**: Fixed critical indentation errors preventing code
  execution after refactoring
- **Regex Pattern Bugs**: Resolved critical double backslash issues in
  coordinate format detection

### Changed

- **Fundamental Architecture Shift**: From regex pre-validation to mature
  library validation with exception handling
- **Parser Strategy Pattern**: Simplified base class with direct parsing, no
  complex `can_parse()` methods
- **Enhanced Validation Logic**: Added projected coordinate detection and UTM
  pattern recognition to prevent false positives

---

## [3.9.0] - 2025-09-01

### Added

- **Comprehensive Parser Integration**: SmartCoordinateParser now used
  consistently across all UI components (zoomToLatLon, digitizer, multizoom)
- **Cross-Platform Test Support**: Test suites now support Windows, Linux, and
  macOS with dynamic QGIS path detection
- **Performance Optimizations**: Pre-compiled regex patterns for improved
  coordinate parsing performance
- **Regex Validation Framework**: Comprehensive test suite to prevent regex
  over-escaping issues

### Fixed

- **WKB 3D Coordinate Parsing**: Fixed critical issue where WKB coordinates
  failed in zoomToLatLon but worked in other components
- **Parser Integration Inconsistencies**: All coordinate input components now
  use SmartCoordinateParser as primary parser with legacy fallback
- **Regex Over-Escaping Issues**: Fixed multiple regex patterns that would match
  literal backslashes instead of intended characters
- **Cross-Platform Compatibility**: Test suites now work across different
  operating systems and QGIS installations

### Changed

- **Architecture**: Unified coordinate parsing strategy across all UI components
  for consistency
- **Testing**: Enhanced test framework with 16 comprehensive tests covering
  parser integration and regex validation
- **Error Handling**: Improved logging with QgsMessageLog for better debugging
  in QGIS environment
- **Performance**: Optimized regex compilation to reduce repeated pattern
  compilation overhead

---

## [3.8.1] - 2025-09-01

### Added

- **Comprehensive Test Infrastructure**: New validation test suite with 34+
  tests across 5 test files
- **GitHub Actions CI/CD**: Complete workflows for automated builds, testing,
  and releases
- **Manual WKB Parsing**: Fallback parser for non-standard WKB geometries that
  QGIS can't handle
- **Test Documentation**: TESTING_GUIDE.md and GITHUB_ACTIONS_TESTING.md with
  complete testing workflows

### Fixed

- **Critical WKB 3D Parsing**: Fixed parsing failures for valid 3D WKB
  geometries with SRID
  - Now correctly handles POINT Z geometries like
    `01010000A0281A00005396BF88FF9560405296C6D462D64040A857CA32C41D7240`
- **UTM Coordinate Detection**: Enhanced parsing to handle elevation suffixes
  and prevent invalid transformations
  - Properly rejects UTM coordinates with elevation (e.g.,
    `33N 315428 5741324 1234`) instead of misinterpreting as lat/lon
- **DMS Elevation Handling**: Fixed DMS parsing to strip elevation suffixes
  before coordinate extraction
  - Now correctly parses coordinates like `40°42'46"N 74°00'22"W 1234m`
- **Regex Pattern Bugs**: Resolved critical double backslash issues in
  coordinate format detection
- **Import Compatibility**: Fixed relative import issues across multiple modules
  for standalone testing
- **GitHub Actions Workflows**: Updated deprecated actions and fixed Python
  syntax errors preventing CI/CD execution

### Changed

- **Test Runner**: Enhanced to support all validation test files with proper
  QGIS initialization
- **Error Messages**: Improved coordinate validation error reporting with
  geographic bounds checking
- **Code Quality**: Standardized regex patterns, group access, and consistent
  return formats across parsers

### Technical Improvements

- **WKB Parser**: Added manual parsing for IEEE 754 double precision coordinates
- **UTM Validation**: Added geographic bounds checking to prevent invalid
  coordinate transformations
- **Test Coverage**: Comprehensive regex validation tests to catch pattern
  matching bugs automatically
- **CI/CD Pipeline**: Modern GitHub Actions workflows with artifact management
  and automated releases

---

## [3.8.0] - 2025-08-30

### Added

- Changelog file to track plugin improvements and fixes

### Fixed

- **Zoom to Coordinate**: Input field is now preserved when switching between
  lat/lon and lon/lat coordinate order
  - Previously, clicking the XY/YX button would clear the input field
  - Now maintains the entered coordinate while updating the interpretation order
  - Affects `zoomToLatLon.py:345-359` in the `xyButtonClicked()` method
  - Improves user experience by preventing data loss during coordinate order
    changes

### Changed

- None

### Deprecated

- None

### Removed

- None

### Security

- None

---

## [3.7.4] - 2024-XX-XX

### Changed

- Updated to work with H3 version 4.x.x
- Fix to handle invalid geometries in Point layer to MGRS
- Add clear marker button to Multi-zoom panel
- Update metadata
- Move repository location

---

_Note: This changelog started with version 3.7.5-dev. Previous changes can be
found in the metadata.txt file._
