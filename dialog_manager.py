"""
Dialog Lifecycle Management - Centralized UI Component Management

Handles creation, configuration, and cleanup of plugin dialogs to reduce
complexity in main plugin class and provide consistent dialog management.

**Architecture Benefits:**
- Lazy loading of dialogs (created only when first accessed)
- Centralized configuration and cleanup
- Consistent dialog lifecycle management
- Reduced complexity in main latLonTools.py class

**Managed Dialogs:**
- SettingsWidget: Plugin configuration dialog
- ZoomToLatLon: Single coordinate zoom dock widget
- MultiZoomWidget: Multi-location zoom dialog
- DigitizerWidget: Point digitizing dialog  
- CoordinateConverterWidget: Coordinate conversion dock widget

**Integration with Main Plugin:**
    # In latLonTools.py __init__()
    from .dialog_manager import DialogManager
    self.dialog_manager = DialogManager(self.iface, self.plugin_dir, self)
    
    # Access dialogs
    self.dialog_manager.show_settings_dialog()
    self.dialog_manager.show_zoom_to_dialog()
    
    # Cleanup on plugin unload
    self.dialog_manager.cleanup_dialogs()

**Memory Management:**
- Automatic cleanup prevents memory leaks
- Lazy loading improves startup performance
- Proper dock widget management

Author: Claude Code (Deep Refactoring Phase 2)
Purpose: Extract dialog management from main plugin class
"""
import processing
from typing import Optional, Dict, Any, TYPE_CHECKING
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDockWidget

if TYPE_CHECKING:
    from qgis.gui import QgsInterface

try:
    from .settings import SettingsWidget
    from .zoomToLatLon import ZoomToLatLon
    from .multizoom import MultiZoomWidget
    from .digitizer import DigitizerWidget
    from .coordinateConverter import CoordinateConverterWidget
except ImportError:
    # Fallback for standalone testing
    from settings import SettingsWidget
    from zoomToLatLon import ZoomToLatLon
    from multizoom import MultiZoomWidget
    from digitizer import DigitizerWidget
    from coordinateConverter import CoordinateConverterWidget


