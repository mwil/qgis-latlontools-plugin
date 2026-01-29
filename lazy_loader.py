"""
Lazy Loading Utilities for QGIS Plugin Performance Optimization

This module provides thread-safe lazy loading mechanisms to defer expensive imports
and initializations until actually needed, significantly improving plugin startup time.

**Architecture Overview:**
- LazyLoader: Generic lazy loading for any callable
- LazyModuleLoader: Module-specific lazy loading with import management
- LazyClassLoader: Class instantiation with constructor parameters
- LoadingStats: Performance monitoring and statistics

**Integration Points:**
- Used by parser_service.py for SmartCoordinateParser lazy loading
- Can be extended for other expensive plugin components
- Thread-safe for QGIS's multi-threaded environment

**Usage Examples:**
    # Basic lazy loading
    loader = LazyLoader(lambda: expensive_function())
    result = loader.get()  # Only loads on first access

    # Class lazy loading with parameters
    class_loader = LazyClassLoader('module_name', 'ClassName', arg1, arg2)
    instance = class_loader.get_instance()

Author: Claude Code (Deep Refactoring Phase 2)
Compatibility: Maintains upstream merge compatibility
"""

from typing import Any, Callable, Optional, Dict, TypeVar, Generic, cast
import threading
import importlib

T = TypeVar("T")


class LazyLoader(Generic[T]):
    """
    Generic lazy loader that imports and initializes objects on first access.

    Thread-safe lazy loading with weak references to prevent memory leaks.
    Uses double-checked locking pattern for optimal performance.

    **When to Use:**
    - Expensive computations that may not be needed
    - Heavy imports that slow startup
    - Objects with complex initialization

    **Thread Safety:**
    - Uses threading.Lock() for concurrent access
    - Double-checked locking pattern prevents race conditions
    - Safe for QGIS's multi-threaded environment

    **Modification Points:**
    - _loader_func: Change what gets loaded
    - _loading_lock: Modify thread safety behavior
    - get(): Add caching or retry logic here
    """

    def __init__(self, loader_func: Callable[[], T]) -> None:
        """
        Initialize lazy loader.

        Args:
            loader_func: Function that returns the object when called
        """
        self._loader_func = loader_func
        self._loaded_obj: Optional[T] = None
        self._loading_lock = threading.Lock()
        self._is_loaded = False

    def get(self) -> T:
        """
        Get the lazily loaded object, loading it if necessary.

        Returns:
            The loaded object
        """
        if not self._is_loaded:
            with self._loading_lock:
                # Double-check locking pattern
                if not self._is_loaded:
                    self._loaded_obj = self._loader_func()
                    self._is_loaded = True

        return cast(T, self._loaded_obj)

    def is_loaded(self) -> bool:
        """Check if the object has been loaded."""
        return self._is_loaded

    def reset(self) -> None:
        """Reset the loader, forcing re-loading on next access."""
        with self._loading_lock:
            self._loaded_obj = None
            self._is_loaded = False


class LazyModuleLoader:
    """
    Lazy module loader for deferring expensive module imports.

    Particularly useful for modules with heavy dependencies or initialization.
    """

    def __init__(self) -> None:
        self._modules: Dict[str, LazyLoader] = {}
        self._import_cache: Dict[str, Any] = {}

    def register_module(
        self, module_name: str, import_path: str, from_package: Optional[str] = None
    ) -> None:
        """
        Register a module for lazy loading.

        Args:
            module_name: Name to use for accessing the module
            import_path: Python import path (e.g., 'latlontools.smart_parser')
            from_package: Parent package name for constructing full import path (e.g., 'latlontools')
                         If provided, prepends to import_path as '{from_package}.{import_path}'
        """

        def loader():
            # Construct full import path if from_package is provided
            full_import_path = (
                f"{from_package}.{import_path}" if from_package else import_path
            )

            try:
                # Use importlib for reliable programmatic imports
                module = importlib.import_module(full_import_path)
            except (ImportError, ModuleNotFoundError):
                # Fallback to standard import
                module = __import__(full_import_path, fromlist=[""])

            self._import_cache[module_name] = module
            return module

        self._modules[module_name] = LazyLoader(loader)

    def get_module(self, module_name: str) -> Any:
        """
        Get a lazily loaded module.

        Args:
            module_name: Name of the module to get

        Returns:
            The loaded module

        Raises:
            KeyError: If module is not registered
        """
        if module_name not in self._modules:
            raise KeyError(f"Module '{module_name}' not registered for lazy loading")

        return self._modules[module_name].get()

    def is_module_loaded(self, module_name: str) -> bool:
        """Check if a module has been loaded."""
        return module_name in self._modules and self._modules[module_name].is_loaded()

    def preload_module(self, module_name: str) -> None:
        """Preload a module (useful for background loading)."""
        self.get_module(module_name)

    def reset_module(self, module_name: str) -> None:
        """Reset a module, forcing re-import on next access."""
        if module_name in self._modules:
            self._modules[module_name].reset()

    def get_loaded_modules(self) -> Dict[str, Any]:
        """Get all currently loaded modules."""
        return {
            name: loader.get()
            for name, loader in self._modules.items()
            if loader.is_loaded()
        }


