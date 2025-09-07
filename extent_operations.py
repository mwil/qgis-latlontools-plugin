"""
Extent and Coordinate Capture Operations - Extracted UI Functionality

Extracted from main LatLonTools class for better separation of concerns
and improved maintainability of extent-related functionality.

**Purpose:** Centralizes all extent and coordinate capture operations that were
scattered throughout the main plugin class, providing a focused interface.

**Core Functionality:**
- Copy map canvas extent to clipboard
- Copy layer extent to clipboard  
- Copy selected features extent to clipboard
- Copy formatted canvas bounds
- Coordinate system transformations
- Extent validation utilities

**Integration with Main Plugin:**
    # In latLonTools.py __init__()
    from .extent_operations import ExtentOperations
    self.extent_ops = ExtentOperations(self.iface, self.settings)
    
    # Usage in toolbar/menu actions
    def copy_canvas_extent(self):
        self.extent_ops.copy_extent()
    
    def copy_layer_extent(self):
        self.extent_ops.copy_layer_extent()

**Clipboard Integration:**
- Uses QApplication.clipboard() for system clipboard access
- Formats extents using existing captureExtent.getExtentString()
- Provides fallback formatting if primary formatting fails

**Coordinate System Support:**
- Automatic CRS detection and transformation
- WGS84 standardization for bounds output
- Handles both geographic and projected coordinate systems

Author: Claude Code (Deep Refactoring Phase 2)
Refactored from: latLonTools.py extent handling methods
"""
from typing import Tuple, Optional, TYPE_CHECKING
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import (
    QgsProject, QgsGeometry, QgsRectangle, QgsCoordinateTransform, 
    QgsWkbTypes, QgsFeature, QgsCoordinateReferenceSystem,
    QgsVectorLayer, Qgis
)

if TYPE_CHECKING:
    from qgis.gui import QgsInterface

try:
    from .util import epsg4326
    from .captureExtent import getExtentString
    from .settings import Settings
except ImportError:
    from util import epsg4326
    from captureExtent import getExtentString
    from settings import Settings


