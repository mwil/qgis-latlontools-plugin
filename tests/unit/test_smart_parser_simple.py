#!/usr/bin/env python3
"""
Simple Smart Parser test without complex QGIS mocking
Tests the core parsing logic patterns
"""

import sys
import os

def test_basic_patterns():
    """Test basic pattern detection without full parser"""
    import re
    
    print("=== SMART PARSER PATTERN TESTS ===")
    
    # Test coordinate patterns used by smart parser
    test_cases = [
        # (input, expected_pattern_match, description)
        ("40.7128, -74.0060", r'[-+]?\d*\.?\d+', "Decimal coordinates"),
        ("SRID=4326;POINT(-74.0 40.7)", r'SRID=\d+;', "EWKT format"),
        ("POINT(-74.0 40.7)", r'POINT[ZM]*\s*\(', "WKT format"), 
        ("18TWN8540011518", r'\d{1,2}[A-Z]{3}\d+', "MGRS format"),
        ("87G7X2VV+2V", r'[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,}', "Plus Codes"),
        ("JO65HA", r'^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$', "Maidenhead"),
        ("dr5regy", r'^[0-9bcdefghjkmnpqrstuvwxyz]+$', "Geohash"),
        ("GJPJ0615", r'^[A-Z]{4}\d{2,}$', "GEOREF"),
        ("40°42'46.1\"N 74°00'21.6\"W", r'[°′″\'"]', "DMS symbols"),
        ("40.7128° -74.0060°", r'[\d.]+\s*[°]\s*[\d.-]+\s*[°]', "Degree symbols"),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, (input_text, pattern, description) in enumerate(test_cases, 1):
        print(f"\nTest {i}: {description}")
        print(f"  Input: '{input_text}'")
        print(f"  Pattern: {pattern}")
        
        if pattern == r'[-+]?\d*\.?\d+':
            # Special case for number extraction
            numbers = re.findall(pattern, input_text)
            match = len(numbers) >= 2
            if match:
                coord1, coord2 = float(numbers[0]), float(numbers[1])
                valid_coords = (-90 <= coord1 <= 90 and -180 <= coord2 <= 180) or \
                              (-90 <= coord2 <= 90 and -180 <= coord1 <= 180)
                match = valid_coords
        elif pattern == r'^[A-R]{2}\d{2}([A-X]{2}(\d{2})?)?$':
            # Maidenhead pattern check
            match = re.match(pattern, input_text.upper())
        elif pattern == r'^[0-9bcdefghjkmnpqrstuvwxyz]+$':
            # Geohash pattern with length check
            match = re.match(pattern, input_text.lower()) and 3 <= len(input_text) <= 12
        else:
            # Regular pattern matching
            match = re.search(pattern, input_text, re.IGNORECASE)
        
        if match:
            print(f"  ✅ PASS")
            passed += 1
        else:
            print(f"  ❌ FAIL")
    
    print(f"\n=== RESULTS ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All pattern tests passed!")
        return True
    else:
        print("⚠️ Some pattern tests failed")
        return False

def test_coordinate_validation():
    """Test coordinate validation logic"""
    
    print("\n=== COORDINATE VALIDATION TESTS ===")
    
    validation_cases = [
        # (coord1, coord2, expected_valid, description)
        (40.7128, -74.0060, True, "NYC coordinates"),
        (-74.0060, 40.7128, True, "NYC flipped (both valid)"),
        (90.0, 180.0, True, "Extreme valid coordinates"),
        (-90.0, -180.0, True, "Extreme negative coordinates"),
        (91.0, 181.0, False, "Both coordinates invalid"),
        (0.0, 181.0, False, "Invalid longitude > 180"),
        (0.0, 0.0, True, "Origin coordinates"),
        (45.0, 45.0, True, "Equal ambiguous coordinates"),
    ]
    
    def validate_coordinates(coord1, coord2):
        """Simple coordinate validation - both orders must be valid"""
        lat_lon_valid = -90 <= coord1 <= 90 and -180 <= coord2 <= 180
        lon_lat_valid = -90 <= coord2 <= 90 and -180 <= coord1 <= 180
        # For invalid cases, both orders should be invalid
        return lat_lon_valid or lon_lat_valid
    
    passed = 0
    total = len(validation_cases)
    
    for i, (coord1, coord2, expected, description) in enumerate(validation_cases, 1):
        result = validate_coordinates(coord1, coord2)
        
        print(f"\nTest {i}: {description}")
        print(f"  Input: ({coord1}, {coord2})")
        print(f"  Expected: {'Valid' if expected else 'Invalid'}")
        print(f"  Result: {'Valid' if result else 'Invalid'}")
        
        if result == expected:
            print(f"  ✅ PASS")
            passed += 1
        else:
            print(f"  ❌ FAIL")
    
    print(f"\n=== RESULTS ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All validation tests passed!")
        return True
    else:
        print("⚠️ Some validation tests failed")
        return False

def main():
    """Run all simple parser tests"""
    print("🧪 SMART PARSER SIMPLE TESTS")
    print("=" * 50)
    
    pattern_success = test_basic_patterns()
    validation_success = test_coordinate_validation()
    
    overall_success = pattern_success and validation_success
    
    print("\n" + "=" * 50)
    if overall_success:
        print("🎉 ALL SIMPLE TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())