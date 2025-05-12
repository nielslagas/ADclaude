"""
Test the OpenAI key configuration in the actual environment.
"""
import os
import sys
from openai import OpenAI

# Get API key from environment or settings
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

print(f"API key length: {len(OPENAI_API_KEY)}")
print(f"API key available: {'Yes' if OPENAI_API_KEY else 'No'}")

# Try with environment key
try:
    print("\nTrying with environment key...")
    client = OpenAI(api_key=OPENAI_API_KEY)
    models = client.models.list()
    print(f"SUCCESS! Found {len(models.data)} models")
    print("First few models:")
    for model in models.data[:3]:
        print(f"- {model.id}")
except Exception as e:
    print(f"ERROR with environment key: {str(e)}")