class ExtentOperations:
    """
    Handles extent copying and coordinate capture operations.
    
    Separated from main plugin class to improve maintainability and testability.
    
    **Design Benefits:**
    - Single Responsibility: Only handles extent operations
    - Testability: Can be unit tested independently
    - Maintainability: Isolated from main plugin complexity
    - Reusability: Can be used by different plugin components
    
    **Dependencies:**
    - QgsInterface: For accessing map canvas and active layers
    - Settings: For extent formatting preferences
    - captureExtent.getExtentString(): For consistent extent formatting
    
    **Method Categories:**
    1. Clipboard Operations: copy_extent(), copy_layer_extent(), etc.
    2. Coordinate Utilities: get_canvas_center_coordinate()
    3. Transformation: transform_extent_to_crs()
    4. Validation: validate_extent()
    
    **Adding New Extent Operations:**
    1. Add method following naming pattern: copy_* or get_*
    2. Use _copy_extent_to_clipboard() for consistent clipboard handling
    3. Handle coordinate system transformations appropriately
    4. Include proper error handling and fallbacks
    
    **Error Handling Strategy:**
    - Graceful degradation on transformation failures
    - Fallback to simple extent format if formatting fails
    - Silent failures for clipboard operations (user-friendly)
    """
    
    def __init__(self, iface: "QgsInterface", settings: Settings) -> None:
        """
        Initialize extent operations.
        
        Args:
            iface: QGIS interface object
            settings: Plugin settings object
        """
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settings = settings
    
    def copy_extent(self) -> None:
        """Copy the current map canvas extent to clipboard.
        
        **Primary Use Case:** Copy current map view extent
        **Triggered by:** Toolbar button or menu action
        **Format:** Uses plugin extent formatting settings
        **CRS:** Respects current map canvas CRS
        """
        extent = self.canvas.extent()
        crs = self.canvas.mapSettings().destinationCrs()
        self._copy_extent_to_clipboard(extent, crs)
    
    def copy_layer_extent(self) -> None:
        """Copy the extent of the active layer to clipboard.
        
        **Purpose:** Get full extent of currently selected layer
        **Validation:** Checks for valid active layer before processing
        **CRS:** Uses the layer's native coordinate system
        **Failure Mode:** Silent failure if no active layer
        """
        layer = self.iface.activeLayer()
        if layer is None or not layer.isValid():
            return
            
        extent = layer.extent()
        crs = layer.crs()
        self._copy_extent_to_clipboard(extent, crs)
    
    def copy_selected_features_extent(self) -> None:
        """Copy the extent of selected features to clipboard.
        
        **Purpose:** Get bounding extent of currently selected features
        **Algorithm:** Calculates combined extent using QgsRectangle.combineExtentWith()
        **Validation:** Requires active layer with selected features
        **Geometry Handling:** Safely handles null/invalid geometries
        **Failure Mode:** Silent failure if no selection
        """
        layer = self.iface.activeLayer()
        if layer is None or not layer.isValid():
            return
            
        # Get selected features
        selected_features = layer.selectedFeatures()
        if not selected_features:
            return
            
        # Calculate combined extent of selected features
        extent = QgsRectangle()
        extent.setMinimal()
        
        for feature in selected_features:
            geom = feature.geometry()
            if geom and not geom.isNull():
                bbox = geom.boundingBox()
                if extent.isEmpty():
                    extent = bbox
                else:
                    extent.combineExtentWith(bbox)
        
        if not extent.isEmpty():
            crs = layer.crs()
            self._copy_extent_to_clipboard(extent, crs)
    
    def copy_canvas_bounds(self) -> None:
        """Copy formatted canvas bounds to clipboard.
        
        **Format:** Comma-separated bounds: minX, minY, maxX, maxY
        **CRS:** Always transforms to WGS84 for standardization
        **Precision:** 8 decimal places for high accuracy
        **Use Case:** Standard bounds format for web mapping APIs
        """
        extent = self.canvas.extent()
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        
        # Transform to WGS84 for standard output
        if canvas_crs != epsg4326:
            transform = QgsCoordinateTransform(canvas_crs, epsg4326, QgsProject.instance())
            extent = transform.transformBoundingBox(extent)
            
        # Format as comma-separated bounds: minX, minY, maxX, maxY
        bounds_text = f"{extent.xMinimum():.8f}, {extent.yMinimum():.8f}, {extent.xMaximum():.8f}, {extent.yMaximum():.8f}"
        
        # Copy to system clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(bounds_text)
    
    def _copy_extent_to_clipboard(self, extent: QgsRectangle, crs) -> None:
        """
        Internal method to copy extent to clipboard with proper formatting.
        
        **INTERNAL METHOD:** Used by all public copy_* methods for consistency
        
        **Formatting Strategy:**
        1. Try to use captureExtent.getExtentString() for plugin-consistent formatting
        2. Fall back to simple comma-separated format if formatting fails
        3. Always succeed with clipboard operation (graceful degradation)
        
        **Error Recovery:**
        - Catches all formatting exceptions
        - Provides minimal fallback format
        - Ensures clipboard operation always completes
        
        Args:
            extent: QgsRectangle extent to copy
            crs: Coordinate reference system of the extent
        """
        try:
            # Use the existing getExtentString function for consistent formatting
            extent_string = getExtentString(extent, crs, epsg4326)
            
            # Copy to system clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(extent_string)
            
        except Exception as e:
            # Fallback to simple extent format if formatting fails
            simple_extent = f"{extent.xMinimum()}, {extent.yMinimum()}, {extent.xMaximum()}, {extent.yMaximum()}"
            clipboard = QApplication.clipboard()
            clipboard.setText(simple_extent)
    
    def get_canvas_center_coordinate(self) -> Tuple[float, float]:
        """
        Get the center coordinate of the current map canvas.
        
        **Purpose:** Calculate center point of current map view
        **Algorithm:** Simple midpoint calculation: (min + max) / 2
        **CRS:** Returns coordinates in canvas coordinate system
        **Usage:** Can be used for centering operations or reference points
        
        Returns:
            Tuple of (x, y) coordinates in canvas CRS
        """
        extent = self.canvas.extent()
        center_x = (extent.xMinimum() + extent.xMaximum()) / 2.0
        center_y = (extent.yMinimum() + extent.yMaximum()) / 2.0
        return (center_x, center_y)
    
    def transform_extent_to_crs(
        self, 
        extent: QgsRectangle, 
        source_crs: QgsCoordinateReferenceSystem, 
        target_crs: QgsCoordinateReferenceSystem
    ) -> QgsRectangle:
        """
        Transform extent from source CRS to target CRS.
        
        **Optimization:** Returns original extent if CRS are identical
        **Transformation:** Uses QGIS QgsCoordinateTransform for accuracy
        **Error Handling:** Caller responsible for transformation exceptions
        
        **Use Cases:**
        - Converting layer extents to canvas CRS
        - Standardizing extents to WGS84
        - Preparing extents for external APIs
        
        **Performance Note:**
        QGIS coordinate transformations are expensive - check CRS equality first
        
        Args:
            extent: Source extent to transform
            source_crs: Source coordinate reference system
            target_crs: Target coordinate reference system
            
        Returns:
            Transformed extent in target CRS
        """
        if source_crs == target_crs:
            return extent
            
        transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
        return transform.transformBoundingBox(extent)
    
    def validate_extent(self, extent: QgsRectangle) -> bool:
        """
        Validate that extent is reasonable and not empty.
        
        **Validation Checks:**
        1. Extent exists and is not null
        2. Extent is not empty (has positive area)
        3. Width and height are positive
        4. Dimensions are reasonable for geographic data
        
        **Geographic Bounds Check:**
        - Width < 360 degrees (less than full longitude range)
        - Height < 180 degrees (less than full latitude range)
        - Helps catch obviously invalid extents
        
        **Use Cases:**
        - Validate user input extents
        - Check calculated extents before processing
        - Prevent invalid extent operations
        
        Args:
            extent: Extent to validate
            
        Returns:
            True if extent passes all validation checks
        """
        return (extent and not extent.isEmpty() and 
                extent.width() > 0 and extent.height() > 0 and
                extent.width() < 360 and extent.height() < 180)  # Reasonable geographic bounds check