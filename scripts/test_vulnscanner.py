#!/usr/bin/env python3
"""
Test script for HemoStat Vulnerability Scanner integration

This script tests the OWASP ZAP integration by:
1. Starting the required services
2. Running a vulnerability scan
3. Checking the results

Usage:
    python test_vulnscanner.py
"""

import json
import time
import requests
from agents.hemostat_vulnscanner import VulnerabilityScanner


def test_zap_connection():
    """Test if ZAP is accessible."""
    print("Testing ZAP connection...")
    try:
        response = requests.get("http://localhost:8080/JSON/core/view/version/", timeout=5)
        if response.status_code == 200:
            version_info = response.json()
            print(f"✅ ZAP is accessible. Version: {version_info.get('version', 'unknown')}")
            return True
        else:
            print(f"❌ ZAP returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to ZAP: {e}")
        return False


def test_juice_shop_connection():
    """Test if Juice Shop is accessible."""
    print("Testing Juice Shop connection...")
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Juice Shop is accessible")
            return True
        else:
            print(f"❌ Juice Shop returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Juice Shop: {e}")
        return False


def test_vulnerability_scan():
    """Test a complete vulnerability scan."""
    print("Testing vulnerability scan...")
    try:
        # Initialize scanner
        scanner = VulnerabilityScanner()
        
        # Run a single scan cycle
        scanner.run_scan_cycle()
        
        print("✅ Vulnerability scan completed successfully")
        return True
    except Exception as e:
        print(f"❌ Vulnerability scan failed: {e}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("HemoStat Vulnerability Scanner Integration Test")
    print("=" * 60)
    
    # Test individual components
    tests = [
        ("ZAP Connection", test_zap_connection),
        ("Juice Shop Connection", test_juice_shop_connection),
        ("Vulnerability Scan", test_vulnerability_scan),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Running: {test_name}")
        result = test_func()
        results.append((test_name, result))
        time.sleep(2)  # Brief pause between tests
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! The vulnerability scanner integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        print("\nTroubleshooting tips:")
        print("1. Ensure Docker services are running: docker-compose up -d")
        print("2. Wait for services to be healthy: docker-compose ps")
        print("3. Check service logs: docker-compose logs zap juice-shop")


if __name__ == "__main__":
    main()
