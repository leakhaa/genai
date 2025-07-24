#!/usr/bin/env python3
"""
Test script for WMS Automation System
Demonstrates system functionality with sample data
"""
import requests
import json
import time
import os
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api"

def print_header(title):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_response(response, title="Response"):
    """Print formatted API response"""
    print(f"\n{title}:")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text)

def test_health_check():
    """Test system health"""
    print_header("HEALTH CHECK")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        print_response(response, "Health Check")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_issue_reporting():
    """Test issue reporting with various scenarios"""
    print_header("ISSUE REPORTING TESTS")
    
    test_cases = [
        {
            "name": "Missing ASN",
            "data": {
                "user_email": "warehouse.user@company.com",
                "message": "ASN456 is missing from the system. We expected it yesterday but it hasn't arrived yet."
            }
        },
        {
            "name": "Missing PO",
            "data": {
                "user_email": "receiving.clerk@company.com", 
                "message": "PO123 is missing from ASN456. The ASN shows up but PO123 is not there."
            }
        },
        {
            "name": "Pallet Missing",
            "data": {
                "user_email": "floor.supervisor@company.com",
                "message": "Pallet PALT789 is missing from PO123. All other pallets are accounted for."
            }
        },
        {
            "name": "Quantity Mismatch",
            "data": {
                "user_email": "inventory.manager@company.com",
                "message": "There's a quantity mismatch for PO124. Excel shows 1000 units but system shows 950."
            }
        },
        {
            "name": "Unclear Issue",
            "data": {
                "user_email": "new.employee@company.com",
                "message": "Something is wrong with the warehouse system. Not sure what exactly."
            }
        }
    ]
    
    issue_ids = []
    
    for test_case in test_cases:
        print(f"\n--- Testing: {test_case['name']} ---")
        
        try:
            response = requests.post(
                f"{API_BASE}/report-issue",
                json=test_case['data'],
                headers={'Content-Type': 'application/json'}
            )
            
            print_response(response, f"Issue Report - {test_case['name']}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    issue_ids.append(data['issue_id'])
                    print(f"✅ Issue created: {data['issue_id'][:8]}")
                    print(f"   Type: {data['classification']['issue_type']}")
                    print(f"   Action: {data['classification']['action']}")
                    print(f"   Priority: {data['classification']['priority']}")
                else:
                    print(f"❌ Issue creation failed: {data.get('error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception during {test_case['name']}: {e}")
        
        # Small delay between requests
        time.sleep(1)
    
    return issue_ids

def test_issue_status_check(issue_ids):
    """Test issue status checking"""
    print_header("ISSUE STATUS CHECKS")
    
    for issue_id in issue_ids:
        print(f"\n--- Checking Status for Issue: {issue_id[:8]} ---")
        
        try:
            response = requests.get(f"{API_BASE}/issue-status/{issue_id}")
            print_response(response, f"Status Check - {issue_id[:8]}")
            
            if response.status_code == 200:
                data = response.json()
                issue = data['issue']
                actions = data['actions']
                
                print(f"✅ Issue Status: {issue['status']}")
                print(f"   Type: {issue['issue_type']}")
                print(f"   Priority: {issue['priority']}")
                print(f"   Created: {issue['created_at']}")
                print(f"   Actions Taken: {len(actions)}")
                
                for action in actions:
                    print(f"   - {action['action_type']}: {action['description']}")
            else:
                print(f"❌ Status check failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception during status check: {e}")
        
        time.sleep(0.5)

def test_excel_validation():
    """Test Excel file validation"""
    print_header("EXCEL VALIDATION TEST")
    
    # Create a sample Excel file for testing
    import pandas as pd
    
    sample_data = {
        'PO_ID': ['PO123', 'PO123', 'PO124', 'PO124'],
        'Pallet_ID': ['PALT001', 'PALT002', 'PALT003', 'PALT004'],
        'Quantity': [100, 150, 200, 250]
    }
    
    df = pd.DataFrame(sample_data)
    test_file = 'test_warehouse_data.xlsx'
    df.to_excel(test_file, index=False)
    
    print(f"Created test Excel file: {test_file}")
    print("Sample data:")
    print(df)
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {
                'po_id': 'PO123',
                'issue_id': 'test-validation'
            }
            
            response = requests.post(
                f"{API_BASE}/validate-excel",
                files=files,
                data=data
            )
            
        print_response(response, "Excel Validation")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                validation = result['validation_result']
                print(f"✅ Validation completed")
                print(f"   Status: {validation['status']}")
                print(f"   Total Records: {validation['total_records']}")
                print(f"   Excel Total: {validation.get('excel_total', 'N/A')}")
                print(f"   Database Total: {validation.get('database_total', 'N/A')}")
                print(f"   Variance: {validation.get('variance', 'N/A')}")
            else:
                print(f"❌ Validation failed: {result.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception during Excel validation: {e}")
    
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            print(f"Cleaned up test file: {test_file}")

def test_dashboard_data():
    """Test dashboard data retrieval"""
    print_header("DASHBOARD DATA TEST")
    
    try:
        response = requests.get(f"{API_BASE}/dashboard")
        print_response(response, "Dashboard Data")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data['statistics']
                print(f"✅ Dashboard data retrieved")
                print(f"   Total Issues: {stats.get('total_issues', 0)}")
                print(f"   Average Resolution Time: {stats.get('average_resolution_hours', 0):.1f} hours")
                print(f"   Status Distribution: {stats.get('status_distribution', {})}")
                print(f"   Type Distribution: {stats.get('type_distribution', {})}")
            else:
                print(f"❌ Dashboard data failed: {data.get('error')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception during dashboard test: {e}")

def test_warehouse_data():
    """Test warehouse data retrieval"""
    print_header("WAREHOUSE DATA TEST")
    
    test_cases = [
        ("asn", "ASN456"),
        ("po", "PO123"),
        ("pallet", "PALT789")
    ]
    
    for data_type, entity_id in test_cases:
        print(f"\n--- Testing {data_type.upper()} Data: {entity_id} ---")
        
        try:
            response = requests.get(f"{API_BASE}/warehouse-data/{data_type}/{entity_id}")
            print_response(response, f"{data_type.upper()} Data")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print(f"✅ {data_type.upper()} data retrieved successfully")
                    # Print key fields based on type
                    warehouse_data = data['data']
                    if data_type == 'asn':
                        print(f"   ASN Number: {warehouse_data.get('asn_number', 'N/A')}")
                        print(f"   Status: {warehouse_data.get('status', 'N/A')}")
                        print(f"   Total POs: {warehouse_data.get('total_pos', 0)}")
                    elif data_type == 'po':
                        print(f"   PO Number: {warehouse_data.get('po_number', 'N/A')}")
                        print(f"   Status: {warehouse_data.get('status', 'N/A')}")
                        print(f"   Total Quantity: {warehouse_data.get('total_quantity', 0)}")
                    elif data_type == 'pallet':
                        print(f"   Pallet Number: {warehouse_data.get('pallet_number', 'N/A')}")
                        print(f"   Status: {warehouse_data.get('status', 'N/A')}")
                        print(f"   Quantity: {warehouse_data.get('quantity', 0)}")
                else:
                    print(f"❌ {data_type.upper()} data failed: {data.get('error')}")
            elif response.status_code == 404:
                print(f"⚠️  {data_type.upper()} {entity_id} not found (expected for test data)")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception during {data_type} test: {e}")
        
        time.sleep(0.5)

def main():
    """Main test execution"""
    print_header("WMS AUTOMATION SYSTEM - COMPREHENSIVE TEST")
    print(f"Testing system at: {BASE_URL}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if system is running
    if not test_health_check():
        print("\n❌ System health check failed. Make sure the Flask app is running.")
        print("   Start the system with: python app.py")
        return
    
    print("\n✅ System is healthy. Proceeding with tests...")
    
    # Run test suite
    issue_ids = test_issue_reporting()
    
    if issue_ids:
        print(f"\n✅ Created {len(issue_ids)} test issues")
        time.sleep(2)  # Allow some processing time
        test_issue_status_check(issue_ids)
    else:
        print("\n⚠️  No issues were created, skipping status checks")
    
    test_excel_validation()
    test_dashboard_data()
    test_warehouse_data()
    
    print_header("TEST SUMMARY")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Issues created: {len(issue_ids)}")
    print("\n🎉 All tests completed!")
    print("\nNext steps:")
    print("1. Check the web dashboard at: http://localhost:5000")
    print("2. Review the logs for detailed processing information")
    print("3. Check email templates in email_service/templates/")
    print("4. Review generated screenshots in screenshots/ directory")

if __name__ == "__main__":
    main()