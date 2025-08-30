# Lat Lon Tools Plugin Enhancements

This document describes the new enhanced functionality added to the Lat Lon Tools plugin for QGIS. These enhancements make coordinate input more intuitive, flexible, and persistent across sessions.

## New Features Overview

### 1. Smart Auto-Detect Mode
**What it does**: Automatically detects and parses multiple coordinate formats without requiring you to specify the format in advance.

**Where to find it**: 
- Settings Dialog: "Smart Auto-Detect (Any Format)" option in the coordinate system dropdown
- Zoom to Coordinate Dialog: "Smart Auto-Detect" option in the CRS menu

**Supported Formats**:
- **WKT (Well-Known Text)**: `POINT(longitude latitude)`
- **EWKT (Extended WKT)**: `SRID=4326;POINT(longitude latitude)`
- **WKB (Well-Known Binary)**: Hexadecimal encoded binary format
- **MGRS**: Military Grid Reference System coordinates
- **Plus Codes**: Open Location Code format (e.g., `8FVC2222+22`)
- **UTM**: Universal Transverse Mercator (e.g., `33N 315428 5741324`)
- **UPS**: Universal Polar Stereographic coordinates
- **Geohash**: Base-32 encoded coordinates (e.g., `u4pruydqqvj`)
- **Maidenhead**: Ham radio grid squares (e.g., `JN58td`)
- **H3**: Uber's H3 hexagonal hierarchical spatial index (if installed)
- **GeoJSON**: Point geometry in JSON format
- **Decimal Degrees**: Standard lat/lon (e.g., `40.7128, -74.0060`)
- **DMS**: Degrees, Minutes, Seconds (e.g., `40°42'46"N 74°00'22"W`)

### 2. Text Preservation During Order Changes
**What it does**: When you click the X,Y ↔ Y,X button to change coordinate order, your input text is preserved instead of being cleared.

**Why it's useful**: You can experiment with different coordinate orders without losing your input and having to retype coordinates.

**How it works**: The enhancement automatically saves your input text, changes the coordinate order, updates the UI labels, then restores your text.

### 3. Enhanced Settings Persistence
**What it does**: Your selected coordinate mode and settings are automatically saved and restored when you restart QGIS.

**What's saved**:
- Selected coordinate system/format
- Coordinate order preference (X,Y vs Y,X)
- Smart Auto-Detect mode selection

### 4. Improved Zoom Functionality
**What it does**: The "Zoom to Coordinate" dialog now properly zooms the map to show your target location at an appropriate scale.

**Smart Zoom Behavior**:
- If map is very zoomed out (scale > 100,000): Zooms to 1:50,000 scale
- If moderately zoomed out (scale > 50,000): Zooms to 1:25,000 scale  
- If already zoomed in: Centers on point but maintains current zoom level

## Usage Guide

### Using Smart Auto-Detect Mode

1. **Enable Smart Auto-Detect**:
   - Open Settings Dialog (Plugin menu → Lat Lon Tools → Settings)
   - Select "Smart Auto-Detect (Any Format)" from the dropdown
   - Click OK to save

2. **Input Coordinates**:
   - Open "Zoom to Coordinate" dialog
   - Enter coordinates in ANY supported format
   - The plugin will automatically detect the format and parse accordingly
   - No need to specify the coordinate system in advance

3. **Coordinate Order Preference**:
   - Set your preferred order (Lat/Lon vs Lon/Lat) in settings
   - Smart Auto-Detect will prefer this order for ambiguous inputs
   - The dialog label shows your current preference

### Best Practices for Smart Auto-Detect

**For Unambiguous Formats** (always detected correctly):
- Use WKT: `POINT(-74.0060 40.7128)` 
- Use MGRS: `18TWL8040944131`
- Use Plus Codes: `87G7QX2F+2X`
- Use UTM with zone: `18N 583960 4507523`

**For Potentially Ambiguous Decimal Degrees**:
- Include directional indicators when possible: `40.7128N, 74.0060W`
- Use hemisphere indicators: `40.7128, -74.0060` (negative = West/South)
- Be aware of your coordinate order setting (Lat/Lon vs Lon/Lat)

**Format Examples**:
```
# WKT formats
POINT(-74.0060 40.7128)
POINT(40.7128 -74.0060)
SRID=4326;POINT(-74.0060 40.7128)

# Decimal degrees  
40.7128, -74.0060
-74.0060, 40.7128
40.7128N 74.0060W

# DMS formats
40°42'46"N 74°00'22"W
40d42m46sN 74d00m22sW
40 42 46 N, 74 00 22 W

# MGRS
18TWL8040944131

# UTM
18N 583960 4507523
583960 4507523 18N

# Plus Codes
87G7QX2F+2X
QX2F+2X New York

# Geohash
dr5regw3p

# GeoJSON
{"type":"Point","coordinates":[-74.0060,40.7128]}
```

### Troubleshooting

**Issue**: Smart Auto-Detect doesn't recognize my coordinates
**Solution**: 
- Check that coordinates are in a supported format
- For decimal degrees, try adding hemisphere indicators (N/S/E/W)
- Verify coordinate values are within valid ranges (lat: -90 to 90, lon: -180 to 180)

**Issue**: Wrong coordinate order interpretation  
**Solution**:
- Check your coordinate order setting in the Settings dialog
- Use unambiguous formats like WKT when precision is critical
- Add directional indicators (N/S/E/W) to decimal degree inputs

**Issue**: Zoom doesn't work as expected
**Solution**:
- Ensure coordinates are valid for your map's coordinate system
- Check that the target location is within your map extent
- Try different zoom scales if the default behavior doesn't suit your needs

## Technical Details

### Smart Parser Logic
The Smart Auto-Detect parser uses a priority-based approach:

1. **Structured Formats** (highest priority): WKT, EWKT, WKB, GeoJSON
2. **Grid Systems**: MGRS, UTM, UPS, Plus Codes
3. **Hash Systems**: Geohash, Maidenhead, H3
4. **Degree Formats**: DMS, decimal degrees (lowest priority due to ambiguity)

### Coordinate Order Handling
- Smart Auto-Detect respects your coordinate order preference setting
- For ambiguous inputs, it tries both orders and uses the one that produces valid results
- Unambiguous formats (like WKT) always use their native coordinate order

### Settings Storage
Settings are stored in QGIS's standard settings system and persist across:
- Plugin reloads
- QGIS restarts  
- QGIS upgrades (settings migrate automatically)

## Compatibility

- **QGIS Version**: Compatible with QGIS 3.x
- **Dependencies**: Uses standard QGIS libraries, no additional packages required
- **Optional Features**: H3 support requires the H3 library (gracefully disabled if not available)

## Development Notes

The enhancements are implemented as separate modules that integrate cleanly with the existing plugin:
- `enhanced_settings.py`: Settings management and Smart Auto-Detect options
- `smart_parser.py`: Coordinate parsing logic
- `text_preservation.py`: Input text preservation functionality  
- `plugin_cleanup.py`: Safe plugin cleanup to prevent QGIS hanging
- `plugin_enhancements.py`: Main coordinator that ties everything together

This modular approach ensures minimal changes to the core plugin code while providing comprehensive new functionality.