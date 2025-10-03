#!/usr/bin/env python3
"""
Full test of AD report structure and endpoint functionality
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

async def test_full_ad_report_generation():
    """Test complete AD report generation with proper structure"""
    print("🔍 Testing full AD report generation with complex structure...")
    
    try:
        model = create_llm_instance(
            temperature=0.1,
            max_tokens=8192,
            dangerous_content_level="BLOCK_NONE"
        )
        
        system_prompt = """Je bent een professionele arbeidsdeskundige die een volledig gestructureerd AD rapport opstelt.
Je moet een JSON object maken dat exact voldoet aan het ADReport Pydantic schema.

Belangrijke regels:
1. Gebruik realistische testgegevens
2. Alle datums moeten in DD-MM-YYYY formaat
3. Het JSON object moet ALLE vereiste velden bevatten
4. Gebruik de exacte structuur zoals vereist door het Pydantic model
5. Geef ALLEEN een geldig JSON object terug, geen andere tekst."""

        user_prompt = """Maak een volledig gestructureerd AD rapport met deze EXACTE structuur:

{
  "titel": "Arbeidsdeskundig rapport - Test Persoon",
  "versie": "1.0",
  "template": "standaard",
  "opdrachtgever": {
    "naam_bedrijf": "Test Techniek BV",
    "contactpersoon": "J. Manager",
    "functie_contactpersoon": "HR Manager",
    "adres": "Industriestraat 123",
    "postcode": "1234 AB",
    "woonplaats": "Amsterdam",
    "telefoonnummer": "020-1234567",
    "email": "info@testtechniek.nl",
    "aard_bedrijf": "Technische dienstverlening",
    "omvang_bedrijf": "50 werknemers"
  },
  "werknemer": {
    "naam": "P.J. Werknemer",
    "geboortedatum": "15-03-1980",
    "adres": "Werknemerstraat 45",
    "postcode": "5678 CD",
    "woonplaats": "Utrecht",
    "telefoonnummer": "030-9876543",
    "email": "p.werknemer@email.nl"
  },
  "adviseur": {
    "naam": "Dr. A.B. Deskundige",
    "functie": "Gecertificeerd Register Arbeidsdeskundige",
    "adres": "Adviseurslaan 12",
    "postcode": "9876 XY",
    "woonplaats": "Den Haag",
    "telefoonnummer": "070-2468135",
    "email": "a.deskundige@advies.nl"
  },
  "onderzoek": {
    "datum_onderzoek": "01-11-2024",
    "datum_rapportage": "15-11-2024",
    "locatie_onderzoek": "Bedrijfslocatie Amsterdam"
  },
  "samenvatting_vraagstelling": [
    "Is werknemer geschikt voor eigen functie?",
    "Welke aanpassingen zijn mogelijk?"
  ],
  "samenvatting_conclusie": [
    "Beperkt geschikt voor eigen functie",
    "Aanpassingen in werktijden aanbevolen"
  ],
  "vraagstelling": [],
  "ondernomen_activiteiten": ["Dossieronderzoek", "Gesprek werknemer", "Werkplekbezoek"],
  "voorgeschiedenis": "Werknemer heeft rugklachten sinds incident in 2023",
  "verzuimhistorie": "Totaal 4 maanden verzuim in afgelopen jaar",
  "opleidingen": [],
  "arbeidsverleden_lijst": [],
  "bekwaamheden": {
    "computervaardigheden": "Goed",
    "taalvaardigheid": "Nederlands uitstekend",
    "rijbewijs": "B, geldig"
  },
  "belastbaarheid": {
    "datum_beoordeling": "05-11-2024",
    "beoordelaar": "Dr. A.B. Deskundige",
    "fml_rubrieken": [
      {
        "rubriek_nummer": "I",
        "rubriek_naam": "Tillen",
        "mate_beperking": "Beperkt",
        "items": [
          {
            "beschrijving": "Max 10 kg tillen"
          }
        ]
      }
    ]
  },
  "eigen_functie": {
    "naam_functie": "Technisch medewerker",
    "arbeidspatroon": "Fulltime, dagdienst",
    "overeenkomst": "Vast contract",
    "aantal_uren": "40 uur per week",
    "functieomschrijving": "Onderhoud en reparatie van technische installaties"
  },
  "functiebelasting": [],
  "gesprek_werkgever": {},
  "gesprek_werknemer": {},
  "geschiktheid_eigen_werk": [
    {
      "belastend_aspect": "Zwaar tillen",
      "belastbaarheid_werknemer": "Beperkt tot 10 kg",
      "conclusie": "Aanpassingen noodzakelijk"
    }
  ],
  "conclusie_eigen_werk": "Beperkt geschikt mits aanpassingen",
  "aanpassing_eigen_werk": "Beperking tillast, hulpmiddelen inzetten",
  "geschiktheid_ander_werk_intern": "Mogelijk binnen technische afdeling",
  "geschiktheid_ander_werk_extern": "Breed inzetbaar in technische sector",
  "visie_duurzaamheid": "Met aanpassingen duurzaam inzetbaar",
  "trajectplan": [
    {
      "actie": "Ergonomisch onderzoek werkplek",
      "verantwoordelijke": "Arbodienst",
      "termijn": "2 weken"
    }
  ],
  "conclusies": [
    {
      "conclusie": "Beperkt geschikt voor eigen functie",
      "toelichting": "Met aanpassingen goed functioneren mogelijk"
    }
  ],
  "vervolg": ["Implementatie aanpassingen", "Evaluatie na 3 maanden"]
}

Genereer exact dit JSON object."""
        
        response = model.generate_content([
            {"role": "system", "parts": [system_prompt]},
            {"role": "user", "parts": [user_prompt]}
        ])
        
        if hasattr(response, 'text') and response.text:
            print("✅ LLM generated structured response")
            
            # Parse JSON
            import re
            json_text = response.text.strip()
            json_match = re.search(r'\{.*\}', json_text, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                
            parsed_json = json.loads(json_text)
            print("✅ JSON parsing successful")
            
            # Validate with Pydantic
            ad_report = ADReport(**parsed_json)
            print("✅ Full Pydantic validation successful")
            
            # Test specific complex fields
            print(f"✅ Geschiktheid items: {len(ad_report.geschiktheid_eigen_werk)}")
            print(f"✅ Trajectplan items: {len(ad_report.trajectplan)}")
            print(f"✅ Conclusies items: {len(ad_report.conclusies)}")
            print(f"✅ FML rubrieken: {len(ad_report.belastbaarheid.fml_rubrieken)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Full AD report generation failed: {str(e)}")
        return False

async def main():
    """Run comprehensive AD report test"""
    print("🚀 Starting Comprehensive AD Report Test")
    print(f"📋 LLM Provider: {settings.LLM_PROVIDER}")
    print(f"📋 Anthropic Model: {settings.ANTHROPIC_MODEL}")
    print("=" * 60)
    
    success = await test_full_ad_report_generation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Comprehensive AD report generation test PASSED!")
        print("✅ System ready for production use")
    else:
        print("❌ Comprehensive test FAILED - check configuration")
        
if __name__ == "__main__":
    asyncio.run(main())