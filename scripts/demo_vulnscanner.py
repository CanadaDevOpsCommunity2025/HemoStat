#!/usr/bin/env python3
"""
HemoStat Vulnerability Scanner Demo

This script demonstrates the complete OWASP ZAP integration workflow:
1. Connects to ZAP API
2. Scans Juice Shop for vulnerabilities
3. Processes and displays results
4. Shows integration with HemoStat ecosystem

Usage:
    python demo_vulnscanner.py
"""

import json
import time
import requests
from datetime import datetime


class ZAPDemo:
    """Demo class showing ZAP API integration."""
    
    def __init__(self):
        self.zap_api_url = "http://localhost:8080"
        self.target_url = "http://localhost:3000"  # Juice Shop
    
    def wait_for_zap(self, max_wait=60):
        """Wait for ZAP to be ready."""
        print("🔄 Waiting for ZAP to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.zap_api_url}/JSON/core/view/version/", timeout=5)
                if response.status_code == 200:
                    version_info = response.json()
                    print(f"✅ ZAP is ready! Version: {version_info.get('version', 'unknown')}")
                    return True
            except Exception:
                pass
            time.sleep(2)
        
        print("❌ ZAP did not become ready in time")
        return False
    
    def start_scan(self):
        """Start a ZAP scan."""
        print(f"🚀 Starting ZAP scan for: {self.target_url}")
        
        try:
            response = requests.get(
                f"{self.zap_api_url}/JSON/ascan/action/scan/",
                params={
                    "url": self.target_url,
                    "recurse": "true",
                    "inScopeOnly": "false"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                scan_id = result.get("scan")
                if scan_id:
                    print(f"✅ Scan started successfully! Scan ID: {scan_id}")
                    return scan_id
            
            print(f"❌ Failed to start scan: {response.text}")
            return None
            
        except Exception as e:
            print(f"❌ Error starting scan: {e}")
            return None
    
    def get_scan_progress(self, scan_id):
        """Get scan progress."""
        try:
            response = requests.get(
                f"{self.zap_api_url}/JSON/ascan/view/status/",
                params={"scanId": scan_id},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return int(result.get("status", -1))
            
        except Exception as e:
            print(f"❌ Error getting scan progress: {e}")
        
        return -1
    
    def wait_for_scan_completion(self, scan_id, max_wait=300):
        """Wait for scan to complete."""
        print("⏳ Waiting for scan to complete...")
        start_time = time.time()
        last_progress = -1
        
        while time.time() - start_time < max_wait:
            progress = self.get_scan_progress(scan_id)
            
            if progress == -1:
                print("❌ Failed to get scan progress")
                return False
            
            if progress != last_progress:
                print(f"📊 Scan progress: {progress}%")
                last_progress = progress
            
            if progress >= 100:
                print("✅ Scan completed!")
                return True
            
            time.sleep(5)
        
        print("⏰ Scan timed out")
        return False
    
    def get_scan_results(self):
        """Get vulnerability results."""
        print("📋 Retrieving scan results...")
        
        try:
            response = requests.get(f"{self.zap_api_url}/JSON/core/view/alerts/", timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                alerts = result.get("alerts", [])
                print(f"📊 Found {len(alerts)} vulnerability alerts")
                return alerts
            
        except Exception as e:
            print(f"❌ Error getting results: {e}")
        
        return []
    
    def process_results(self, alerts):
        """Process and display vulnerability results."""
        if not alerts:
            print("🎉 No vulnerabilities found!")
            return
        
        # Categorize by risk
        risk_counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
        critical_vulns = []
        
        for alert in alerts:
            risk = alert.get("risk", "Informational")
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            if risk == "High":
                critical_vulns.append({
                    "name": alert.get("alert", "Unknown"),
                    "url": alert.get("url", ""),
                    "description": alert.get("description", "")[:100] + "..."
                })
        
        # Display summary
        print("\n" + "=" * 60)
        print("🔍 VULNERABILITY SCAN RESULTS")
        print("=" * 60)
        print(f"Target: {self.target_url}")
        print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Vulnerabilities: {len(alerts)}")
        
        print("\n📊 Risk Summary:")
        for risk, count in risk_counts.items():
            if count > 0:
                emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Informational": "ℹ️"}
                print(f"  {emoji.get(risk, '•')} {risk}: {count}")
        
        if critical_vulns:
            print(f"\n🚨 CRITICAL VULNERABILITIES ({len(critical_vulns)}):")
            for i, vuln in enumerate(critical_vulns[:5], 1):  # Show top 5
                print(f"\n  {i}. {vuln['name']}")
                print(f"     URL: {vuln['url']}")
                print(f"     Description: {vuln['description']}")
            
            if len(critical_vulns) > 5:
                print(f"\n     ... and {len(critical_vulns) - 5} more critical vulnerabilities")
        
        # Save results to file
        report = {
            "timestamp": datetime.now().isoformat(),
            "target_url": self.target_url,
            "total_vulnerabilities": len(alerts),
            "risk_summary": risk_counts,
            "critical_vulnerabilities": critical_vulns,
            "full_results": alerts
        }
        
        with open("zap_scan_results.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Full results saved to: zap_scan_results.json")
    
    def run_demo(self):
        """Run the complete demo."""
        print("=" * 60)
        print("🔒 HemoStat OWASP ZAP Vulnerability Scanner Demo")
        print("=" * 60)
        
        # Step 1: Wait for ZAP
        if not self.wait_for_zap():
            return False
        
        # Step 2: Start scan
        scan_id = self.start_scan()
        if not scan_id:
            return False
        
        # Step 3: Wait for completion
        if not self.wait_for_scan_completion(scan_id):
            return False
        
        # Step 4: Get and process results
        alerts = self.get_scan_results()
        self.process_results(alerts)
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("=" * 60)
        
        return True


def main():
    """Main demo function."""
    demo = ZAPDemo()
    
    try:
        success = demo.run_demo()
        if not success:
            print("\n❌ Demo failed. Make sure services are running:")
            print("   docker-compose up -d juice-shop zap")
            return 1
        
        print("\n🎯 Next Steps:")
        print("1. Start the full HemoStat system: docker-compose up -d")
        print("2. Check the vulnerability scanner logs: docker-compose logs vulnscanner")
        print("3. View the dashboard: http://localhost:8501")
        print("4. Monitor Redis channels for vulnerability alerts")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
