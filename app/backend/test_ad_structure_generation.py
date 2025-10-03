#!/usr/bin/env python3
"""
Test script voor AD structure generation endpoint
"""
import sys
import os
import json
import asyncio
from datetime import datetime

# Add the app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from app.utils.llm_provider import create_llm_instance
from app.models.ad_report_structure import ADReport, ADReportGenerator
from app.core.config import settings

async def test_llm_basic():
    """Test basis LLM functionaliteit"""
    print("🧪 Testing basic LLM functionality...")
    
    try:
        model = create_llm_instance(
            temperature=0.1,
            max_tokens=1000,
            dangerous_content_level="BLOCK_NONE"
        )
        
        test_response = model.generate_content([
            {"role": "system", "parts": ["Je bent een hulpzame assistent."]},
            {"role": "user", "parts": ["Zeg gewoon 'Test succesvol' als je dit kunt lezen."]}
        ])
        
        if hasattr(test_response, 'text') and test_response.text:
            print(f"✅ LLM response: {test_response.text}")
            return True
        else:
            print(f"❌ Unexpected response format: {type(test_response)}")
            return False
            
    except Exception as e:
        print(f"❌ LLM test failed: {str(e)}")
        return False

def test_pydantic_model():
    """Test Pydantic ADReport model"""
    print("\n🧪 Testing Pydantic ADReport model...")
    
    try:
        # Test empty report creation
        empty_report = ADReportGenerator.create_empty_report()
        print("✅ Empty ADReport created successfully")
        
        # Test model validation with minimal data
        test_data = {
            "titel": "Test rapport",
            "versie": "1.0",
            "template": "standaard",
            "opdrachtgever": {
                "naam_bedrijf": "Test BV"
            },
            "werknemer": {
                "naam": "Jan Test"
            },
            "adviseur": {
                "naam": "Test Adviseur"
            },
            "onderzoek": {
                "datum_onderzoek": datetime.now().strftime("%d-%m-%Y"),
                "datum_rapportage": datetime.now().strftime("%d-%m-%Y")
            },
            "samenvatting_vraagstelling": ["Test vraag"],
            "samenvatting_conclusie": ["Test conclusie"],
            "vraagstelling": [],
            "ondernomen_activiteiten": [],
            "voorgeschiedenis": "Test",
            "verzuimhistorie": "Test", 
            "opleidingen": [],
            "arbeidsverleden_lijst": [],
            "bekwaamheden": {
                "computervaardigheden": "Test",
                "taalvaardigheid": "Test",
                "rijbewijs": "Test"
            },
            "belastbaarheid": {
                "datum_beoordeling": datetime.now().strftime("%d-%m-%Y"),
                "beoordelaar": "Test",
                "fml_rubrieken": []
            },
            "eigen_functie": {
                "naam_functie": "Test",
                "arbeidspatroon": "Test", 
                "overeenkomst": "Test",
                "aantal_uren": "Test",
                "functieomschrijving": "Test"
            },
            "functiebelasting": [],
            "gesprek_werkgever": {},
            "gesprek_werknemer": {},
            "geschiktheid_eigen_werk": [],
            "conclusie_eigen_werk": "Test",
            "aanpassing_eigen_werk": "Test",
            "geschiktheid_ander_werk_intern": "Test",
            "geschiktheid_ander_werk_extern": "Test",
            "visie_duurzaamheid": "Test",
            "trajectplan": [],
            "conclusies": [],
            "vervolg": []
        }
        
        # Validate the model
        ad_report = ADReport(**test_data)
        print("✅ ADReport Pydantic validation successful")
        
        # Convert back to dict
        report_dict = ad_report.model_dump()
        print(f"✅ Model conversion successful - {len(report_dict)} fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Pydantic test failed: {str(e)}")
        return False

async def test_full_json_generation():
    """Test volledige JSON structuur generatie"""
    print("\n🧪 Testing full JSON structure generation...")
    
    try:
        model = create_llm_instance(
            temperature=0.1,
            max_tokens=4000,
            dangerous_content_level="BLOCK_NONE"
        )
        
        system_prompt = """Je bent een professionele arbeidsdeskundige. 
Genereer een JSON object voor een AD rapport met de basis velden.
Geef ALLEEN een geldig JSON object terug, geen andere tekst."""

        user_prompt = """Maak een eenvoudig AD rapport JSON object met deze structuur:
{
  "titel": "Test Arbeidsdeskundig rapport",
  "versie": "1.0",
  "template": "standaard",
  "opdrachtgever": {
    "naam_bedrijf": "Test Bedrijf BV",
    "contactpersoon": "J. Test",
    "functie_contactpersoon": "HR Manager",
    "adres": "Teststraat 1",
    "postcode": "1234 AB",
    "woonplaats": "Amsterdam",
    "telefoonnummer": "020-1234567",
    "email": "test@test.nl",
    "aard_bedrijf": "Techniek",
    "omvang_bedrijf": "50 werknemers"
  },
  "werknemer": {
    "naam": "P. Werknemer",
    "geboortedatum": "01-01-1980",
    "adres": "Werknemerlaan 1",
    "postcode": "5678 CD",
    "woonplaats": "Utrecht",
    "telefoonnummer": "030-7654321",
    "email": "werknemer@email.nl"
  },
  "adviseur": {
    "naam": "A. Deskundige",
    "functie": "Gecertificeerd Register Arbeidsdeskundige",
    "adres": "Adviseurstraat 1",
    "postcode": "9876 ZX",
    "woonplaats": "Den Haag",
    "telefoonnummer": "070-9876543",
    "email": "adviseur@advies.nl"
  }
}

Genereer dit exacte JSON object."""
        
        response = model.generate_content([
            {"role": "system", "parts": [system_prompt]},
            {"role": "user", "parts": [user_prompt]}
        ])
        
        if hasattr(response, 'text') and response.text:
            print(f"📤 LLM Response (first 200 chars): {response.text[:200]}...")
            
            # Try to parse JSON
            try:
                import re
                json_text = response.text.strip()
                
                # Extract JSON if wrapped
                json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group()
                
                parsed_json = json.loads(json_text)
                print("✅ JSON parsing successful")
                print(f"📊 Generated structure has {len(parsed_json)} top-level fields")
                
                # Check key fields
                required_keys = ["opdrachtgever", "werknemer", "adviseur"]
                for key in required_keys:
                    if key in parsed_json:
                        print(f"✅ Found {key} section")
                    else:
                        print(f"❌ Missing {key} section")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {str(e)}")
                print(f"Raw response: {response.text}")
                return False
        else:
            print("❌ No text in LLM response")
            return False
            
    except Exception as e:
        print(f"❌ Full JSON generation test failed: {str(e)}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Starting AD Structure Generation Tests")
    print(f"📋 LLM Provider: {settings.LLM_PROVIDER}")
    print(f"📋 Anthropic Model: {settings.ANTHROPIC_MODEL}")
    print("=" * 50)
    
    # Run tests
    tests = [
        ("Basic LLM", test_llm_basic()),
        ("Pydantic Model", test_pydantic_model()),
        ("JSON Generation", test_full_json_generation())
    ]
    
    results = []
    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY:")
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Ready to test in frontend.")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    asyncio.run(main())