#!/usr/bin/env python3
"""
Simple test script to debug report generation
"""

import sys
import time
from app.utils.llm_provider import create_llm_instance

print("Starting simple report generation test...")
print("=" * 60)

try:
    # Create LLM instance
    print("1. Creating LLM instance...")
    model = create_llm_instance(
        temperature=0.1,
        max_tokens=500  # Small for testing
    )
    print("   ✓ LLM instance created")
    
    # Test with simple prompt
    print("\n2. Testing simple prompt...")
    simple_prompt = "Schrijf een korte samenvatting voor een arbeidsdeskundig rapport. Maximum 2 zinnen."
    
    start_time = time.time()
    response = model.generate_content([
        {"role": "user", "parts": [simple_prompt]}
    ])
    elapsed = time.time() - start_time
    
    print(f"   ✓ Response received in {elapsed:.2f} seconds")
    print(f"   Content: {response.text[:200] if hasattr(response, 'text') else str(response)[:200]}")
    
    # Test with larger context
    print("\n3. Testing with document context...")
    doc_prompt = """
    Genereer de sectie 'Belastbaarheid' voor een arbeidsdeskundig rapport.
    
    Context: Werknemer heeft rugklachten, kan max 4 uur werken, geen tillen boven 5kg.
    
    Schrijf een professionele paragraaf van maximaal 100 woorden.
    """
    
    start_time = time.time()
    response = model.generate_content([
        {"role": "system", "parts": ["Je bent een arbeidsdeskundige."]},
        {"role": "user", "parts": [doc_prompt]}
    ])
    elapsed = time.time() - start_time
    
    print(f"   ✓ Response received in {elapsed:.2f} seconds")
    print(f"   Content: {response.text[:200] if hasattr(response, 'text') else str(response)[:200]}")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed! LLM is working correctly.")
    
except Exception as e:
    print(f"\n❌ Error occurred: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)