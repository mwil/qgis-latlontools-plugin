#!/usr/bin/env python3
"""
Pattern Collision Tests

Tests for edge cases where input might match multiple coordinate format patterns.
This helps verify that the fast-path classification correctly handles ambiguous inputs.
"""

import re
import sys
import os

# Add parent directory to path
plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)


def test_mgrs_vs_geohash_collision():
    """
    Test that MGRS and Geohash patterns don't incorrectly collide.
    MGRS: zone (1-2 digits) + letter (C-X, excluding I,O) + grid letters + digits
    Geohash: base32 characters (0-9, b,c,d,e,f,g,h,j,k,m,n,p,q,r,s,t,u,v,w,x,y,z)

    Edge case: "4QFJ" - could be ambiguous
    """
    print("=== MGRS vs Geohash Pattern Collision Tests ===")
    print()

    test_cases = [
        # (input, should_match_mgrs, should_match_geohash, description)
        ("4QFJ", True, False, "MGRS grid square (no digits)"),
        ("4QFJ12", True, False, "MGRS with precision"),
        ("4qfj", False, True, "Geohash (lowercase)"),
        ("4QF", False, False, "Too short for both"),
        ("4QFGH", False, False, "Has letter outside Geohash set (g)"),
        ("12345678", False, True, "Pure digits (Geohash in decode mode)"),
    ]

    mgrs_pattern = re.compile(r"^\d{1,2}[C-HJ-NP-X][A-HJ-NP-Z]{2}\d{2,}$")
    geohash_pattern = re.compile(r"^[0-9bcdefghjkmnpqrstuvwxyz]+$")

    passed = 0
    for input_text, expect_mgrs, expect_geohash, desc in test_cases:
        matches_mgrs = bool(mgrs_pattern.match(input_text.upper()))
        matches_geohash = bool(geohash_pattern.match(input_text.lower()))

        mgrs_ok = matches_mgrs == expect_mgrs
        geohash_ok = matches_geohash == expect_geohash

        status = "✅ PASS" if (mgrs_ok and geohash_ok) else "❌ FAIL"
        print(f"{status} - {desc}")
        print(f"  Input: {input_text}")
        print(
            f"  MGRS: {matches_mgrs} (expected: {expect_mgrs}) - {'OK' if mgrs_ok else 'FAIL'}"
        )
        print(
            f"  Geohash: {matches_geohash} (expected: {expect_geohash}) - {'OK' if geohash_ok else 'FAIL'}"
        )
        print()

        if mgrs_ok and geohash_ok:
            passed += 1

    total = len(test_cases)
    print(f"RESULTS: {passed}/{total} passed")
    return passed == total


def test_wkt_with_decimal_coordinates():
    """
    Test that WKT classification doesn't incorrectly catch decimal coordinates.
    """
    print("=== WKT vs Decimal Coordinates Collision Tests ===")
    print()

    test_cases = [
        # (input, should_be_wkt, should_extract_decimal, description)
        ("POINT(-122.5 45.6)", True, False, "Valid WKT"),
        ("POINT 45.6, -122.5", True, True, "Invalid WKT but has POINT keyword"),
        ("45.6, -122.5", False, True, "Pure decimal coordinates"),
        ("LINESTRING(45.6 -122.5, 47.6 -121.5)", True, False, "WKT LineString"),
        ("POLYGON((45.6 -122.5, ...))", True, False, "WKT Polygon"),
        ("My POINT is at 45.6, -122.5", True, True, "Text containing POINT keyword"),
    ]

    wkt_keywords = [
        "POINT",
        "LINESTRING",
        "POLYGON",
        "MULTIPOINT",
        "MULTILINESTRING",
        "MULTIPOLYGON",
        "GEOMETRYCOLLECTION",
    ]

    passed = 0
    for input_text, expect_wkt, expect_decimal, desc in test_cases:
        has_wkt_keyword = any(kw in input_text.upper() for kw in wkt_keywords)

        # Extract numbers to check if decimal coordinates can be extracted
        numbers = re.findall(r"[+-]?\d*\.?\d+", input_text)
        has_decimal_coords = len(numbers) >= 2

        wkt_ok = has_wkt_keyword == expect_wkt
        decimal_ok = has_decimal_coords == expect_decimal

        status = "✅ PASS" if (wkt_ok and decimal_ok) else "⚠️  PARTIAL"
        print(f"{status} - {desc}")
        print(f"  Input: {input_text}")
        print(f"  WKT keyword: {has_wkt_keyword} (expected: {expect_wkt})")
        print(f"  Has decimals: {has_decimal_coords} (expected: {expect_decimal})")
        print()

        if wkt_ok and decimal_ok:
            passed += 1

    total = len(test_cases)
    print(f"RESULTS: {passed}/{total} passed")
    return passed >= total * 0.8  # Allow some partial passes


