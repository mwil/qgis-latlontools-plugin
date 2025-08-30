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
- User always runs QGIS for testing
- No automated test suite - manual testing required through QGIS interface
- Plugin Reloader tool is available for development - use this to reload plugin changes without restarting QGIS
- After deployment with `make deploy`, use Plugin Reloader to refresh the plugin

## Architecture

### Main Components
- **LatLonTools** (`latLonTools.py`) - Main plugin class managing GUI and tool coordination
- **Settings** (`settings.py`) - Configuration dialog and settings management
- **Processing Provider** (`provider.py`, `latLonToolsProcessing.py`) - QGIS Processing framework integration

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
- **No automated test suite** - manual testing required
- Test with various coordinate formats and edge cases
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
3. Manual testing required (no automated tests available)
4. Run `make deploy` for local testing
5. Consider internationalization for user-facing strings
6. Update documentation if adding significant features