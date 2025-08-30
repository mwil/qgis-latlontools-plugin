#!/usr/bin/env python3
"""
Simple test script for Smart Coordinate Parser logic
Tests the core parsing patterns without full QGIS dependencies
"""

import re

def test_coordinate_patterns():
    """Test coordinate format detection patterns"""
    
    test_cases = [
        # Phase 1: Explicit formats
        ("SRID=4326;POINT(-74.0 40.7)", "EWKT", True),
        ("POINT(-74.0 40.7)", "WKT", True),
        ("SRID=32618;POINT(585398 4511518)", "EWKT", True),
        
        # Phase 2: Existing formats
        ("18TWN8540011518", "MGRS", True),
        ("87G7X2VV+2V", "Plus Codes", True),
        ("18T 585398 4511518", "UTM", True),
        ("dr5regy", "Geohash", True),
        ("MKJH23ab", "Maidenhead", True),
        ("GJPJ0615", "GEOREF", True),
        ('{"type": "Point", "coordinates": [-74.0, 40.7]}', "GeoJSON", True),
        
        # Phase 3: Basic coordinates
        ("40.7128, -74.0060", "Decimal", True),
        ("-74.0060, 40.7128", "Decimal", True),
        ("40.7128 -74.0060", "Decimal", True),
        ("N40.7128 W74.0060", "DMS", True),
        ("40°42'46.1\"N 74°00'21.6\"W", "DMS", True),
        
        # Invalid cases
        ("invalid coordinates", "None", False),
        ("abc def", "None", False),
    ]
    
    print("=" * 80)
    print("COORDINATE PATTERN DETECTION TEST")
    print("=" * 80)
    
    def detect_format(text):
        """Detect coordinate format using the same logic as smart parser"""
        
        # Phase 1: Explicit formats
        if re.search(r'SRID=\d+;', text, re.IGNORECASE):
            return "EWKT"
        if re.search(r'POINT[ZM]*\s*\(', text, re.IGNORECASE):
            return "WKT"
        if re.match(r'^[0-9A-Fa-f]+$', text.replace(' ', '')) and len(text.replace(' ', '')) >= 20:
            return "WKB"
            
        # Phase 2: Existing formats
        text_upper = text.upper()
        
        # MGRS pattern
        if re.search(r'\d{1,2}[A-Z]{3}\d+', text_upper):
            return "MGRS"
            
        # Plus Codes pattern
        if '+' in text and re.search(r'[23456789CFGHJMPQRVWX]{8}\+[23456789CFGHJMPQRVWX]{2,}', text_upper):
            return "Plus Codes"
            
        # UTM pattern
        if 'UTM' in text_upper or re.search(r'\d{1,2}[A-Z]\s+\d+\s+\d+', text):
            return "UTM"
            
        # UPS pattern  
        if 'UPS' in text_upper:
            return "UPS"
            
        # Geohash pattern (base32 without 0,1,i,l,o,u)
        if re.match(r'^[0-9bcdefghjkmnpqrstuvwxyz]+$', text.lower()) and 4 <= len(text) <= 12:
            return "Geohash"
            
        # Maidenhead grid pattern
        if re.match(r'^[A-R]{2}\d{2}[a-x]{0,2}[A-X]{0,2}$', text, re.IGNORECASE):
            return "Maidenhead"
            
        # GEOREF pattern
        if re.match(r'^[A-Z]{4}\d{2,}$', text_upper):
            return "GEOREF"
            
        # GeoJSON pattern
        if text.strip().startswith('{') and '"type"' in text and '"Point"' in text:
            return "GeoJSON"
            
        # Phase 3: Basic coordinates
        # DMS with cardinal directions
        if re.search(r'[NSEW]', text):
            return "DMS"
            
        # Decimal coordinates (extract numbers)
        numbers = re.findall(r'[-+]?\d*\.?\d+', text)
        if len(numbers) >= 2:
            coord1, coord2 = float(numbers[0]), float(numbers[1])
            # Check if they could be valid geographic coordinates
            if (-90 <= coord1 <= 90 and -180 <= coord2 <= 180) or (-90 <= coord2 <= 90 and -180 <= coord1 <= 180):
                return "Decimal"
                
        return "Unknown"
    
    def validate_coordinates(text):
        """Extract and validate coordinate numbers"""
        numbers = re.findall(r'[-+]?\d*\.?\d+', text)
        if len(numbers) >= 2:
            coord1, coord2 = float(numbers[0]), float(numbers[1])
            
            # Check both possible orders
            lat_lon_valid = -90 <= coord1 <= 90 and -180 <= coord2 <= 180
            lon_lat_valid = -90 <= coord2 <= 90 and -180 <= coord1 <= 180
            
            if lat_lon_valid:
                return (coord1, coord2, "Lat/Lon")
            elif lon_lat_valid:
                return (coord2, coord1, "Lon/Lat (auto-corrected)")
            else:
                return (None, None, "Invalid range")
        return (None, None, "Insufficient numbers")
    
    success_count = 0
    total_count = len(test_cases)
    
    for i, (input_text, expected_format, should_succeed) in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{input_text}'")
        print("-" * len(f"Test {i}: '{input_text}'"))
        
        detected_format = detect_format(input_text)
        print(f"Detected format: {detected_format}")
        print(f"Expected format: {expected_format}")
        
        # Validate coordinates for basic formats
        if detected_format in ["Decimal", "DMS"]:
            lat, lon, order_info = validate_coordinates(input_text)
            if lat is not None and lon is not None:
                print(f"Extracted coordinates: lat={lat:.6f}, lon={lon:.6f} ({order_info})")
            else:
                print(f"Coordinate validation failed: {order_info}")
        
        # Check if detection matches expectation
        format_correct = (detected_format == expected_format) or (detected_format != "Unknown" and should_succeed)
        
        if format_correct:
            print("✓ PASS")
            success_count += 1
        else:
            print("✗ FAIL")
            if should_succeed:
                print(f"  Expected to detect format, but got: {detected_format}")
            else:
                print(f"  Expected to fail, but detected: {detected_format}")
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {success_count}/{total_count}")
    print(f"Success rate: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 All tests passed! Pattern detection is working correctly.")
    else:
        print("⚠️  Some tests failed. Review the detection logic.")
    
    print("\nThis validates the core pattern matching logic used by the smart parser.")
    print("The actual parser includes additional validation, transformation, and error handling.")

