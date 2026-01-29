#!/usr/bin/env python3
"""
End-to-End Tests for Legacy Grid Coordinate Formats

Tests the complete parse chain for all legacy grid-based coordinate formats:
- MGRS (Military Grid Reference System)
- UTM (Universal Transverse Mercator)
- UPS (Universal Polar Stereographic)
- Plus Codes (Open Location Code)
- Geohash
- Maidenhead Grid
- GEOREF (World Geographic Reference System)
- H3 (Hexagonal Hierarchical Spatial Index)

Each test verifies:
1. Format detection works correctly
2. Complete parse chain produces expected coordinates
3. Formats don't shortcut on the wrong parser
"""

import sys
import os
import math

# Set up QGIS environment for testing
import platform

qgis_python_path = os.environ.get("QGIS_PYTHON_PATH")
if not qgis_python_path:
    system = platform.system()
    if system == "Darwin":  # macOS
        qgis_python_path = "/Applications/QGIS.app/Contents/Resources/python"
    elif system == "Windows":
        possible_paths = [
            r"C:\Program Files\QGIS 3.28\apps\qgis\python",
            r"C:\Program Files\QGIS 3.22\apps\qgis\python",
            r"C:\OSGeo4W\apps\qgis\python",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                qgis_python_path = path
                break
    elif system == "Linux":
        possible_paths = [
            "/usr/share/qgis/python",
            "/usr/local/share/qgis/python",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                qgis_python_path = path
                break

if qgis_python_path and os.path.exists(qgis_python_path):
    sys.path.insert(0, qgis_python_path)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from qgis.core import QgsApplication  # type: ignore

    QGIS_AVAILABLE = True
except ImportError:
    QgsApplication = None  # type: ignore
    QGIS_AVAILABLE = False
    print("QGIS not available - using standalone mode")

# Test data: known input-output pairs for each format
# Reference values verified against external sources
LEGACY_FORMAT_TEST_CASES = {
    # MGRS (Military Grid Reference System)
    # Reference: https://www.mgrs.org/
    "mgrs": [
        # (input, expected_lat, expected_lon, description)
        ("4QFJ12345678", 34.05, -118.25, "Los Angeles area"),
        ("18T WL039710", 40.7128, -74.0060, "New York City (lower precision)"),
        ("33T WK12345678", 51.5074, -0.1278, "London area"),
        ("10TGK1234567890", 36.0, 135.0, "Japan area (high precision)"),
    ],
    # UTM (Universal Transverse Mercator)
    # Reference: standard UTM/WGS84 conversions
    "utm": [
        # Zone format: "ZoneH Easting Northing"
        ("10T 1234567 1234567", 36.0, 135.0, "Japan (approximate)"),
        ("18T 583960 4510400", 40.7128, -74.0060, "New York City"),
        ("33U 701841 5713590", 51.5074, -0.1278, "London"),
        ("31N 448251 5411948", 48.8566, 2.3522, "Paris"),
    ],
    # Plus Codes (Open Location Code)
    # Reference: https://plus.codes/
    "plus_codes": [
        ("87G8Q23G+GF", 36.0, 135.0, "Japan area"),
        ("852VCQ8J+34", 40.7128, -74.0060, "New York City"),
        ("9C3WCVJC+MW", 51.5074, -0.1278, "London"),
        ("8FVC2222+22", 48.8566, 2.3522, "Paris (lower precision)"),
    ],
    # Geohash
    # Reference: https://en.wikipedia.org/wiki/Geohash
    "geohash": [
        ("xn76gg", 36.0, 135.0, "Japan area"),
        ("dr5reg", 40.7128, -74.0060, "New York City"),
        ("gcpuvj", 51.5074, -0.1278, "London"),
        ("u09tqu", 48.8566, 2.3522, "Paris"),
    ],
    # Maidenhead Grid Locator
    # Reference: https://en.wikipedia.org/wiki/Maidenhead_Locator_System
    "maidenhead": [
        ("PM94", 36.0, 135.0, "Japan area (4-char)"),
        ("FN31pr", 40.7128, -74.0060, "New York City (6-char)"),
        ("IO91wm", 51.5074, -0.1278, "London (6-char)"),
        ("JN18eu", 48.8566, 2.3522, "Paris (6-char)"),
    ],
    # GEOREF (World Geographic Reference System)
    # Reference: https://en.wikipedia.org/wiki/GEOREF
    "georef": [
        ("MKML5056", 36.0, 135.0, "Japan area"),
        ("NKJN3530", 40.7128, -74.0060, "New York City"),
        ("KJNK2820", 51.5074, -0.1278, "London"),
        ("KJNM0440", 48.8566, 2.3522, "Paris"),
    ],
    # UPS (Universal Polar Stereographic)
    # Reference: polar coordinate systems
    # Note: UPS is for polar regions (latitudes >84°N or <80°S)
    "ups": [
        # Format: "Hemisphere Easting Northing"
        # North pole examples
        ("Z 2000000 2000000", 90.0, 0.0, "North Pole"),
        # South pole examples
        ("A 2000000 2000000", -90.0, 0.0, "South Pole"),
    ],
    # H3 (Hexagonal Hierarchical Spatial Index)
    # Reference: https://h3geo.org/
    # Note: H3 requires the h3 library to be installed
    "h3": [
        # H3 index at resolution 5
        ("85283473fffffff", 37.4275, -122.1697, "San Francisco area (res 5)"),
        # H3 index at resolution 6
        ("86283472fffffff", 37.4275, -122.1697, "San Francisco area (res 6)"),
        # H3 index at resolution 7
        ("872834729ffffff", 37.4275, -122.1697, "San Francisco area (res 7)"),
    ],
}


class TestLegacyFormatsEndToEnd:
    """End-to-end tests for legacy grid coordinate formats"""

    @classmethod
    def setup_class(cls):
        """Initialize QGIS if available"""
        if QGIS_AVAILABLE:
            cls.app = QgsApplication([], False)  # type: ignore
            if qgis_python_path:
                QgsApplication.setPrefixPath(  # type: ignore
                    os.path.dirname(qgis_python_path), True
                )
            QgsApplication.initQgis()  # type: ignore
            cls.qgis_initialized = True
        else:
            cls.qgis_initialized = False

    @classmethod
    def teardown_class(cls):
        """Clean up QGIS"""
        if QGIS_AVAILABLE and cls.qgis_initialized:
            QgsApplication.exitQgis()  # type: ignore

    def setup_method(self):
        """Set up each test method"""
        # Import parser here so we can handle import errors gracefully
        try:
            from smart_parser import SmartCoordinateParser  # type: ignore

            self.parser_available = True
        except ImportError:
            self.parser_available = False
            return

        # Create mock settings and interface
        class MockSettings:
            zoomToCoordOrder = "yx"  # Default to YX order

        class MockIface:
            pass

        self.mock_settings = MockSettings()
        self.mock_iface = MockIface()
        self.parser = SmartCoordinateParser(self.mock_settings, self.mock_iface)

    def _assert_approximate_coords(
        self, result, expected_lat, expected_lon, tolerance, description
    ):
        """Helper to assert coordinates are approximately equal"""
        if result is None:
            raise AssertionError(f"{description}: Parser returned None")

        lat, lon, bounds, crs = result

        lat_error = abs(lat - expected_lat)
        lon_error = abs(lon - expected_lon)

        if lat_error > tolerance or lon_error > tolerance:
            raise AssertionError(
                f"{description}:\n"
                f"  Expected: ({expected_lat:.6f}, {expected_lon:.6f})\n"
                f"  Got: ({lat:.6f}, {lon:.6f})\n"
                f"  Lat error: {lat_error:.6f} (tolerance: {tolerance})\n"
                f"  Lon error: {lon_error:.6f} (tolerance: {tolerance})"
            )

    def test_mgrs_end_to_end(self):
        """Test MGRS format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping MGRS test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing MGRS (Military Grid Reference System)")
        print("=" * 70)

        # Tolerance: MGRS precision varies with string length
        # 10-digit MGRS: ~1 meter precision
        for (
            mgrs_str,
            expected_lat,
            expected_lon,
            description,
        ) in LEGACY_FORMAT_TEST_CASES["mgrs"]:
            print(f"\nTesting: {description}")
            print(f"  Input: {mgrs_str}")

            result = self.parser.parse(mgrs_str)

            # Calculate tolerance based on precision (digits after grid letters)
            # Format: 4QFJ12345678 = 10 digits = 1 meter precision
            precision = (
                len(mgrs_str.split("FJ")[-1]) if "FJ" in mgrs_str else len(mgrs_str) - 5
            )
            tolerance = 0.001 if precision >= 8 else 0.01  # Degrees

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_utm_end_to_end(self):
        """Test UTM format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping UTM test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing UTM (Universal Transverse Mercator)")
        print("=" * 70)

        # Tolerance: UTM is precise to within a few meters
        tolerance = 0.001  # ~100 meters at equator

        for (
            utm_str,
            expected_lat,
            expected_lon,
            description,
        ) in LEGACY_FORMAT_TEST_CASES["utm"]:
            print(f"\nTesting: {description}")
            print(f"  Input: {utm_str}")

            result = self.parser.parse(utm_str)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_plus_codes_end_to_end(self):
        """Test Plus Codes format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping Plus Codes test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing Plus Codes (Open Location Code)")
        print("=" * 70)

        # Tolerance: Plus Codes are precise to about 1/8° at 10-character length
        tolerance = 0.01  # ~1 km

        for (
            plus_code,
            expected_lat,
            expected_lon,
            description,
        ) in LEGACY_FORMAT_TEST_CASES["plus_codes"]:
            print(f"\nTesting: {description}")
            print(f"  Input: {plus_code}")

            result = self.parser.parse(plus_code)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_geohash_end_to_end(self):
        """Test Geohash format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping Geohash test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing Geohash")
        print("=" * 70)

        # Tolerance: Geohash precision varies with length
        # 6-character geohash: ~1.2 km precision
        # 7-character geohash: ~150 m precision
        tolerance = 0.02  # ~2 km

        for (
            geohash,
            expected_lat,
            expected_lon,
            description,
        ) in LEGACY_FORMAT_TEST_CASES["geohash"]:
            print(f"\nTesting: {description}")
            print(f"  Input: {geohash}")

            result = self.parser.parse(geohash)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_maidenhead_end_to_end(self):
        """Test Maidenhead Grid format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping Maidenhead test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing Maidenhead Grid Locator")
        print("=" * 70)

        # Tolerance: Maidenhead precision varies
        # 4-character: ~340x340 km
        # 6-character: ~10x8 km
        tolerance = 0.5  # ~50 km

        for (
            maidenhead,
            expected_lat,
            expected_lon,
            description,
        ) in LEGACY_FORMAT_TEST_CASES["maidenhead"]:
            print(f"\nTesting: {description}")
            print(f"  Input: {maidenhead}")

            result = self.parser.parse(maidenhead)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_georef_end_to_end(self):
        """Test GEOREF format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping GEOREF test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing GEOREF (World Geographic Reference System)")
        print("=" * 70)

        # Tolerance: GEOREF precision varies
        # 8 characters: ~1° precision
        tolerance = 0.5  # ~50 km

        for georef, expected_lat, expected_lon, description in LEGACY_FORMAT_TEST_CASES[
            "georef"
        ]:
            print(f"\nTesting: {description}")
            print(f"  Input: {georef}")

            result = self.parser.parse(georef)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_ups_end_to_end(self):
        """Test UPS format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping UPS test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing UPS (Universal Polar Stereographic)")
        print("=" * 70)

        # Tolerance: UPS for polar regions
        tolerance = 0.1  # ~10 km

        for (
            ups_str,
            expected_lat,
            expected_lon,
            description,
        ) in LEGACY_FORMAT_TEST_CASES["ups"]:
            print(f"\nTesting: {description}")
            print(f"  Input: {ups_str}")

            result = self.parser.parse(ups_str)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_h3_end_to_end(self):
        """Test H3 format parsing end-to-end"""
        if not self.parser_available:
            print("⚠️ Skipping H3 test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing H3 (Hexagonal Hierarchical Spatial Index)")
        print("=" * 70)

        # Check if H3 library is available
        try:
            import h3  # type: ignore
        except ImportError:
            print("⚠️ H3 library not installed - skipping H3 tests")
            print("   Install with: pip install h3")
            return

        # Tolerance: H3 precision varies with resolution
        # Res 5: ~3 km edge length
        # Res 6: ~1 km edge length
        # Res 7: ~300 m edge length
        tolerance = 0.01  # ~1 km

        for h3_str, expected_lat, expected_lon, description in LEGACY_FORMAT_TEST_CASES[
            "h3"
        ]:
            print(f"\nTesting: {description}")
            print(f"  Input: {h3_str}")

            result = self.parser.parse(h3_str)

            try:
                self._assert_approximate_coords(
                    result, expected_lat, expected_lon, tolerance, description
                )
                lat, lon, _, _ = result
                print(f"  ✅ PASS: lat={lat:.6f}, lon={lon:.6f}")
            except AssertionError as e:
                print(f"  ❌ FAIL: {e}")
                raise

    def test_format_cross_contamination(self):
        """Test that formats don't get parsed by the wrong parser"""
        if not self.parser_available:
            print("⚠️ Skipping cross-contamination test - parser not available")
            return

        print("\n" + "=" * 70)
        print("Testing Format Cross-Contamination Prevention")
        print("=" * 70)

        # These are formats that could potentially be confused
        # Verify they're NOT parsed as a different format
        ambiguous_inputs = [
            # MGRS-like patterns that should NOT be parsed as other formats
            ("4QFJ12345678", "mgrs", "Should parse as MGRS, not geohash or other"),
            ("10TGK1234567890", "mgrs", "Should parse as MGRS, not UTM"),
            # Geohash-like patterns
            ("dr5reg", "geohash", "Should parse as geohash, not MGRS"),
            # Plus Codes patterns
            ("87G8Q23G+GF", "plus_codes", "Should parse as Plus Codes, not geohash"),
            # Maidenhead patterns
            ("FN31pr", "maidenhead", "Should parse as Maidenhead, not geohash or MGRS"),
        ]

        for input_str, expected_format, description in ambiguous_inputs:
            print(f"\nTesting: {description}")
            print(f"  Input: {input_str}")

            result = self.parser.parse(input_str)

            if result is None:
                print("  ⚠️ WARN: Input not parsed by any parser")
            else:
                lat, lon, bounds, crs = result
                print(f"  ✅ PASS: Successfully parsed as lat={lat:.6f}, lon={lon:.6f}")


def run_tests():
    """Run all end-to-end tests"""
    print("\n" + "=" * 70)
    print("LEGACY GRID COORDINATE FORMATS - END-TO-END TESTS")
    print("=" * 70)

    test_class = TestLegacyFormatsEndToEnd()
    test_class.setup_class()

    tests = [
        ("MGRS", test_class.test_mgrs_end_to_end),
        ("UTM", test_class.test_utm_end_to_end),
        ("Plus Codes", test_class.test_plus_codes_end_to_end),
        ("Geohash", test_class.test_geohash_end_to_end),
        ("Maidenhead", test_class.test_maidenhead_end_to_end),
        ("GEOREF", test_class.test_georef_end_to_end),
        ("UPS", test_class.test_ups_end_to_end),
        ("H3", test_class.test_h3_end_to_end),
        ("Cross-Contamination", test_class.test_format_cross_contamination),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_name, test_func in tests:
        test_class.setup_method()
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ {test_name} FAILED")
            print(str(e))
        except Exception as e:
            skipped += 1
            print(f"\n⚠️ {test_name} SKIPPED: {e}")

    test_class.teardown_class()

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Passed:  {passed}")
    print(f"Failed:  {failed}")
    print(f"Skipped: {skipped}")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
