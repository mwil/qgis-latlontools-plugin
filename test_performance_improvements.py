#!/usr/bin/env python3
"""
Quick performance test for coordinate parsing optimizations
Run with: python3 test_performance_improvements.py
"""
import time
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_fast_detection():
    """Test the fast format detection system"""
    print("=== TESTING FAST COORDINATE DETECTION ===")
    
    try:
        from fast_coordinate_detector import FastCoordinateDetector
        
        detector = FastCoordinateDetector()
        
        test_cases = [
            ("40.7128, -74.0060", "decimal_degrees"),
            ("40°42'46.1\"N 74°00'21.6\"W", "dms_symbols"),
            ("POINT(-74.0060 40.7128)", "wkt_point"),
            ("0101000000000000000000000000000000", "wkb_hex"),
            ("33N 315428 5741324", "utm"),
            ("MGRS:33UUP1234567890", "mgrs"),
            ("9q5prz", "geohash"),
            ("87283472bffffff", "h3"),
            ("9C2XRV+2F", "plus_codes"),
            ("FN20id", "maidenhead"),
        ]
        
        total_time = 0
        successful_detections = 0
        
        for i, (coordinate, expected_format) in enumerate(test_cases, 1):
            start = time.perf_counter()
            detected = detector.detect_format_fast(coordinate)
            elapsed = time.perf_counter() - start
            total_time += elapsed
            
            status = "✅" if detected == expected_format else "❌"
            print(f"Test {i:2d}: {status} '{coordinate[:30]:<30}' → {detected or 'None':<15} ({elapsed*1000:.2f}ms)")
            
            if detected == expected_format:
                successful_detections += 1
        
        print(f"\n📊 RESULTS:")
        print(f"   Success Rate: {successful_detections}/{len(test_cases)} ({successful_detections/len(test_cases)*100:.1f}%)")
        print(f"   Average Time: {total_time/len(test_cases)*1000:.2f}ms per detection")
        print(f"   Total Time:   {total_time*1000:.1f}ms")
        
        # Performance stats
        stats = detector.get_detection_stats()
        print(f"   Hit Rate:     {stats['hit_rate_percent']:.1f}%")
        print(f"   Fast Routes:  {stats['fast_routes']}")
        
        return successful_detections == len(test_cases)
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False


def test_pattern_performance():
    """Test the pre-compiled regex pattern performance"""
    print("\n=== TESTING REGEX PATTERN PERFORMANCE ===")
    
    try:
        from fast_coordinate_detector import COORDINATE_PATTERNS
        
        # Test coordinate strings
        test_strings = [
            "40.7128, -74.0060",
            "40°42'46.1\"N 74°00'21.6\"W", 
            "POINT(-74.0060 40.7128)",
            "33N 315428 5741324",
            "9q5prz",
            "Invalid coordinate text",
        ]
        
        iterations = 1000
        
        print(f"Testing {len(COORDINATE_PATTERNS)} patterns against {len(test_strings)} strings, {iterations} iterations each...")
        
        start = time.perf_counter()
        
        for _ in range(iterations):
            for test_string in test_strings:
                for pattern_name, pattern in COORDINATE_PATTERNS.items():
                    pattern.search(test_string)
        
        elapsed = time.perf_counter() - start
        total_operations = len(COORDINATE_PATTERNS) * len(test_strings) * iterations
        
        print(f"✅ Completed {total_operations:,} pattern matches in {elapsed:.3f}s")
        print(f"   Average: {elapsed/total_operations*1000000:.1f}μs per pattern match")
        print(f"   Rate: {total_operations/elapsed:,.0f} operations/second")
        
        return True
        
    except Exception as e:
        print(f"❌ Pattern test error: {e}")
        return False


def main():
    """Run all performance tests"""
    all_passed = True
    
    # Test fast detection
    if not test_fast_detection():
        all_passed = False
    
    # Test pattern performance
    if not test_pattern_performance():
        all_passed = False
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)