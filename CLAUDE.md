# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the "Lat Lon Tools" plugin for QGIS, providing comprehensive coordinate handling, conversion, and mapping tools. It supports multiple coordinate formats (WGS84, DMS, UTM, UPS, MGRS, Plus Codes, Geohash, H3, Maidenhead grid, GEOREF, WKT, GeoJSON, ECEF) and integrates with external mapping services.

## Development Commands

### Build and Deploy
- `make deploy` - Deploy plugin to QGIS plugins directory, build translations, and generate documentation
- **Note**: HTML documentation generation requires Python markdown module. Use `.venv` virtual environment:
  ```bash
  source .venv/bin/activate && python -m markdown -x extra readme.md >> index.html
  ```

### Translation Management
- Translation files: `i18n/latlonTools_fr.ts` (French), `i18n/latlonTools_zh.ts` (Chinese)  
- Compiled automatically during deployment to `.qm` files

### Testing Workflow
- **Comprehensive test suite available** - Use `python3 run_all_tests.py` to run all tests
- **Mixed testing approach**:
  - Standalone tests (no QGIS required): `python3 run_all_tests.py --type standalone`
  - Service layer tests (QGIS required): `python3 run_all_tests.py --type service`
  - Validation tests (QGIS required): `python3 run_all_tests.py --type validation` 
  - Integration tests (QGIS required): `python3 run_all_tests.py --type integration`
- **Fast mode available**: `python3 run_all_tests.py --fast` (skips slow integration tests)
- **Cross-platform QGIS detection**: Test runner automatically detects QGIS installation on macOS/Windows/Linux
- **Manual testing still important**: Plugin Reloader tool available for development
- After deployment with `make deploy`, use Plugin Reloader to refresh the plugin

### Test Structure
```
tests/
├── unit/                          # Standalone tests (no QGIS)
│   ├── test_pattern_detection.py
│   └── test_smart_parser_simple.py
├── integration/                   # QGIS-dependent integration tests
│   ├── test_service_layer_integration.py
│   └── test_comprehensive_parser_regression.py
├── validation/                    # QGIS-dependent validation tests
│   ├── test_regex_validation.py
│   ├── test_z_coordinate_handling.py
│   ├── test_coordinate_flipping_comprehensive.py
│   ├── test_real_world_coordinate_scenarios.py
│   ├── test_smart_parser_validation.py
│   └── test_comprehensive_edge_cases.py
└── run_all_tests.py              # Unified test runner
```

## Release Management

### Automated GitHub Actions Workflows

The plugin uses GitHub Actions for automated building, testing, and releasing:

#### 1. Development Builds (`build.yml`)
**Triggers**: Push to `main`/`develop`, Pull Requests, Manual dispatch
- Builds plugin package for testing
- Runs linting (flake8, pylint)
- Creates development artifacts (30-day retention)
- Package format: `latlontools-{version}-dev-{commit}.zip`

#### 2. Automatic Releases (`release.yml`) 
**Trigger**: Git tags matching `v*` pattern (e.g., `v3.7.5`)
- Automatically updates `metadata.txt` with release version
- Updates `CHANGELOG.md` with release date
- Builds complete plugin package
- Creates GitHub release with downloadable zip
- Package format: `latlontools-{version}.zip`

#### 3. Manual Releases (`manual-release.yml`)
**Trigger**: Manual GitHub Actions dispatch
- Allows creating releases without pushing tags
- Input validation for semantic versioning
- Optional pre-release marking
- Same build and packaging process as automatic releases

### Release Process

#### Option A: Tag-based Release (Recommended)
```bash
# 1. Ensure CHANGELOG.md has [Unreleased] section with changes
# 2. Create and push a version tag
git tag v3.7.5
git push origin v3.7.5

# 3. GitHub Actions will automatically:
#    - Update metadata.txt to version 3.7.5
#    - Update CHANGELOG.md with release date  
#    - Build and package plugin
#    - Create GitHub release with downloadable zip
#    - Commit updated files back to main branch
```

#### Option B: Manual Release
1. Go to GitHub Actions → "Manual Release" workflow
2. Click "Run workflow"
3. Enter version (e.g., `3.7.5`)
4. Choose options (pre-release, create tag)
5. Run the workflow

### Package Structure
Released zip files contain:
```
latlontools-3.7.5.zip
└── latlontools/
    ├── *.py                    # All Python modules
    ├── metadata.txt            # Updated with release version
    ├── icon.png, LICENSE       # Plugin assets
    ├── ui/                     # Qt UI files
    ├── images/                 # Icons and graphics
    ├── i18n/                   # Translations (.qm files)
    ├── doc/                    # Documentation images
    ├── index.html              # Generated HTML docs
    ├── readme.md               # Main README
    └── PLUGIN_ENHANCEMENTS_README.md  # Feature documentation
```

### Version Management
- **metadata.txt**: Automatically updated by release workflows
- **CHANGELOG.md**: Uses "Keep a Changelog" format with [Unreleased] sections
- **Semantic Versioning**: Uses `major.minor.patch` format (e.g., 3.7.5)
- **Development versions**: Marked as `-dev` in metadata.txt

