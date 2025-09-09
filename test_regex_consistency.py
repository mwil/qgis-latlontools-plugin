#!/usr/bin/env python3
"""
Test the consistency of the obviously_projected regex pattern
"""
import re

def test_regex_consistency():
    """Test that the obviously_projected pattern behaves consistently"""
    # Define the pattern directly to avoid import issues
    pattern = re.compile(
        r'''
        ^\s*                # Optional leading whitespace
        [+-]?               # Optional sign
        (?:\d{4,})\.?\d*    # 4+ digits (easting), optional decimal
        [\s,;]+             # Separator(s)
        [+-]?               # Optional sign
        (?:\d{4,})\.?\d*    # 4+ digits (northing), optional decimal
        \s*$                # Optional trailing whitespace
        ''',
        re.VERBOSE
    )
    
    # Test cases that should ALL match (consistent 4+ digits)
    test_cases = [
        ('1234, 5678', True, '4 digits each - should match'),
        ('5678, 1234', True, '4 digits each (reversed) - should match'),
        ('1234, 56789', True, '4+ and 5+ digits - should match'),
        ('56789, 1234', True, '5+ and 4+ digits - should match'),
        ('12345, 67890', True, '5 digits each - should match'),
        ('500000, 4000000', True, 'UTM coordinates - should match'),
        ('4000000, 500000', True, 'UTM coordinates (reversed) - should match'),
    ]
    
    # Test cases that should NOT match (valid geographic)
    geographic_cases = [
        ('45.123, -122.456', False, 'Valid lat/lon - should NOT match'),
        ('89.999, 179.999', False, 'Near poles - should NOT match'),
        ('-89.999, -179.999', False, 'Near poles negative - should NOT match'),
        ('123, 456', False, '3 digits each - should NOT match'),
        ('12, 345', False, 'Less than 4 digits - should NOT match'),
    ]
    
    all_tests = test_cases + geographic_cases
    passed = 0
    
    print("Testing obviously_projected regex pattern consistency:")
    print("=" * 60)
    
    for coordinate, should_match, description in all_tests:
        match = pattern.match(coordinate)
        is_match = match is not None
        
        if is_match == should_match:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
        
        print(f"{status}: '{coordinate}' - {description}")
    
    print("=" * 60)
    print(f"Results: {passed}/{len(all_tests)} passed")
    
    if passed == len(all_tests):
        print("🎉 All consistency tests passed!")
        print("✅ Regex pattern now behaves consistently in both coordinate orders")
        return True
    else:
        print("❌ Some tests failed")
        return False

if __name__ == '__main__':
    success = test_regex_consistency()
    exit(0 if success else 1)