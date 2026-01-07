#!/usr/bin/env python3
"""
Test script para Cost Management API endpoints
"""
import requests
import json
import uuid
from decimal import Decimal

BASE_URL = "http://localhost:8080"

def test_list_plans():
    """Listar planes"""
    print("\n🧪 Testing GET /api/costs/plans...")
    try:
        response = requests.get(f"{BASE_URL}/api/costs/plans")
        if response.status_code == 200:
            plans = response.json()
            print(f"✅ Success: Found {len(plans)} plans")
            for plan in plans:
                print(f"   - {plan['plan_code']}: ${plan['price_monthly_usd']}/mo")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_get_plan():
    """Obtener plan específico"""
    print("\n🧪 Testing GET /api/costs/plans/professional...")
    try:
        response = requests.get(f"{BASE_URL}/api/costs/plans/professional")
        if response.status_code == 200:
            plan = response.json()
            print(f"✅ Success: Got plan '{plan['plan_name']}'")
            print(f"   - Monthly: ${plan['price_monthly_usd']}")
            print(f"   - Annual: ${plan['price_annually_usd']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_list_resources():
    """Listar costos de recursos"""
    print("\n🧪 Testing GET /api/costs/resources...")
    try:
        response = requests.get(f"{BASE_URL}/api/costs/resources")
        if response.status_code == 200:
            resources = response.json()
            print(f"✅ Success: Found {len(resources)} resources")
            for res in resources[:5]:
                print(f"   - {res['tool_name']}: ${res['cost_per_unit_usd']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_calculate_cost():
    """Calcular costo estimado"""
    print("\n🧪 Testing POST /api/costs/calculate...")
    try:
        payload = {
            "resource_type": "analysis",
            "units": 1,
            "tool_name": "sparrow"
        }
        response = requests.post(
            f"{BASE_URL}/api/costs/calculate",
            json=payload
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: Calculation complete")
            print(f"   - Tool: {result['tool_name']}")
            print(f"   - Units: {result['units']}")
            print(f"   - Cost: ${result['total_cost_usd']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_register_usage():
    """Registrar uso de recurso"""
    print("\n🧪 Testing POST /api/costs/usage...")
    try:
        payload = {
            "tenant_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "case_id": str(uuid.uuid4()),
            "resource_type": "analysis",
            "resource_name": "Sparrow Analysis",
            "units_consumed": "1",
            "tool_name": "sparrow",
            "execution_time_seconds": 120
        }
        response = requests.post(
            f"{BASE_URL}/api/costs/usage",
            json=payload
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: Usage registered")
            print(f"   - Usage ID: {result.get('usage_id', 'N/A')}")
            print(f"   - Resource: {result['resource_type']}")
            print(f"   - Status: {result['status']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_tenant_costs():
    """Obtener costos del tenant"""
    print("\n🧪 Testing GET /api/costs/usage/tenant/...")
    tenant_id = str(uuid.uuid4())
    try:
        response = requests.get(
            f"{BASE_URL}/api/costs/usage/tenant/{tenant_id}",
            params={"billing_period": "2025-01"}
        )
        if response.status_code == 404:
            print(f"✅ Expected 404: No costs found for new tenant")
            return True
        elif response.status_code == 200:
            result = response.json()
            print(f"✅ Success: Got tenant costs")
            print(f"   - Total Cost: ${result['total_cost_usd']}")
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("=" * 60)
    print("COST MANAGEMENT API - ENDPOINT TESTS")
    print("=" * 60)
    
    # Esperar a que el servidor esté listo
    print("\n⏳ Waiting for API server to be ready...")
    import time
    for i in range(30):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=1)
            if response.status_code == 200:
                print(f"✅ API is ready!")
                break
        except:
            pass
        time.sleep(1)
    else:
        print("❌ API server not responding after 30 seconds")
        return
    
    # Ejecutar tests
    results = {
        "list_plans": test_list_plans(),
        "get_plan": test_get_plan(),
        "list_resources": test_list_resources(),
        "calculate_cost": test_calculate_cost(),
        "register_usage": test_register_usage(),
        "tenant_costs": test_tenant_costs(),
    }
    
    # Resumen
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed. Check output above.")
        print("\nFailed tests:")
        for test, result in results.items():
            if not result:
                print(f"   - {test}")

if __name__ == "__main__":
    main()