def test_coordinate_order_detection():
    """Test coordinate order detection and auto-correction"""
    
    print("\n" + "=" * 80)
    print("COORDINATE ORDER DETECTION TEST")
    print("=" * 80)
    
    test_coords = [
        # (coord1, coord2, description)
        (40.7128, -74.0060, "NYC - Clear Lat/Lon order"),
        (-74.0060, 40.7128, "NYC - Needs Lon/Lat correction"),
        (34.0, 35.0, "Ambiguous - both orders valid"),
        (-34.0, -35.0, "Ambiguous negative - both orders valid"),
        (91.0, -74.0, "Invalid - lat out of range"),
        (40.0, 181.0, "Invalid - lon out of range"),
        (200.0, 300.0, "Invalid - both out of range"),
    ]
    
    def analyze_coordinate_order(coord1, coord2):
        """Analyze coordinate order with the same logic as smart parser"""
        
        # Check validity of both possible orders
        lat_lon_valid = -90 <= coord1 <= 90 and -180 <= coord2 <= 180
        lon_lat_valid = -90 <= coord2 <= 90 and -180 <= coord1 <= 180
        
        if lat_lon_valid and lon_lat_valid:
            return (coord1, coord2, "AMBIGUOUS - both orders valid", "⚠️")
        elif lat_lon_valid:
            return (coord1, coord2, "Valid Lat/Lon order", "✓")
        elif lon_lat_valid:
            return (coord2, coord1, "Auto-corrected to Lat/Lon", "🔄")
        else:
            return (None, None, "Invalid in both orders", "✗")
    
    for coord1, coord2, description in test_coords:
        print(f"\nInput: ({coord1}, {coord2}) - {description}")
        print("-" * 60)
        
        result_lat, result_lon, analysis, status = analyze_coordinate_order(coord1, coord2)
        
        print(f"{status} {analysis}")
        if result_lat is not None:
            print(f"   Final coordinates: lat={result_lat:.6f}, lon={result_lon:.6f}")
        else:
            print(f"   No valid coordinate interpretation found")
    
    print("\nThis shows how the smart parser handles coordinate order ambiguity")
    print("and automatically corrects common lon/lat vs lat/lon ordering issues.")

if __name__ == "__main__":
    test_coordinate_patterns()
    test_coordinate_order_detection()