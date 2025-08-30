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