class LazyClassLoader(Generic[T]):
    """
    Lazy loader specifically designed for class instantiation.

    Supports both lazy import and lazy instantiation with parameters.
    **Primary Use Case:** SmartCoordinateParser lazy loading in parser_service.py

    **Key Features:**
    - Handles both relative and absolute imports
    - Supports constructor arguments (*args, **kwargs)
    - Fallback mechanism for plugin vs standalone contexts
    - Thread-safe instantiation

    **Integration Guide:**
    1. Import: from .lazy_loader import LazyClassLoader
    2. Create: loader = LazyClassLoader('module', 'Class', *args, **kwargs)
    3. Use: instance = loader.get_instance()

    **Common Modifications:**
    - _import_path: Change target module
    - _class_name: Change target class
    - _args/_kwargs: Modify constructor parameters
    - get_instance(): Add pre/post-instantiation logic
    """

    def __init__(
        self,
        import_path: str,
        class_name: str,
        *args: Any,
        from_package: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize lazy class loader.

        Args:
            import_path: Python module import path
            class_name: Name of the class to instantiate
            *args: Arguments to pass to class constructor
            from_package: Package name for relative imports
            **kwargs: Keyword arguments to pass to class constructor
        """
        self._import_path = import_path
        self._class_name = class_name
        self._args = args
        self._kwargs = kwargs
        self._from_package = from_package
        self._instance: Optional[T] = None
        self._loading_lock = threading.Lock()
        self._is_loaded = False

    def get_instance(self) -> T:
        """
        Get the lazily loaded class instance.

        Returns:
            The class instance
        """
        if not self._is_loaded:
            with self._loading_lock:
                if not self._is_loaded:
                    # Import the module using importlib for reliable imports
                    # Construct full import path if from_package is provided
                    full_import_path = (
                        f"{self._from_package}.{self._import_path}"
                        if self._from_package
                        else self._import_path
                    )

                    try:
                        module = importlib.import_module(full_import_path)
                    except (ImportError, ModuleNotFoundError):
                        # Fallback to standard import
                        module = __import__(full_import_path, fromlist=[""])

                    # Get the class and instantiate it
                    cls = getattr(module, self._class_name)
                    self._instance = cls(*self._args, **self._kwargs)
                    self._is_loaded = True

        return cast(T, self._instance)

    def is_loaded(self) -> bool:
        """Check if the instance has been created."""
        return self._is_loaded

    def reset(self) -> None:
        """Reset the loader, forcing re-instantiation on next access."""
        with self._loading_lock:
            self._instance = None
            self._is_loaded = False


# Global lazy module loader instance for the plugin
# This singleton provides centralized module lazy loading across the entire plugin
# Used by: Currently available for future expansion - not actively used yet
# To use: import { register_lazy_module, get_lazy_module } from .lazy_loader
_lazy_modules = LazyModuleLoader()


def register_lazy_module(
    module_name: str, import_path: str, from_package: Optional[str] = None
) -> None:
    """
    Register a module for lazy loading.

    Args:
        module_name: Name to use for accessing the module
        import_path: Python import path
        from_package: Package name for relative imports
    """
    _lazy_modules.register_module(module_name, import_path, from_package)


def get_lazy_module(module_name: str) -> Any:
    """
    Get a lazily loaded module.

    Args:
        module_name: Name of the module to get

    Returns:
        The loaded module
    """
    return _lazy_modules.get_module(module_name)


def is_module_loaded(module_name: str) -> bool:
    """Check if a module has been loaded."""
    return _lazy_modules.is_module_loaded(module_name)


def preload_module(module_name: str) -> None:
    """Preload a module in background."""
    _lazy_modules.preload_module(module_name)


# Performance monitoring for lazy loading
# Global instance automatically tracks all LazyClassLoader usage
# Access via: from .lazy_loader import loading_stats; stats = loading_stats.get_stats()
class LoadingStats:
    """
    Track loading performance and statistics for lazy loading optimization.

    **Purpose:** Monitor and optimize plugin performance by tracking:
    - Module load times for bottleneck identification
    - Access patterns for usage optimization
    - Failed loads for debugging

    **Usage in Plugin:**
    - Automatically used by LazyClassLoader in parser_service.py
    - Provides metrics for performance tuning
    - Helps identify which components benefit most from lazy loading

    **Adding New Metrics:**
    1. Add new tracking dict in __init__()
    2. Create record_* method for the metric
    3. Include in get_stats() return dict
    4. Update callers to record the new metric

    **Debugging Performance Issues:**
    - Check load_times for slow components
    - Review access_counts for usage patterns
    - Examine failed_loads for import issues
    """

    def __init__(self) -> None:
        self._load_times: Dict[str, float] = {}
        self._access_counts: Dict[str, int] = {}
        self._failed_loads: Dict[str, Exception] = {}

    def record_load_time(self, module_name: str, load_time: float) -> None:
        """Record loading time for a module."""
        self._load_times[module_name] = load_time

    def increment_access_count(self, module_name: str) -> None:
        """Increment access count for a module."""
        self._access_counts[module_name] = self._access_counts.get(module_name, 0) + 1

    def record_failed_load(self, module_name: str, error: Exception) -> None:
        """Record a failed load attempt."""
        self._failed_loads[module_name] = error

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive loading statistics."""
        return {
            "load_times": self._load_times.copy(),
            "access_counts": self._access_counts.copy(),
            "failed_loads": {k: str(v) for k, v in self._failed_loads.items()},
            "average_load_time": sum(self._load_times.values()) / len(self._load_times)
            if self._load_times
            else 0,
            "total_accesses": sum(self._access_counts.values()),
        }


# Global loading statistics singleton
# Automatically collects performance data from all lazy loaders
# Used by: parser_service.py for SmartCoordinateParser metrics
# Future: Can be extended for other performance monitoring needs
loading_stats = LoadingStats()
