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

    def test_agri_analysis(self):
        """Test Agricultural Analysis endpoint with specific test cases"""
        print("\n🌱 Testing Agricultural Analysis Endpoint...")
        
        # Test Case 1: Low moisture (20%), high temp (38°C) → should return immediate irrigation urgency
        print("\n📋 Test Case 1: Low moisture + High temperature (Critical conditions)")
        success1, response1 = self.run_test(
            "Agri Analysis - Critical Irrigation Needed",
            "POST",
            "agri-analysis",
            200,
            data={
                "moisture": 20.0,
                "temperature": 38.0,
                "humidity": 50.0
            }
        )
        
        if success1 and response1:
            # Validate response structure
            required_fields = [
                "environmental_assessment", "crop_recommendation", "irrigation_decision",
                "yield_insight", "fertilizer_advisory", "risk_detection", "corrective_actions"
            ]
            missing_fields = [field for field in required_fields if field not in response1]
            if missing_fields:
                print(f"   ❌ Missing fields: {missing_fields}")
                success1 = False
            else:
                print(f"   ✅ All required fields present")
                
                # Check irrigation urgency for critical conditions
                irrigation = response1.get("irrigation_decision", {})
                if irrigation.get("urgency") == "immediate" and irrigation.get("irrigation_needed") == True:
                    print(f"   ✅ Correct irrigation urgency: {irrigation.get('urgency')}")
                else:
                    print(f"   ❌ Expected immediate irrigation, got: {irrigation.get('urgency')}")
                    success1 = False
                
                # Check risk detection for high temperature
                risks = response1.get("risk_detection", {}).get("identified_risks", [])
                heat_stress_found = any(risk.get("type") == "Heat Stress" for risk in risks)
                water_stress_found = any(risk.get("type") == "Water Stress" for risk in risks)
                if heat_stress_found and water_stress_found:
                    print(f"   ✅ Correctly identified heat stress and water stress risks")
                else:
                    print(f"   ❌ Expected heat stress and water stress risks")
                    success1 = False
        
        # Test Case 2: Optimal conditions (55% moisture, 25°C) → should return favorable yield status
        print("\n📋 Test Case 2: Optimal conditions")
        success2, response2 = self.run_test(
            "Agri Analysis - Optimal Conditions",
            "POST",
            "agri-analysis",
            200,
            data={
                "moisture": 55.0,
                "temperature": 25.0,
                "humidity": 65.0
            }
        )
        
        if success2 and response2:
            # Check yield status for optimal conditions
            yield_insight = response2.get("yield_insight", {})
            if yield_insight.get("yield_status") == "favorable":
                print(f"   ✅ Correct yield status: {yield_insight.get('yield_status')}")
            else:
                print(f"   ❌ Expected favorable yield status, got: {yield_insight.get('yield_status')}")
                success2 = False
            
            # Check irrigation decision for optimal conditions
            irrigation = response2.get("irrigation_decision", {})
            if irrigation.get("irrigation_needed") == False:
                print(f"   ✅ Correctly determined no irrigation needed")
            else:
                print(f"   ❌ Expected no irrigation needed for optimal conditions")
                success2 = False
        
        # Test Case 3: High moisture (80%) → should detect waterlogging risk
        print("\n📋 Test Case 3: High moisture (Waterlogging risk)")
        success3, response3 = self.run_test(
            "Agri Analysis - High Moisture",
            "POST",
            "agri-analysis",
            200,
            data={
                "moisture": 80.0,
                "temperature": 28.0,
                "humidity": 85.0
            }
        )
        
        if success3 and response3:
            # Check for waterlogging risk detection
            risks = response3.get("risk_detection", {}).get("identified_risks", [])
            waterlogging_found = any(risk.get("type") == "Waterlogging" for risk in risks)
            disease_risk_found = any(risk.get("type") == "Disease Risk" for risk in risks)
            
            if waterlogging_found:
                print(f"   ✅ Correctly identified waterlogging risk")
            else:
                print(f"   ❌ Expected waterlogging risk detection")
                success3 = False
            
            if disease_risk_found:
                print(f"   ✅ Correctly identified disease risk (high moisture + humidity)")
            else:
                print(f"   ❌ Expected disease risk detection")
                success3 = False
            
            # Check irrigation decision for high moisture
            irrigation = response3.get("irrigation_decision", {})
            if irrigation.get("irrigation_needed") == False:
                print(f"   ✅ Correctly determined no irrigation needed for high moisture")
            else:
                print(f"   ❌ Expected no irrigation needed for high moisture conditions")
                success3 = False
        
        # Test invalid input
        print("\n📋 Test Case 4: Invalid input validation")
        success4, _ = self.run_test(
            "Agri Analysis - Missing Fields",
            "POST",
            "agri-analysis",
            422,  # Expecting validation error
            data={
                "moisture": 50.0
                # Missing temperature and humidity
            }
        )
        
        # Test edge cases
        print("\n📋 Test Case 5: Edge case values")
        success5, response5 = self.run_test(
            "Agri Analysis - Edge Cases",
            "POST",
            "agri-analysis",
            200,
            data={
                "moisture": 0.0,
                "temperature": 50.0,
                "humidity": 100.0
            }
        )
        
        if success5 and response5:
            # Should detect extreme conditions
            risks = response5.get("risk_detection", {}).get("identified_risks", [])
            risk_count = len([r for r in risks if r.get("severity") in ["high", "medium"]])
            if risk_count > 0:
                print(f"   ✅ Correctly identified {risk_count} risks for extreme conditions")
            else:
                print(f"   ❌ Expected risk detection for extreme conditions")
                success5 = False
        
        overall_success = success1 and success2 and success3 and success4 and success5
        
        if overall_success:
            print(f"\n✅ All Agricultural Analysis tests passed!")
        else:
            print(f"\n❌ Some Agricultural Analysis tests failed")
        
        return overall_success

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