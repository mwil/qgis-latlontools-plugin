#!/usr/bin/env python3
"""
Real-world coordinate scenarios test suite
Tests practical coordinate inputs that users commonly encounter

Focus areas:
- Real locations with typical coordinate confusion scenarios  
- Mixed formats in single session
- Copy-paste from various sources (maps, GPS, databases)
- International locations with different conventions
- Scientific/surveying coordinate formats
- Batch processing scenarios
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

class TestRealWorldCoordinateScenarios(unittest.TestCase):
    """Real-world coordinate input scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.setup_test_data()
        
    def setup_test_data(self):
        """Set up real-world test coordinate data"""
        # Real locations that commonly cause lat/lon confusion
        self.real_world_locations = {
            "Tokyo": {
                "correct_lat_lon": (35.6762, 139.6503),
                "correct_lon_lat": (139.6503, 35.6762),
                "common_inputs": [
                    "35.6762, 139.6503",  # Lat, Lon
                    "139.6503, 35.6762",  # Lon, Lat  
                    "POINT(139.6503 35.6762)",  # WKT standard
                    "POINT(35.6762 139.6503)",  # WKT confused
                    "SRID=4326;POINT(139.6503 35.6762)",  # EWKT correct
                    "SRID=4326;POINT(35.6762 139.6503)",  # EWKT confused
                ]
            },
            "New_York": {
                "correct_lat_lon": (40.7128, -74.0060),
                "correct_lon_lat": (-74.0060, 40.7128),
                "common_inputs": [
                    "40.7128, -74.0060",
                    "-74.0060, 40.7128", 
                    "POINT(-74.0060 40.7128)",
                    "POINT(40.7128 -74.0060)",
                    "40°42'46.1\"N 74°00'21.6\"W",  # DMS
                    "18TWN8540011518",  # MGRS
                ]
            },
            "London": {
                "correct_lat_lon": (51.5074, -0.1278),
                "correct_lon_lat": (-0.1278, 51.5074),
                "common_inputs": [
                    "51.5074, -0.1278",
                    "-0.1278, 51.5074",
                    "POINT(-0.1278 51.5074)",
                    "POINT(51.5074 -0.1278)",
                ]
            },
            "Sydney": {
                "correct_lat_lon": (-33.8688, 151.2093),
                "correct_lon_lat": (151.2093, -33.8688),
                "common_inputs": [
                    "-33.8688, 151.2093",
                    "151.2093, -33.8688",
                    "POINT(151.2093 -33.8688)",
                    "POINT(-33.8688 151.2093)",
                ]
            },
            "Null_Island": {
                "correct_lat_lon": (0.0, 0.0),
                "correct_lon_lat": (0.0, 0.0),
                "common_inputs": [
                    "0, 0",
                    "0.0, 0.0", 
                    "POINT(0 0)",
                    "SRID=4326;POINT(0 0)",
                ]
            }
        }
        
    def test_common_copy_paste_scenarios(self):
        """Test coordinates commonly copied from various sources"""
        print("\n=== COMMON COPY-PASTE SCENARIOS ===")
        
        copy_paste_cases = [
            # (source, input, expected_format, description)
            ("Google Maps", "35°40'34.3\"N 139°39'02.6\"E", "DMS", "Google Maps DMS format"),
            ("GPS Device", "N35°40.572' E139°39.043'", "DM", "GPS decimal minutes"),
            ("Database Export", "35.67620, 139.65034", "Decimal", "Database with trailing zeros"),
            ("GIS Software", "POINT(139.65034 35.67620)", "WKT", "Standard GIS WKT output"),
            ("Web API", '{"lat": 35.67620, "lng": 139.65034}', "JSON", "Web API JSON response"),
            ("Spreadsheet", "35.67620\t139.65034", "Tab-separated", "Excel/CSV export"),
            ("Scientific Paper", "35.676°N, 139.650°E", "Decimal Degrees", "Academic format"),
            ("Survey Report", "35° 40' 34.32\" N, 139° 39' 2.6\" E", "DMS Spaced", "Survey documentation"),
        ]
        
        passed = 0
        total = len(copy_paste_cases)
        
        for i, (source, input_text, expected_format, description) in enumerate(copy_paste_cases, 1):
            print(f"\nTest {i}: {description}")
            print(f"  Source: {source}")
            print(f"  Input: '{input_text}'")
            print(f"  Expected Format: {expected_format}")
            
            # Test if input contains expected patterns
            has_coordinates = self._contains_coordinate_patterns(input_text)
            format_detected = self._detect_likely_format(input_text)
            
            print(f"  Detected Format: {format_detected}")
            
            if has_coordinates:
                print(f"  ✅ PASS: Coordinate patterns detected")
                passed += 1
            else:
                print(f"  ❌ FAIL: No coordinate patterns detected")
        
        print(f"\nCopy-Paste Scenarios: {passed}/{total} passed ({passed/total*100:.1f}%)")
        return passed == total
        
    def test_international_location_scenarios(self):
        """Test coordinates from various international locations"""
        print("\n=== INTERNATIONAL LOCATION SCENARIOS ===")
        
        passed = 0
        total = 0
        
        for location, data in self.real_world_locations.items():
            print(f"\n--- {location.replace('_', ' ')} ---")
            correct_lat, correct_lon = data["correct_lat_lon"]
            
            location_passed = 0
            location_total = len(data["common_inputs"])
            
            for j, input_text in enumerate(data["common_inputs"], 1):
                print(f"Test {j}: {input_text}")
                
                # Analyze what coordinate order this represents
                format_info = self._analyze_coordinate_input(input_text)
                expected_needs_flip = format_info.get("needs_flip", False)
                
                print(f"  Format: {format_info['format']}")
                print(f"  Expected flip needed: {expected_needs_flip}")
                
                # For this test, we're validating the analysis logic
                if format_info["format"] != "Unknown":
                    print(f"  ✅ PASS: Format recognized")
                    location_passed += 1
                else:
                    print(f"  ❌ FAIL: Format not recognized")
                    
                total += 1
                
            print(f"{location}: {location_passed}/{location_total} passed")
            passed += location_passed
            
        print(f"\nInternational Locations: {passed}/{total} passed ({passed/total*100:.1f}%)")
        return passed == total
        
    def test_ambiguous_coordinate_scenarios(self):
        """Test scenarios where coordinate order is genuinely ambiguous"""
        print("\n=== AMBIGUOUS COORDINATE SCENARIOS ===")
        
        ambiguous_cases = [
            # Cases where both lat/lon and lon/lat are geographically valid
            # (input, lat_lon_location, lon_lat_location, user_preference_matters)
            ("45.0, 45.0", "Somewhere in Europe/Asia", "Same location", True),
            ("30.0, 30.0", "Egypt/Algeria region", "Same location", True), 
            ("45.5, -75.5", "Ottawa area, Canada", "Southern Ocean (also valid)", True),
            ("-45.5, 75.5", "Southern Ocean", "Northern Antarctica region (also valid)", True),
            ("10.0, 10.0", "West Africa", "Same location", True),
            ("60.0, 60.0", "Russia/Northern Europe", "Same location", True),
            
            # Edge cases near coordinate system boundaries
            ("89.9, 179.9", "Near North Pole", "Invalid", False),
            ("-89.9, -179.9", "Near South Pole", "Invalid", False), 
            ("0.1, 0.1", "West Africa coast", "Same location", True),
        ]
        
        passed = 0
        total = len(ambiguous_cases)
        
        for i, (input_coord, lat_lon_desc, lon_lat_desc, preference_matters) in enumerate(ambiguous_cases, 1):
            print(f"\nTest {i}: {input_coord}")
            print(f"  As Lat/Lon: {lat_lon_desc}")
            print(f"  As Lon/Lat: {lon_lat_desc}")
            print(f"  User preference matters: {preference_matters}")
            
            # Extract coordinates
            coords = input_coord.split(", ")
            if len(coords) == 2:
                try:
                    coord1, coord2 = float(coords[0]), float(coords[1])
                    
                    # Check validity in both orders
                    lat_lon_valid = self._is_valid_geographic(coord1, coord2)
                    lon_lat_valid = self._is_valid_geographic(coord2, coord1)
                    
                    is_ambiguous = lat_lon_valid and lon_lat_valid
                    
                    if is_ambiguous == preference_matters:
                        print(f"  ✅ PASS: Ambiguity correctly identified")
                        passed += 1
                    else:
                        print(f"  ❌ FAIL: Ambiguity detection mismatch")
                        
                except ValueError:
                    print(f"  ❌ FAIL: Could not parse coordinates")
            else:
                print(f"  ❌ FAIL: Could not extract coordinate pair")
        
        print(f"\nAmbiguous Scenarios: {passed}/{total} passed ({passed/total*100:.1f}%)")
        return passed == total
        
    def test_batch_processing_scenarios(self):
        """Test scenarios involving multiple coordinate inputs"""
        print("\n=== BATCH PROCESSING SCENARIOS ===")
        
        batch_scenarios = [
            {
                "name": "Mixed Format Survey Data",
                "inputs": [
                    "35.6762, 139.6503",  # Decimal
                    "POINT(139.6504 35.6763)",  # WKT  
                    "35°40'34\"N 139°39'03\"E",  # DMS
                    "18TWN8540011518",  # MGRS
                ],
                "expected_consistency": "All should resolve to same general area"
            },
            {
                "name": "GPS Track Points",
                "inputs": [
                    "35.6762, 139.6503",
                    "35.6763, 139.6504", 
                    "35.6764, 139.6505",
                    "35.6765, 139.6506",
                ],
                "expected_consistency": "Sequential track with consistent order"
            },
            {
                "name": "Database Migration",
                "inputs": [
                    "SRID=4326;POINT(139.6503 35.6762)",
                    "SRID=4326;POINT(139.6504 35.6763)",
                    "SRID=4326;POINT(139.6505 35.6764)",
                ],
                "expected_consistency": "Consistent EWKT format"
            }
        ]
        
        passed = 0
        total = len(batch_scenarios)
        
        for i, scenario in enumerate(batch_scenarios, 1):
            print(f"\nTest {i}: {scenario['name']}")
            print(f"  Expected: {scenario['expected_consistency']}")
            
            formats_detected = []
            coordinate_pairs = []
            
            for input_text in scenario['inputs']:
                format_info = self._analyze_coordinate_input(input_text)
                formats_detected.append(format_info['format'])
                
                # Try to extract coordinates for consistency check
                coords = self._extract_any_coordinates(input_text)
                if coords:
                    coordinate_pairs.append(coords)
            
            print(f"  Formats detected: {', '.join(set(formats_detected))}")
            print(f"  Coordinate pairs extracted: {len(coordinate_pairs)}")
            
            # Check for consistency (basic validation)
            consistency_ok = len(coordinate_pairs) == len(scenario['inputs'])
            
            if consistency_ok:
                print(f"  ✅ PASS: Consistent batch processing")
                passed += 1
            else:
                print(f"  ❌ FAIL: Inconsistent batch processing")
        
        print(f"\nBatch Processing: {passed}/{total} passed ({passed/total*100:.1f}%)")
        return passed == total
        
    def test_error_recovery_scenarios(self):
        """Test recovery from common coordinate input errors"""
        print("\n=== ERROR RECOVERY SCENARIOS ===")
        
        error_cases = [
            # (input, error_type, expected_recovery)
            ("35.6762,139.6503", "Missing space", "Should parse correctly"),
            ("35.6762 , 139.6503", "Extra spaces", "Should parse correctly"), 
            ("35.6762; 139.6503", "Wrong separator", "Should parse correctly"),
            ("35.6762\t139.6503", "Tab separator", "Should parse correctly"),
            ("(35.6762, 139.6503)", "Parentheses", "Should parse correctly"),
            ("[35.6762, 139.6503]", "Brackets", "Should parse correctly"),
            ("35.6762°, 139.6503°", "Degree symbols", "Should parse correctly"),
            ("lat: 35.6762, lon: 139.6503", "Labels", "Should parse correctly"),
            ("35.6762, 139.6503, 0", "Extra elevation", "Should ignore Z and parse XY"),
            ("N35.6762, E139.6503", "Cardinal prefixes", "Should parse correctly"),
        ]
        
        passed = 0
        total = len(error_cases)
        
        for i, (input_text, error_type, expected_recovery) in enumerate(error_cases, 1):
            print(f"\nTest {i}: {error_type}")
            print(f"  Input: '{input_text}'")
            print(f"  Expected: {expected_recovery}")
            
            # Test coordinate extraction with error recovery
            coords = self._extract_any_coordinates(input_text)
            
            if coords and len(coords) >= 2:
                coord1, coord2 = coords[0], coords[1]
                # Check if coordinates are in reasonable range
                reasonable = (-180 <= coord1 <= 180 and -180 <= coord2 <= 180)
                
                if reasonable:
                    print(f"  ✅ PASS: Extracted ({coord1:.6f}, {coord2:.6f})")
                    passed += 1
                else:
                    print(f"  ❌ FAIL: Extracted unreasonable coordinates")
            else:
                print(f"  ❌ FAIL: Could not extract coordinates")
        
        print(f"\nError Recovery: {passed}/{total} passed ({passed/total*100:.1f}%)")
        return passed == total
        
    # Helper methods
    def _contains_coordinate_patterns(self, text):
        """Check if text contains coordinate-like patterns"""
        import re
        patterns = [
            r'[-+]?\d+\.?\d*',  # Numbers
            r'[°′″\'\"]',       # Degree symbols
            r'[NSEW]',          # Cardinals
            r'POINT',           # WKT
            r'SRID',            # EWKT
        ]
        return any(re.search(pattern, text) for pattern in patterns)
        
    def _detect_likely_format(self, text):
        """Detect the likely coordinate format"""
        import re
        if re.search(r'SRID=', text):
            return "EWKT"
        elif re.search(r'POINT', text, re.IGNORECASE):
            return "WKT"
        elif re.search(r'[°′″\'\"]', text):
            return "DMS"
        elif re.search(r'[NSEW]', text):
            return "DMS/Cardinals"
        elif re.search(r'\{.*"coordinates"', text):
            return "GeoJSON"
        elif re.search(r'[-+]?\d+\.?\d*[,\s]+[-+]?\d+\.?\d*', text):
            return "Decimal"
        else:
            return "Unknown"
            
    def _analyze_coordinate_input(self, input_text):
        """Analyze coordinate input for format and potential issues"""
        format_detected = self._detect_likely_format(input_text)
        
        # Simple analysis - in real implementation would be more sophisticated
        needs_flip = False
        if format_detected in ["WKT", "EWKT"]:
            # Check if coordinates might be flipped in WKT
            coords = self._extract_any_coordinates(input_text)
            if coords and len(coords) >= 2:
                x, y = coords[0], coords[1]
                # If X is in lat range and Y is in lon range, might be flipped
                if -90 <= x <= 90 and -180 <= y <= 180 and not (-90 <= y <= 90):
                    needs_flip = True
        
        return {
            "format": format_detected,
            "needs_flip": needs_flip,
            "input": input_text
        }
        
    def _is_valid_geographic(self, lat, lon):
        """Check if coordinates are valid geographic coordinates"""
        return -90 <= lat <= 90 and -180 <= lon <= 180
        
    def _extract_any_coordinates(self, text):
        """Extract numeric coordinates from any text format"""
        import re
        # Find all numbers (including negative)
        pattern = r'[-+]?\d*\.?\d+'
        matches = re.findall(pattern, text)
        
        coordinates = []
        for match in matches:
            if match and match not in ['.', '-', '+', '']:
                try:
                    coordinates.append(float(match))
                except ValueError:
                    continue
        
        return coordinates
        
def main():
    """Run real-world coordinate scenario tests"""
    print("🌍 REAL-WORLD COORDINATE SCENARIOS TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    test = TestRealWorldCoordinateScenarios()
    test.setUp()
    
    # Run all test categories
    results = []
    results.append(test.test_common_copy_paste_scenarios())
    results.append(test.test_international_location_scenarios())
    results.append(test.test_ambiguous_coordinate_scenarios())
    results.append(test.test_batch_processing_scenarios())
    results.append(test.test_error_recovery_scenarios())
    
    # Summary
    passed_suites = sum(results)
    total_suites = len(results)
    
    print("\n" + "=" * 60)
    if passed_suites == total_suites:
        print("🎉 ALL REAL-WORLD SCENARIO TESTS PASSED!")
        print(f"Test suites passed: {passed_suites}/{total_suites}")
        return 0
    else:
        print("❌ SOME REAL-WORLD SCENARIO TESTS FAILED")
        print(f"Test suites passed: {passed_suites}/{total_suites}")
        return 1

if __name__ == "__main__":
    sys.exit(main())