class DialogManager:
    """
    Manages plugin dialog lifecycle and coordination.
    
    Provides centralized management of dialog creation, configuration,
    and cleanup to reduce complexity in main plugin class.
    
    **Design Pattern:** Facade + Lazy Loading
    - Facade: Simplifies dialog access for main plugin
    - Lazy Loading: Dialogs created only when first accessed
    
    **Dialog Categories:**
    1. Settings Dialog: Modal configuration dialog
    2. Dock Widgets: ZoomToLatLon, CoordinateConverter (auto-docked)
    3. Floating Dialogs: MultiZoom, Digitizer (manually positioned)
    
    **Lifecycle Management:**
    - Creation: Lazy properties ensure single instance per dialog
    - Configuration: configure_all_dialogs() updates all instantiated dialogs
    - Cleanup: cleanup_dialogs() handles proper resource deallocation
    
    **Adding New Dialogs:**
    1. Add private _dialog_name attribute in __init__()
    2. Create dialog_name property with lazy loading
    3. Add show_dialog_name() method
    4. Update configure_all_dialogs() if needed
    5. Add to cleanup_dialogs() list
    
    **Thread Safety:**
    - All dialogs created on main UI thread
    - No concurrent access issues (QGIS single-threaded UI)
    """
    
    def __init__(self, iface: "QgsInterface", plugin_dir: str, plugin_instance=None) -> None:
        """
        Initialize dialog manager.
        
        Args:
            iface: QGIS interface object
            plugin_dir: Plugin directory path
            plugin_instance: Main plugin instance (for dialogs that need it)
        """
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.plugin_instance = plugin_instance
        
        # Dialog instances (created on demand)
        self._settings_dialog: Optional[SettingsWidget] = None
        self._zoom_to_dialog: Optional[ZoomToLatLon] = None
        self._multi_zoom_dialog: Optional[MultiZoomWidget] = None
        self._digitizer_dialog: Optional[DigitizerWidget] = None
        self._coordinate_converter_dialog: Optional[CoordinateConverterWidget] = None
    
    @property
    def settings_dialog(self) -> SettingsWidget:
        """Get or create settings dialog (lazy loading).
        
        **Dialog Type:** Modal configuration dialog
        **Lifecycle:** Created once, reused for all settings access
        **Integration:** Used by toolbar settings button and menu items
        """
        if self._settings_dialog is None:
            self._settings_dialog = SettingsWidget(
                self.plugin_instance, 
                self.iface, 
                self.iface.mainWindow()
            )
        return self._settings_dialog
    
    @property  
    def zoom_to_dialog(self) -> ZoomToLatLon:
        """Get or create zoom to coordinate dialog (lazy loading).
        
        **Dialog Type:** Dock widget for single coordinate zoom
        **Lifecycle:** Created once, auto-docked to QGIS interface
        **Integration:** Accessible via toolbar and main menu
        **Location:** Auto-positioned by QGIS dock system
        """
        if self._zoom_to_dialog is None:
            self._zoom_to_dialog = ZoomToLatLon(
                self.plugin_instance, 
                self.iface, 
                self.iface.mainWindow()
            )
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self._zoom_to_dialog)
        return self._zoom_to_dialog
    
    @property
    def multi_zoom_dialog(self) -> MultiZoomWidget:
        """Get or create multi-zoom dialog (lazy loading).
        
        **Dialog Type:** Floating dialog for multiple coordinate zoom
        **Lifecycle:** Created once, initially hidden, set as floating
        **Integration:** Accessed via menu or toolbar
        **Dependency:** Requires settings dialog for configuration
        """
        if self._multi_zoom_dialog is None:
            self._multi_zoom_dialog = MultiZoomWidget(
                self.plugin_instance, 
                self.settings_dialog,  # This will lazily create settings dialog if needed
                self.iface.mainWindow()
            )
            self._multi_zoom_dialog.hide()
            self._multi_zoom_dialog.setFloating(True)
        return self._multi_zoom_dialog
    
    @property
    def digitizer_dialog(self) -> DigitizerWidget:
        """Get or create digitizer dialog (lazy loading)."""
        if self._digitizer_dialog is None:
            self._digitizer_dialog = DigitizerWidget(
                self.iface, 
                self.iface.mainWindow(), 
                self.plugin_dir
            )
        return self._digitizer_dialog
    
    @property
    def coordinate_converter_dialog(self) -> CoordinateConverterWidget:
        """Get or create coordinate converter dialog (lazy loading).
        
        **Dialog Type:** Dock widget for coordinate format conversion
        **Lifecycle:** Created once, auto-docked to QGIS interface  
        **Integration:** Primary coordinate conversion interface
        **Location:** Auto-positioned by QGIS dock system
        """
        if self._coordinate_converter_dialog is None:
            self._coordinate_converter_dialog = CoordinateConverterWidget(
                self.iface, 
                self.iface.mainWindow(), 
                self.plugin_dir
            )
            self.iface.addDockWidget(
                Qt.RightDockWidgetArea, 
                self._coordinate_converter_dialog
            )
        return self._coordinate_converter_dialog
    
    def show_settings_dialog(self) -> None:
        """Show the plugin settings dialog."""
        self.settings_dialog.show()
    
    def show_zoom_to_dialog(self) -> None:
        """Show the zoom to coordinate dialog."""
        self.zoom_to_dialog.show()
    
    def show_coordinate_converter_dialog(self) -> None:
        """Show the coordinate converter dialog."""
        self.coordinate_converter_dialog.show()
    
    def configure_all_dialogs(self) -> None:
        """Configure all instantiated dialogs with current settings.
        
        **When to Call:**
        - After settings changes
        - After plugin initialization
        - When locale/language changes
        
        **Pattern:** Only configures dialogs that have been created
        This prevents unnecessary dialog instantiation during configuration.
        
        **Adding New Dialog Configuration:**
        1. Check if dialog exists (if self._dialog_name is not None)
        2. Call appropriate configuration method on dialog
        3. Handle any configuration exceptions gracefully
        """
        # Only configure dialogs that have been created
        if self._zoom_to_dialog is not None:
            self._zoom_to_dialog.configure()
        if self._multi_zoom_dialog is not None:
            self._multi_zoom_dialog.settingsChanged()
        # Add configuration for other dialogs as needed
    
    def execute_processing_algorithm(self, algorithm_id: str, parameters: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute a processing algorithm with dialog.
        
        **Purpose:** Centralize processing algorithm execution from dialogs
        **Usage:** Called by convenience methods below for specific algorithms
        
        **Algorithm Integration:**
        - Automatically opens QGIS Processing algorithm dialog
        - Pre-populates with provided parameters
        - Handles algorithm registration and availability
        
        **Available Algorithms:** See convenience methods below
        - field2geom: Convert attribute fields to geometry
        - geom2field: Convert geometry to attribute fields  
        - geom2wkt: Convert geometry to WKT format
        - wkt2layers: Create layers from WKT text
        - point2mgrs: Convert points to MGRS coordinates
        - mgrs2point: Convert MGRS to point layer
        - Plus similar algorithms for Plus Codes, ECEF, etc.
        
        Args:
            algorithm_id: Processing algorithm ID (e.g., 'latlontools:field2geom')
            parameters: Optional algorithm parameters
        """
        if parameters is None:
            parameters = {}
        processing.execAlgorithmDialog(algorithm_id, parameters)
    
    # Processing algorithm convenience methods
    def show_field_to_geom_dialog(self) -> None:
        """Show field to geometry conversion dialog."""
        self.execute_processing_algorithm('latlontools:field2geom')
    
    def show_geom_to_field_dialog(self) -> None:
        """Show geometry to field conversion dialog."""
        self.execute_processing_algorithm('latlontools:geom2field')
    
    def show_geom_to_wkt_dialog(self) -> None:
        """Show geometry to WKT conversion dialog."""
        self.execute_processing_algorithm('latlontools:geom2wkt')
    
    def show_wkt_to_layers_dialog(self) -> None:
        """Show WKT to layers conversion dialog."""
        self.execute_processing_algorithm('latlontools:wkt2layers')
    
    def show_to_mgrs_dialog(self) -> None:
        """Show point to MGRS conversion dialog."""
        self.execute_processing_algorithm('latlontools:point2mgrs')
    
    def show_mgrs_to_layer_dialog(self) -> None:
        """Show MGRS to point layer conversion dialog."""
        self.execute_processing_algorithm('latlontools:mgrs2point')
    
    def show_to_plus_codes_dialog(self) -> None:
        """Show point to Plus Codes conversion dialog."""
        self.execute_processing_algorithm('latlontools:point2pluscodes')
    
    def show_plus_codes_to_layer_dialog(self) -> None:
        """Show Plus Codes to point layer conversion dialog."""
        self.execute_processing_algorithm('latlontools:pluscodes2point')
    
    def show_lla_to_ecef_dialog(self) -> None:
        """Show LLA to ECEF conversion dialog."""
        self.execute_processing_algorithm('latlontools:lla2ecef')
    
    def show_ecef_to_lla_dialog(self) -> None:
        """Show ECEF to LLA conversion dialog."""
        self.execute_processing_algorithm('latlontools:ecef2lla')
    
    def cleanup_dialogs(self) -> None:
        """
        Clean up all dialog resources.
        
        **CRITICAL:** Must be called during plugin unload to prevent memory leaks.
        **Called from:** latLonTools.py unload() method
        
        **Cleanup Process:**
        1. Remove dock widgets from QGIS interface
        2. Close all dialogs properly
        3. Clear dialog references
        4. Handle cleanup exceptions gracefully
        
        **Memory Leak Prevention:**
        - Qt parent-child relationships don't auto-cleanup dock widgets
        - QGIS interface holds references to docked widgets
        - Explicit cleanup required for proper resource deallocation
        
        **Error Handling:**
        - Individual dialog cleanup failures don't stop overall cleanup
        - Ensures plugin can be cleanly unloaded even if some dialogs fail
        """
        # MODIFICATION POINT: Add new dialogs to this cleanup list
        # Format: (attribute_name, dialog_instance)
        dialogs_to_cleanup = [
            ('_settings_dialog', self._settings_dialog),
            ('_zoom_to_dialog', self._zoom_to_dialog),
            ('_multi_zoom_dialog', self._multi_zoom_dialog),
            ('_digitizer_dialog', self._digitizer_dialog),
            ('_coordinate_converter_dialog', self._coordinate_converter_dialog)
        ]
        
        for attr_name, dialog in dialogs_to_cleanup:
            if dialog is not None:
                try:
                    # Remove from dock widgets if applicable
                    if isinstance(dialog, QDockWidget) and hasattr(self.iface, 'removeDockWidget'):
                        self.iface.removeDockWidget(dialog)
                    
                    # Close dialog
                    if hasattr(dialog, 'close'):
                        dialog.close()
                    
                    # Clean up reference
                    setattr(self, attr_name, None)
                    
                except Exception:
                    # Continue cleanup even if individual dialog cleanup fails
                    setattr(self, attr_name, None)
    
    def get_dialog_count(self) -> int:
        """
        Get count of instantiated dialogs.
        
        **Purpose:** Debugging and monitoring dialog usage
        **Usage:** Can be called to check plugin memory usage
        
        **Performance Note:**
        Only counts instantiated dialogs (lazy loading means
        unopened dialogs don't contribute to count)
        
        Returns:
            Number of currently instantiated dialogs
        """
        count = 0
        dialogs = [
            self._settings_dialog,
            self._zoom_to_dialog,
            self._multi_zoom_dialog,
            self._digitizer_dialog,
            self._coordinate_converter_dialog
        ]
        
        for dialog in dialogs:
            if dialog is not None:
                count += 1
                
        return count
    
    def are_any_dialogs_visible(self) -> bool:
        """
        Check if any dialogs are currently visible.
        
        **Purpose:** UI state management and user experience
        **Usage:** Can be used to prevent conflicting dialog operations
        
        **Use Cases:**
        - Prevent multiple modal dialogs
        - Check before major UI operations
        - User workflow guidance
        
        Returns:
            True if any dialog is visible
        """
        dialogs = [
            self._settings_dialog,
            self._zoom_to_dialog,
            self._multi_zoom_dialog,
            self._digitizer_dialog,
            self._coordinate_converter_dialog
        ]
        
        for dialog in dialogs:
            if dialog is not None and hasattr(dialog, 'isVisible') and dialog.isVisible():
                return True
                
        return False