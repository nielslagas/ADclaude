import requests
import json
import time
import os
import sys

# Color codes for output
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Configuration
API_URL = "http://localhost:8000/api/v1"
# Mock JWT token for testing
MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlX3VzZXJfaWQiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"


def print_header(message):
    print(f"\n{YELLOW}{'=' * 60}{NC}")
    print(f"{YELLOW}{message.center(60)}{NC}")
    print(f"{YELLOW}{'=' * 60}{NC}\n")


def print_test_result(test_name, success, message=""):
    if success:
        print(f"{GREEN}✓ {test_name}{NC}")
    else:
        print(f"{RED}✗ {test_name}{NC}")
        if message:
            print(f"  {message}")


def test_root_endpoint():
    print_header("Testing Root Endpoint")
    try:
        response = requests.get("http://localhost:8000/")
        data = response.json()
        success = "message" in data and "AD-Rapport Generator API" in data["message"]
        print_test_result("Root endpoint", success)
        return success
    except Exception as e:
        print_test_result("Root endpoint", False, str(e))
        return False


def test_auth_endpoint():
    print_header("Testing Auth Endpoint")
    
    try:
        headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
        response = requests.get(f"{API_URL}/auth/me", headers=headers)
        data = response.json()
        success = "user_id" in data
        print_test_result("Auth endpoint", success)
        if success:
            print(f"{BLUE}User ID: {data['user_id']}{NC}")
        return success
    except Exception as e:
        print_test_result("Auth endpoint", False, str(e))
        return False


def test_cases_endpoints():
    print_header("Testing Cases Endpoints")
    
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    case_id = None
    
    # Test GET /cases
    try:
        response = requests.get(f"{API_URL}/cases", headers=headers)
        success = response.status_code == 200 and isinstance(response.json(), list)
        print_test_result("List cases", success)
    except Exception as e:
        print_test_result("List cases", False, str(e))
    
    # Test POST /cases
    try:
        test_case = {
            "title": f"Test Case {int(time.time())}",
            "description": "This is a test case created by the automated test script"
        }
        response = requests.post(
            f"{API_URL}/cases",
            headers=headers,
            json=test_case
        )
        data = response.json()
        success = response.status_code == 201 and "id" in data
        print_test_result("Create case", success)
        if success:
            case_id = data["id"]
            print(f"{BLUE}Created case ID: {case_id}{NC}")
    except Exception as e:
        print_test_result("Create case", False, str(e))
    
    # If we don't have a case ID, we can't continue with the tests
    if not case_id:
        return False
    
    # Test GET /cases/{case_id}
    try:
        response = requests.get(f"{API_URL}/cases/{case_id}", headers=headers)
        data = response.json()
        success = response.status_code == 200 and data["id"] == case_id
        print_test_result("Get specific case", success)
    except Exception as e:
        print_test_result("Get specific case", False, str(e))
    
    # Test documents for case
    try:
        response = requests.get(f"{API_URL}/documents/case/{case_id}", headers=headers)
        success = response.status_code == 200 and isinstance(response.json(), list)
        print_test_result("List case documents", success)
    except Exception as e:
        print_test_result("List case documents", False, str(e))
    
    # Test reports for case
    try:
        response = requests.get(f"{API_URL}/reports/case/{case_id}", headers=headers)
        success = response.status_code == 200 and isinstance(response.json(), list)
        print_test_result("List case reports", success)
    except Exception as e:
        print_test_result("List case reports", False, str(e))
    
    # Test DELETE /cases/{case_id}
    try:
        response = requests.delete(f"{API_URL}/cases/{case_id}", headers=headers)
        success = response.status_code == 204
        print_test_result("Delete case", success)
    except Exception as e:
        print_test_result("Delete case", False, str(e))
    
    return True


def test_report_templates():
    print_header("Testing Report Templates")
    
    headers = {"Authorization": f"Bearer {MOCK_TOKEN}"}
    
    try:
        response = requests.get(f"{API_URL}/reports/templates", headers=headers)
        data = response.json()
        success = response.status_code == 200 and "staatvandienst" in data
        print_test_result("Get report templates", success)
        if success:
            templates = list(data.keys())
            print(f"{BLUE}Available templates: {', '.join(templates)}{NC}")
        return success
    except Exception as e:
        print_test_result("Get report templates", False, str(e))
        return False


if __name__ == "__main__":
    print_header("AD-Rapport Generator Backend API Tests")
    
    success_count = 0
    total_tests = 4
    
    if test_root_endpoint():
        success_count += 1
    
    if test_auth_endpoint():
        success_count += 1
    
    if test_cases_endpoints():
        success_count += 1
    
    if test_report_templates():
        success_count += 1
    
    print_header(f"Test Summary: {success_count}/{total_tests} tests passed")
    
    # Exit with appropriate code for CI/CD pipelines
    sys.exit(0 if success_count == total_tests else 1)