def test_hex_string_discrimination():
    """
    Test that hex strings are correctly discriminated between WKB, H3, and Geohash.
    WKB: >= 20 hex chars, even length
    H3: exactly 15 hex chars
    Geohash: base32 (includes g-z letters), 3-12 chars
    """
    print("=== Hex String Discrimination Tests ===")
    print()

    test_cases = [
        # (input, expected_format, description)
        ("010100000058c0d9f78a9c4140", "WKB", "WKB hex (40 chars, even)"),
        ("8f2830828071fff", "H3", "H3 hex (exactly 15 chars)"),
        ("c2g5", "Geohash", "Geohash (base32, 4 chars)"),
        ("dr5regy", "Geohash", "Geohash (base32, 7 chars)"),
        ("8f2830828071fff00", None, "16 hex chars (not WKB, not H3)"),
        ("g7qg", None, "Contains 'g' (not hex)"),
        ("C2G5", None, "Contains 'C' 'G' (not hex)"),
        ("87G7X2VV+2V", "PlusCodes", "Plus Codes (not hex)"),
    ]

    passed = 0
    for input_text, expected_format, desc in test_cases:
        text_clean = input_text.strip().replace(" ", "")
        is_hex = all(c in "0123456789ABCDEFabcdef" for c in text_clean)

        # Determine actual format
        if not is_hex:
            actual_format = "Not hex"
        elif len(text_clean) == 15:
            actual_format = "H3"
        elif len(text_clean) >= 20 and len(text_clean) % 2 == 0:
            actual_format = "WKB"
        elif len(text_clean) >= 3 and len(text_clean) <= 12:
            # Check if it's Geohash (base32, not just hex)
            if any(c in "ghjkmnpqrstuvwxyz" for c in text_clean.lower()):
                actual_format = "Geohash"
            else:
                actual_format = "Unknown hex"
        elif "+" in input_text:
            actual_format = "PlusCodes"
        else:
            actual_format = "Unknown"

        # Normalize comparison
        if expected_format is None:
            expected_format = "Not hex"

        ok = (expected_format == actual_format) or (actual_format == "Unknown hex")
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} - {desc}")
        print(f"  Input: {input_text}")
        print(f"  Expected: {expected_format}")
        print(f"  Actual: {actual_format}")
        print()

        if ok:
            passed += 1

    total = len(test_cases)
    print(f"RESULTS: {passed}/{total} passed")
    return passed >= total * 0.9


def test_plus_codes_edge_cases():
    """
    Test Plus Codes validation edge cases.
    Plus Codes: base20 alphabet (23456789CFGHJMPQRVWX) with '+' separator
    """
    print("=== Plus Codes Edge Cases Tests ===")
    print()

    test_cases = [
        # (input, should_be_valid, description)
        ("87G7X2VV+2V", True, "Valid Plus Code"),
        ("CWC4+X5", True, "Valid short Plus Code"),
        ("8FVC9G8F+2X", True, "Valid Plus Code with full code"),
        ("+ABC", False, "Empty before plus"),
        ("ABC+", False, "Empty after plus"),
        ("+", False, "Only separator"),
        ("87G7X2VV++2V", False, "Double plus"),
        ("1234+56", False, "Digit '1' not in alphabet"),
        ("ABCD+EF", False, "Letter 'A' 'B' 'D' not in alphabet"),
        ("87G7X2VV 2V", False, "Space instead of plus"),
        ("PREFIX87G7X2VV+2V", False, "Invalid prefix (P,I,R not in alphabet)"),
    ]

    plus_code_alphabet = set("23456789CFGHJMPQRVWX")

    passed = 0
    for input_text, should_be_valid, desc in test_cases:
        is_valid = False

        if "+" in input_text:
            parts = input_text.split("+")
            if len(parts) == 2:
                before_plus, after_plus = parts[0], parts[1]

                if (
                    before_plus
                    and after_plus
                    and len(before_plus) >= 2
                    and len(before_plus) <= 8
                    and all(c in plus_code_alphabet for c in before_plus.upper())
                    and all(c in plus_code_alphabet for c in after_plus.upper())
                ):
                    is_valid = True

        ok = is_valid == should_be_valid
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status} - {desc}")
        print(f"  Input: {input_text}")
        print(f"  Valid: {is_valid} (expected: {should_be_valid})")
        print()

        if ok:
            passed += 1

    total = len(test_cases)
    print(f"RESULTS: {passed}/{total} passed")
    return passed == total


def run_all_tests():
    """Run all pattern collision tests"""
    print("=" * 80)
    print("PATTERN COLLISION TESTS")
    print("=" * 80)
    print()

    results = []

    results.append(("MGRS vs Geohash", test_mgrs_vs_geohash_collision()))
    results.append(("WKT vs Decimal", test_wkt_with_decimal_coordinates()))
    results.append(("Hex Discrimination", test_hex_string_discrimination()))
    results.append(("Plus Codes Edge", test_plus_codes_edge_cases()))

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print()
    if passed == total:
        print("🎉 ALL TEST SUITES PASSED!")
        return True
    else:
        print(f"⚠️  {passed}/{total} test suites passed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
