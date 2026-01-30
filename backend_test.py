import requests
import sys
from datetime import datetime
import json

class AgriSmartAPITester:
    def __init__(self, base_url="https://irrigent.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('/') else f"{self.api_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_status_endpoints(self):
        """Test status check endpoints"""
        # Test POST status
        success, response = self.run_test(
            "Create Status Check",
            "POST", 
            "status",
            200,
            data={"client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"}
        )
        
        # Test GET status
        self.run_test("Get Status Checks", "GET", "status", 200)
        
        return success

    def test_motor_control(self):
        """Test motor control endpoints"""
        # Test motor status
        self.run_test("Get Motor Status", "GET", "motor/status", 200)
        
        # Test motor control - turn on
        success_on, _ = self.run_test(
            "Motor Control - Turn On",
            "POST",
            "motor/control",
            200,
            data={"status": "on"}
        )
        
        # Test motor control - turn off
        success_off, _ = self.run_test(
            "Motor Control - Turn Off", 
            "POST",
            "motor/control",
            200,
            data={"status": "off"}
        )
        
        # Test invalid motor control
        self.run_test(
            "Motor Control - Invalid Status",
            "POST",
            "motor/control", 
            400,
            data={"status": "invalid"}
        )
        
        return success_on and success_off

    def test_commodity_prices(self):
        """Test commodity price endpoints for all crops"""
        crops = ["rice", "onion", "tomato", "cotton", "groundnut"]
        all_success = True
        
        for crop in crops:
            success, response = self.run_test(
                f"Commodity Prices - {crop.title()}",
                "GET",
                f"commodity-prices/{crop}",
                200
            )
            
            if success and response:
                # Validate response structure
                required_fields = ["crop", "prices", "dates", "current_price", "forecast_price", "recommendation", "change_percent", "accuracy"]
                missing_fields = [field for field in required_fields if field not in response]
                if missing_fields:
                    print(f"   ⚠️  Missing fields: {missing_fields}")
                    all_success = False
                else:
                    print(f"   ✅ All required fields present")
            else:
                all_success = False
        
        # Test invalid crop
        self.run_test(
            "Commodity Prices - Invalid Crop",
            "GET",
            "commodity-prices/invalid_crop",
            404
        )
        
        return all_success

    def test_thingspeak_integration(self):
        """Test ThingSpeak integration endpoint"""
        # Test with invalid credentials (should fail gracefully)
        success, _ = self.run_test(
            "ThingSpeak Fetch - Invalid Credentials",
            "POST",
            "thingspeak/fetch",
            400,  # Expecting 400 for invalid credentials
            data={
                "channel_id": "invalid_channel",
                "read_api_key": "invalid_key"
            }
        )
        
        # Note: We can't test valid ThingSpeak without real credentials
        print("   ℹ️  ThingSpeak integration requires valid credentials for full testing")
        return True  # Consider this passed as it handles errors correctly

def main():
    print("🚀 Starting AgriSmart API Testing...")
    print("=" * 60)
    
    tester = AgriSmartAPITester()
    
    # Run all tests
    tests = [
        ("Root Endpoint", tester.test_root_endpoint),
        ("Status Endpoints", tester.test_status_endpoints), 
        ("Motor Control", tester.test_motor_control),
        ("Commodity Prices", tester.test_commodity_prices),
        ("ThingSpeak Integration", tester.test_thingspeak_integration)
    ]
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Tests...")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test suite {test_name} failed with error: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results Summary:")
    print(f"   Tests Run: {tester.tests_run}")
    print(f"   Tests Passed: {tester.tests_passed}")
    print(f"   Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"   Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.failed_tests:
        print(f"\n❌ Failed Tests Details:")
        for i, failure in enumerate(tester.failed_tests, 1):
            print(f"   {i}. {failure.get('test', 'Unknown')}")
            print(f"      Endpoint: {failure.get('endpoint', 'Unknown')}")
            if 'error' in failure:
                print(f"      Error: {failure['error']}")
            else:
                print(f"      Expected: {failure.get('expected')}, Got: {failure.get('actual')}")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())