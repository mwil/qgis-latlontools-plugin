#!/usr/bin/env python3
"""
Test runner for QGIS Lat Lon Tools plugin
Runs tests with proper QGIS environment initialization
"""

import sys
import os
import argparse
import unittest
import subprocess

# Set up QGIS environment first
sys.path.insert(0, '/Applications/QGIS.app/Contents/Resources/python')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize QGIS before any imports
from qgis.core import QgsApplication

def init_qgis():
    """Initialize QGIS application for testing"""
    QgsApplication.setPrefixPath('/Applications/QGIS.app/Contents', True)
    app = QgsApplication([], False)
    QgsApplication.initQgis()
    return app

def cleanup_qgis():
    """Clean up QGIS application"""
    QgsApplication.exitQgis()

def run_unit_tests(verbose=False):
    """Run unit tests that don't require full QGIS"""
    print("🧪 RUNNING UNIT TESTS")
    print("=" * 50)
    
    # These can run without QGIS initialization
    test_files = [
        'tests/unit/test_pattern_detection.py',
        'tests/unit/test_smart_parser_simple.py'
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\n📋 Running {test_file}...")
            try:
                # Import and run the test
                if 'pattern_detection' in test_file:
                    from tests.unit.test_pattern_detection import main
                    main()
                elif 'smart_parser_simple' in test_file:
                    from tests.unit.test_smart_parser_simple import main
                    main()
            except Exception as e:
                print(f"❌ Test failed: {e}")
                if verbose:
                    import traceback
                    traceback.print_exc()

def run_validation_tests(verbose=False):
    """Run validation tests that require QGIS"""
    print("\n🧪 RUNNING VALIDATION TESTS (with QGIS)")
    print("=" * 50)
    
    app = init_qgis()
    
    try:
        # Run all validation test files
        validation_test_files = [
            ('tests/validation/test_z_coordinate_handling.py', 'unittest'),
            ('tests/validation/test_coordinate_flipping_comprehensive.py', 'unittest'),
            ('tests/validation/test_real_world_coordinate_scenarios.py', 'unittest'),
            ('tests/validation/test_smart_parser_validation.py', 'function'),
            ('tests/validation/test_comprehensive_edge_cases.py', 'function')
        ]
        
        total_files = 0
        total_failures = 0
        
        for test_file, test_type in validation_test_files:
            if not os.path.exists(test_file):
                print(f"⚠️  Test file not found: {test_file}")
                continue
                
            total_files += 1
            print(f"📋 Running {os.path.basename(test_file)} ({test_type})...")
            
            try:
                if test_type == 'unittest':
                    # Run unittest-based tests as subprocess to avoid unittest.main() exit
                    result = subprocess.run(['/Applications/QGIS.app/Contents/MacOS/bin/python3', test_file], 
                                          capture_output=True, text=True, cwd=os.getcwd())
                    if result.returncode != 0:
                        raise Exception(f"Test failed with return code {result.returncode}")
                    # Extract and print key results
                    if result.stdout:
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if ('Failed' in line and '(' in line) or 'Total Tests:' in line or 'PASS' in line:
                                print(f"   {line.strip()}")
                    
                elif test_type == 'function':
                    # Run function-based tests as subprocess to handle their own QGIS initialization
                    result = subprocess.run(['/Applications/QGIS.app/Contents/MacOS/bin/python3', test_file], 
                                          capture_output=True, text=True, cwd=os.getcwd())
                    if result.returncode != 0:
                        raise Exception(f"Test failed with return code {result.returncode}")
                    # Print the output for visibility
                    if result.stdout:
                        print(result.stdout)
                    
                print(f"✅ {os.path.basename(test_file)} completed")
                
            except Exception as e:
                print(f"❌ {os.path.basename(test_file)} failed: {e}")
                total_failures += 1
                if verbose:
                    import traceback
                    traceback.print_exc()
        
        print(f"\n🏁 Validation Tests Summary:")
        print(f"Files run: {total_files}")
        print(f"Failures: {total_failures}")
                        
    finally:
        cleanup_qgis()

def run_comprehensive_tests(verbose=False):
    """Run all available tests"""
    print("🚀 COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Run unit tests first (no QGIS needed)
    run_unit_tests(verbose)
    
    # Then run validation tests (with QGIS)
    run_validation_tests(verbose)

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Run QGIS Lat Lon Tools tests')
    parser.add_argument('--type', choices=['unit', 'validation', 'all'], 
                        default='all', help='Type of tests to run')
    parser.add_argument('--verbose', action='store_true', 
                        help='Verbose output with full tracebacks')
    
    args = parser.parse_args()
    
    if args.type == 'unit':
        run_unit_tests(args.verbose)
    elif args.type == 'validation':
        run_validation_tests(args.verbose)
    else:
        run_comprehensive_tests(args.verbose)

if __name__ == "__main__":
    main()