### QGIS Plugin Repository Integration
1. Download release zip from GitHub Releases page
2. Extract and test plugin locally using `make deploy`
3. Submit to QGIS Plugin Repository manually
4. The `metadata.txt` will already have correct version from automated build

## Architecture

### Main Components
- **LatLonTools** (`latLonTools.py`) - Main plugin class managing GUI and tool coordination
- **Settings** (`settings.py`) - Configuration dialog and settings management
- **Processing Provider** (`provider.py`, `latLonToolsProcessing.py`) - QGIS Processing framework integration

### Service Layer Architecture (Phase 2 - Completed)

The plugin implements a centralized service layer for coordinate parsing, eliminating code duplication and providing consistent functionality across all UI components.

**Core Service Components:**
- **CoordinateParserService** (`parser_service.py`) - Singleton service managing SmartCoordinateParser instances
- **CoordinateParserMixin** - Mixin class for UI components needing parser functionality  
- **parse_coordinate_with_service()** - Convenience function for components that can't use mixin pattern

**Service Layer Benefits:**
- **Centralized parsing logic**: Single point of truth for coordinate parsing
- **Singleton pattern**: Thread-safe, fork-safe parser instance management
- **Fallback mechanisms**: Graceful degradation with legacy parsing functions
- **Consistent logging**: Centralized error handling and component-specific logging
- **Minimal refactoring**: Fork-safe approach preserving upstream compatibility

**UI Integration Status (✅ All Complete):**
- **coordinateConverter.py**: Uses `parse_coordinate_with_service()` in `commitWgs84()`
- **digitizer.py**: Uses service layer in `addFeature()` with projection-specific parsing
- **multizoom.py**: Uses service layer in `addSingleCoord()` for multi-location zoom
- **zoomToLatLon.py**: Uses service layer in `convertCoordinate()` with comprehensive fallback

### Coordinate System Modules
Each coordinate system has a dedicated module: `utm.py`, `ups.py`, `mgrs.py`, `pluscodes.py`/`olc.py`, `geohash.py`, `maidenhead.py`, `georef.py`, `ecef.py`

### Dialog Classes
- `coordinateConverter.py` - Coordinate conversion dialog
- `digitizer.py` - Point digitizing dialog  
- `multizoom.py` - Multi-location zoom dialog
- `zoomToLatLon.py` - Single coordinate zoom dialog

### Processing Algorithms
Conversion utilities in separate modules: `field2geom.py`, `geom2field.py`, `mgrstogeom.py`, `tomgrs.py`, `geom2wkt.py`, `wkt2layers.py`

## Code Conventions

### Python Style
- Standard Python naming (snake_case functions/variables, PascalCase classes)
- QGIS plugin conventions (classFactory, initGui, unload methods)
- PyQt signal/slot patterns
- Comprehensive docstrings throughout

### QGIS Integration
- Processing algorithms extend QgsProcessingAlgorithm
- Map tools extend QgsMapTool
- Proper resource cleanup in unload method
- Uses QGIS PyQt for UI components

### Error Handling
- Extensive input validation for coordinate formats
- Graceful handling of missing dependencies (e.g., H3 library)
- User-friendly error messages

## Development Notes

### Testing
- **Comprehensive automated test suite available** - Run `python3 run_all_tests.py`
- **Test Categories**:
  - Unit tests: Pattern detection, parser logic (no QGIS required)
  - Service layer tests: Singleton pattern, UI integration (QGIS required)
  - Validation tests: Regex patterns, coordinate handling (QGIS required)  
  - Integration tests: End-to-end coordinate parsing (QGIS required)
- **Cross-platform support**: Automatic QGIS environment detection (macOS/Windows/Linux)
- **Manual testing still recommended**: Test with various coordinate formats and edge cases
- Test in different QGIS environments and CRS settings
- Verify processing algorithms work in QGIS Processing toolbox

### Plugin Structure
- Standard QGIS plugin: `__init__.py` with `classFactory()`, `metadata.txt`
- UI files in `ui/` directory (Qt Designer .ui files)
- Images and icons in `images/` directory
- Documentation in `doc/` directory

### Dependencies
- Built on QGIS core libraries and PyQt
- Optional dependencies handled gracefully
- No external package management (relies on QGIS environment)

## Task Completion Checklist

When completing development tasks:
1. Follow existing code style and QGIS plugin conventions
2. Handle coordinate format edge cases and invalid inputs
3. **Run comprehensive test suite**: `python3 run_all_tests.py` (validates service layer integration)
4. **Use service layer for coordinate parsing**: Import `parse_coordinate_with_service` instead of directly instantiating SmartCoordinateParser
5. Run `make deploy` for local testing
6. Consider internationalization for user-facing strings
7. Update documentation if adding significant features
8. **Service layer components should use**: `from .parser_service import parse_coordinate_with_service` and provide fallback functions when needed