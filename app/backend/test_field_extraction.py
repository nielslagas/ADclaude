"""
Test the document field extractor with real case data.
"""

import sys
sys.path.insert(0, '/app')

from app.db.database_service import get_database_service
from app.utils.document_field_extractor import extract_from_case
import json

def main():
    db = get_database_service()
    case_id = "41a9fbc5-faaa-4d43-8010-dd51eb325c24"

    print("=" * 80)
    print("EXTRACTING STRUCTURED FIELDS FROM CASE DOCUMENTS")
    print("=" * 80)

    fields = extract_from_case(case_id, db)

    print(f"\n✅ Extracted {len(fields)} fields:\n")
    print(json.dumps(fields, indent=2, ensure_ascii=False))

    # Verify key fields
    print("\n" + "=" * 80)
    print("VERIFICATION - KEY FIELDS")
    print("=" * 80)

    key_fields = [
        'werkgever_naam',
        'werkgever_postcode',
        'contactpersoon_naam',
        'contactpersoon_email',
        'werknemer_naam',
        'geboortedatum',
        'werknemer_postcode',
        'functie_naam',
        'eerste_ziektedag'
    ]

    for field in key_fields:
        value = fields.get(field, '❌ NOT FOUND')
        status = "✅" if field in fields else "❌"
        print(f"{status} {field:25s}: {value}")

    print("\n" + "=" * 80)
    print(f"SUCCESS RATE: {len(fields)}/{len(key_fields)} key fields extracted")
    print("=" * 80)

if __name__ == "__main__":
    main()
