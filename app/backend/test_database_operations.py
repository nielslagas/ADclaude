#!/usr/bin/env python3
"""
Test database operations specifically for update_report functionality
"""
import sys
import os
import json
from datetime import datetime

# Add the app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.db.database_service import DatabaseService

def test_database_connection():
    """Test basic database connectivity"""
    print("🔍 Testing database connection...")
    try:
        db = DatabaseService()
        print("✅ Database service initialized")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def test_update_report_method():
    """Test the update_report method signature"""
    print("🔍 Testing update_report method...")
    try:
        db = DatabaseService()
        
        # Test method signature without actual database operation
        import inspect
        sig = inspect.signature(db.update_report)
        params = list(sig.parameters.keys())
        
        print(f"✅ Method signature: update_report{sig}")
        print(f"✅ Parameters: {params}")
        
        expected_params = ['report_id', 'data']  # 'self' is not shown by inspect
        if params == expected_params:
            print("✅ Method signature is correct")
            return True
        else:
            print(f"❌ Expected {expected_params}, got {params}")
            return False
            
    except Exception as e:
        print(f"❌ Method inspection failed: {str(e)}")
        return False

def test_json_serialization():
    """Test JSON serialization with UUIDEncoder"""
    print("🔍 Testing JSON serialization...")
    try:
        import uuid
        from app.db.database_service import UUIDEncoder
        
        test_data = {
            "id": uuid.uuid4(),
            "timestamp": datetime.now(),
            "content": {
                "nested_uuid": uuid.uuid4(),
                "text": "Test content"
            }
        }
        
        json_str = json.dumps(test_data, cls=UUIDEncoder)
        parsed = json.loads(json_str)
        
        print("✅ JSON serialization with UUID/datetime works")
        return True
        
    except Exception as e:
        print(f"❌ JSON serialization failed: {str(e)}")
        return False

def main():
    """Run all database tests"""
    print("🚀 Starting Database Operations Test")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection()),
        ("Update Report Method", test_update_report_method()),
        ("JSON Serialization", test_json_serialization())
    ]
    
    print("\n" + "=" * 50)
    print("📊 DATABASE TESTS SUMMARY:")
    
    passed = 0
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(tests)} database tests passed")
    
    if passed == len(tests):
        print("🎉 All database tests passed!")
    else:
        print("⚠️ Some database tests failed.")

if __name__ == "__main__":
    main()