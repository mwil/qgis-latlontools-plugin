# Changelog

All notable changes to the QGIS Lat Lon Tools plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Changelog file to track plugin improvements and fixes

### Fixed
- **Zoom to Coordinate**: Input field is now preserved when switching between lat/lon and lon/lat coordinate order
  - Previously, clicking the XY/YX button would clear the input field
  - Now maintains the entered coordinate while updating the interpretation order
  - Affects `zoomToLatLon.py:345-359` in the `xyButtonClicked()` method
  - Improves user experience by preventing data loss during coordinate order changes

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

*Note: This changelog started with version 3.7.5-dev. Previous changes can be found in the metadata.txt file.*