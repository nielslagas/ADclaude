"""
AD Content Generator - Uses LLM to generate content for AD report sections
Based on the standardized AD report structure
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.utils.llm_provider import create_llm_instance
from app.models.ad_report_structure import (
    ADReport,
    ADReportGenerator,
    Contactgegevens,
    Bedrijfsgegevens,
    OnderzoekGegevens,
    Opleiding,
    Arbeidsverleden,
    Bekwaamheden,
    FMLRubriek,
    FMLRubriekItem,
    BeperkingMate,
    Belastbaarheid,
    FunctieGegevens,
    FunctieBelasting,
    GeschiktheidAnalyse,
    VraagstellingItem,
    ConclusieItem,
    TrajectplanItem
)

logger = logging.getLogger(__name__)

class ADContentGenerator:
    """Generates content for AD report sections using LLM"""
    
    def __init__(self, llm_provider: str = None):
        """
        Initialize content generator
        
        Args:
            llm_provider: Optional LLM provider override
        """
        self.llm_provider = llm_provider
        
    async def generate_complete_report(
        self, 
        context: str,
        case_data: Optional[Dict[str, Any]] = None
    ) -> ADReport:
        """
        Generate complete AD report from document context
        
        Args:
            context: Document context containing all relevant information
            case_data: Optional case metadata
            
        Returns:
            Complete ADReport structure
        """
        logger.info("Starting AD report generation")
        
        # Start with empty report structure
        report = ADReportGenerator.create_empty_report()
        
        # Update with case data if provided
        if case_data:
            if 'client_name' in case_data:
                report.werknemer.naam = case_data['client_name']
            if 'company_name' in case_data:
                report.opdrachtgever.naam_bedrijf = case_data['company_name']
        
        # Generate each section
        try:
            # Basic data sections
            report = await self._generate_basic_data(report, context)
            
            # Summary sections
            report = await self._generate_summary(report, context)
            
            # Main content sections
            report = await self._generate_questions(report, context)
            report = await self._generate_activities(report, context)
            report = await self._generate_history(report, context)
            report = await self._generate_employee_data(report, context)
            report = await self._generate_belastbaarheid(report, context)
            report = await self._generate_job_analysis(report, context)
            report = await self._generate_conversations(report, context)
            
            # Analysis sections
            report = await self._generate_suitability_analysis(report, context)
            report = await self._generate_adjustments(report, context)
            report = await self._generate_alternatives(report, context)
            
            # Planning sections
            report = await self._generate_trajectory_plan(report, context)
            report = await self._generate_conclusions(report, context)
            report = await self._generate_follow_up(report, context)
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            # Return partially filled report
            
        return report
    
    async def _generate_basic_data(self, report: ADReport, context: str) -> ADReport:
        """Generate basic data sections (contact info, company info)"""
        
        prompt = f"""
        Analyseer de documenten en extraheer de volgende gegevens in JSON formaat:
        
        {{
            "opdrachtgever": {{
                "naam_bedrijf": "Bedrijfsnaam",
                "contactpersoon": "Naam contactpersoon",
                "functie_contactpersoon": "Functie",
                "adres": "Adres",
                "postcode": "Postcode",
                "woonplaats": "Plaats",
                "telefoonnummer": "Telefoonnummer",
                "email": "E-mailadres",
                "aard_bedrijf": "Beschrijving bedrijfsactiviteiten",
                "omvang_bedrijf": "Omvang/locaties",
                "aantal_werknemers": "Aantal medewerkers",
                "functies_expertises": "Expertises en functies",
                "website": "Website URL"
            }},
            "werknemer": {{
                "naam": "Volledige naam",
                "geboortedatum": "DD-MM-JJJJ",
                "adres": "Adres",
                "postcode": "Postcode",
                "woonplaats": "Plaats",
                "telefoonnummer": "Telefoonnummer",
                "email": "E-mailadres"
            }},
            "adviseur": {{
                "naam": "Naam arbeidsdeskundige",
                "functie": "Functietitel",
                "telefoonnummer": "Telefoonnummer"
            }},
            "onderzoek": {{
                "datum_onderzoek": "DD-MM-JJJJ",
                "datum_rapportage": "DD-MM-JJJJ",
                "locatie_onderzoek": "Locatie"
            }}
        }}
        
        Context documenten:
        {context}
        
        Geef alleen de JSON output, geen andere tekst.
        """
        
        try:
            response = await self._generate_json(prompt)
            
            # Update report with extracted data
            if 'opdrachtgever' in response:
                for key, value in response['opdrachtgever'].items():
                    if hasattr(report.opdrachtgever, key) and value:
                        setattr(report.opdrachtgever, key, value)
                        
            if 'werknemer' in response:
                for key, value in response['werknemer'].items():
                    if hasattr(report.werknemer, key) and value:
                        setattr(report.werknemer, key, value)
                        
            if 'adviseur' in response:
                for key, value in response['adviseur'].items():
                    if hasattr(report.adviseur, key) and value:
                        setattr(report.adviseur, key, value)
                        
            if 'onderzoek' in response:
                for key, value in response['onderzoek'].items():
                    if hasattr(report.onderzoek, key) and value:
                        setattr(report.onderzoek, key, value)
                        
        except Exception as e:
            logger.error(f"Error generating basic data: {str(e)}")
            
        return report
    
    async def _generate_summary(self, report: ADReport, context: str) -> ADReport:
        """Generate summary sections"""
        
        prompt = f"""
        Genereer een samenvatting voor het arbeidsdeskundig rapport in JSON formaat:
        
        {{
            "vraagstelling": [
                "Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?",
                "Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?",
                "Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?",
                "Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden?"
            ],
            "conclusie": [
                "Hoofdconclusie over geschiktheid eigen werk",
                "Conclusie over aanpassingsmogelijkheden",
                "Conclusie over ander werk bij eigen werkgever",
                "Conclusie over externe re-integratie"
            ]
        }}
        
        Baseer de conclusies op de volgende context:
        {context}
        
        Geef alleen de JSON output.
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'vraagstelling' in response:
                report.samenvatting_vraagstelling = response['vraagstelling']
                
            if 'conclusie' in response:
                report.samenvatting_conclusie = response['conclusie']
                
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            # Use default questions
            report.samenvatting_vraagstelling = [
                "Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?",
                "Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?",
                "Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?",
                "Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden?"
            ]
            
        return report
    
    async def _generate_belastbaarheid(self, report: ADReport, context: str) -> ADReport:
        """Generate FML belastbaarheid section"""
        
        prompt = f"""
        Analyseer de FML (Functionele Mogelijkhedenlijst) informatie en genereer JSON:
        
        {{
            "datum_beoordeling": "DD-MM-JJJJ",
            "beoordelaar": "Naam bedrijfsarts",
            "rubrieken": [
                {{
                    "rubriek_nummer": "I",
                    "rubriek_naam": "Persoonlijk functioneren",
                    "mate_beperking": "Niet beperkt/Beperkt/Sterk beperkt",
                    "items": [
                        {{
                            "nummer": "2.",
                            "beschrijving": "Verdelen van de aandacht: [specifieke beschrijving]",
                            "specifieke_voorwaarden": "Voorwaarden indien van toepassing"
                        }}
                    ]
                }},
                {{
                    "rubriek_nummer": "II",
                    "rubriek_naam": "Sociaal functioneren",
                    "mate_beperking": "Niet beperkt/Beperkt/Sterk beperkt",
                    "items": []
                }},
                {{
                    "rubriek_nummer": "III",
                    "rubriek_naam": "Aanpassing aan fysieke omgevingseisen",
                    "mate_beperking": "Niet beperkt",
                    "items": []
                }},
                {{
                    "rubriek_nummer": "IV",
                    "rubriek_naam": "Dynamische handelingen",
                    "mate_beperking": "Niet beperkt/Beperkt",
                    "items": []
                }},
                {{
                    "rubriek_nummer": "V",
                    "rubriek_naam": "Statische houdingen",
                    "mate_beperking": "Niet beperkt/Beperkt",
                    "items": []
                }},
                {{
                    "rubriek_nummer": "VI",
                    "rubriek_naam": "Werktijden",
                    "mate_beperking": "Beperkt",
                    "items": [
                        {{
                            "beschrijving": "Energetische beperking van X uur per dag"
                        }}
                    ]
                }}
            ],
            "prognose": "Beschrijving van de prognose",
            "energetische_beperking": "X uur per dag"
        }}
        
        Context met FML informatie:
        {context}
        
        BELANGRIJK: 
        - Gebruik exact de 6 FML rubrieken (I t/m VI)
        - Alleen items toevoegen als er daadwerkelijk beperkingen zijn
        - Bij "Niet beperkt" geen items toevoegen
        
        Geef alleen de JSON output.
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'datum_beoordeling' in response:
                report.belastbaarheid.datum_beoordeling = response['datum_beoordeling']
                
            if 'beoordelaar' in response:
                report.belastbaarheid.beoordelaar = response['beoordelaar']
                
            if 'rubrieken' in response:
                fml_rubrieken = []
                for rubriek_data in response['rubrieken']:
                    items = []
                    if 'items' in rubriek_data:
                        for item_data in rubriek_data['items']:
                            items.append(FMLRubriekItem(
                                nummer=item_data.get('nummer'),
                                beschrijving=item_data.get('beschrijving', ''),
                                specifieke_voorwaarden=item_data.get('specifieke_voorwaarden')
                            ))
                    
                    fml_rubrieken.append(FMLRubriek(
                        rubriek_nummer=rubriek_data['rubriek_nummer'],
                        rubriek_naam=rubriek_data['rubriek_naam'],
                        mate_beperking=BeperkingMate(rubriek_data.get('mate_beperking', 'Niet beperkt')),
                        items=items
                    ))
                
                report.belastbaarheid.fml_rubrieken = fml_rubrieken
                
            if 'prognose' in response:
                report.belastbaarheid.prognose = response['prognose']
                
            if 'energetische_beperking' in response:
                report.belastbaarheid.energetische_beperking = response['energetische_beperking']
                
        except Exception as e:
            logger.error(f"Error generating belastbaarheid: {str(e)}")
            # Use template structure
            report.belastbaarheid.fml_rubrieken = ADReportGenerator.get_fml_rubrieken_template()
            
        return report
    
    async def _generate_json(self, prompt: str) -> Dict:
        """Generate JSON response from LLM"""
        
        try:
            llm = create_llm_instance(
                temperature=0.1,  # Low temperature for consistency
                max_tokens=4000
            )
            
            response = llm.generate_content([
                {
                    "role": "system",
                    "parts": ["Je bent een arbeidsdeskundige die gestructureerde JSON data genereert voor rapporten. Geef ALLEEN geldige JSON output, geen andere tekst."]
                },
                {
                    "role": "user",
                    "parts": [prompt]
                }
            ])
            
            # Parse JSON from response
            text = response.text.strip()
            
            # Try to find JSON in the response
            if text.startswith('{'):
                return json.loads(text)
            else:
                # Try to extract JSON from text
                import re
                json_match = re.search(r'\{.*\}', text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                    
        except Exception as e:
            logger.error(f"Error generating JSON: {str(e)}")
            
        return {}
    
    # Additional generator methods for other sections
    async def _generate_questions(self, report: ADReport, context: str) -> ADReport:
        """Generate research questions"""
        # Standard questions for AD report
        report.vraagstelling = [
            VraagstellingItem(vraag="Kan werknemer het eigen werk bij de eigen werkgever nog uitvoeren?"),
            VraagstellingItem(vraag="Zo nee, is het eigen werk met behulp van aanpassingen passend te maken?"),
            VraagstellingItem(vraag="Zo nee, kan werknemer ander werk bij de eigen werkgever uitvoeren?"),
            VraagstellingItem(vraag="Zo nee, zijn er mogelijkheden om werknemer naar ander werk te begeleiden?")
        ]
        return report
    
    async def _generate_activities(self, report: ADReport, context: str) -> ADReport:
        """Generate undertaken activities"""
        prompt = f"""
        Genereer een lijst van ondernomen activiteiten voor het arbeidsdeskundig onderzoek.
        
        Standaard activiteiten zijn:
        - Voorbereiding (dossieronderzoek) op [datum]
        - Bestuderen informatie van de bedrijfsarts
        - Gesprek met werknemer op [datum]
        - Gesprek met werkgever op [datum]
        - Rapportage opstellen op [datum]
        
        Context: {context}
        
        Geef een JSON array met strings:
        ["activiteit 1", "activiteit 2", ...]
        """
        
        try:
            response = await self._generate_json(prompt)
            if isinstance(response, list):
                report.ondernomen_activiteiten = response
            elif isinstance(response, dict) and 'activiteiten' in response:
                report.ondernomen_activiteiten = response['activiteiten']
        except:
            # Use defaults
            report.ondernomen_activiteiten = [
                "Voorbereiding (dossieronderzoek)",
                "Bestuderen medische informatie",
                "Gesprek met werknemer",
                "Gesprek met werkgever",
                "Rapportage opstellen"
            ]
            
        return report
    
    async def _generate_history(self, report: ADReport, context: str) -> ADReport:
        """Generate work history and medical history"""
        prompt = f"""
        Genereer voorgeschiedenis en verzuimhistorie in JSON:
        
        {{
            "voorgeschiedenis": "Beschrijving van dienstverband en achtergrond",
            "verzuimhistorie": "Beschrijving van verzuim, uitval datum, oorzaken"
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            report.voorgeschiedenis = response.get('voorgeschiedenis', '')
            report.verzuimhistorie = response.get('verzuimhistorie', '')
        except:
            pass
            
        return report
    
    async def _generate_employee_data(self, report: ADReport, context: str) -> ADReport:
        """Generate employee education and work history"""
        prompt = f"""
        Genereer werknemer gegevens in JSON:
        
        {{
            "opleidingen": [
                {{
                    "naam": "Opleidingsnaam",
                    "richting": "Richting",
                    "diploma_certificaat": "Diploma/Certificaat",
                    "jaar": "Jaar"
                }}
            ],
            "arbeidsverleden": [
                {{
                    "periode": "Van-Tot",
                    "werkgever": "Werkgever naam",
                    "functie": "Functietitel"
                }}
            ],
            "bekwaamheden": {{
                "computervaardigheden": "Niveau",
                "taalvaardigheid": "Nederlands/Engels",
                "rijbewijs": "Categorie B",
                "overige": "Andere vaardigheden"
            }}
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'opleidingen' in response:
                report.opleidingen = [
                    Opleiding(**opl) for opl in response['opleidingen']
                ]
                
            if 'arbeidsverleden' in response:
                report.arbeidsverleden_lijst = [
                    Arbeidsverleden(**werk) for werk in response['arbeidsverleden']
                ]
                
            if 'bekwaamheden' in response:
                report.bekwaamheden = Bekwaamheden(**response['bekwaamheden'])
                
        except Exception as e:
            logger.error(f"Error generating employee data: {str(e)}")
            
        return report
    
    async def _generate_job_analysis(self, report: ADReport, context: str) -> ADReport:
        """Generate job analysis"""
        prompt = f"""
        Genereer functie analyse in JSON:
        
        {{
            "functie": {{
                "naam_functie": "Functietitel",
                "arbeidspatroon": "Dagvenster/Wisselend",
                "overeenkomst": "Vast/Tijdelijk",
                "aantal_uren": "X uur per week",
                "salaris": "€ X per maand",
                "functieomschrijving": "Uitgebreide beschrijving"
            }},
            "belasting": [
                {{
                    "taak": "Taakomschrijving",
                    "percentage": "X%",
                    "belastende_aspecten": "Wat maakt het belastend"
                }}
            ]
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'functie' in response:
                report.eigen_functie = FunctieGegevens(**response['functie'])
                
            if 'belasting' in response:
                report.functiebelasting = [
                    FunctieBelasting(**item) for item in response['belasting']
                ]
                
        except Exception as e:
            logger.error(f"Error generating job analysis: {str(e)}")
            
        return report
    
    async def _generate_conversations(self, report: ADReport, context: str) -> ADReport:
        """Generate conversation summaries"""
        prompt = f"""
        Genereer gesprekverslagen in JSON:
        
        {{
            "gesprek_werkgever": {{
                "algemeen": "Algemene punten besproken",
                "visie_functioneren": "Visie op functioneren voor uitval",
                "visie_duurzaamheid": "Visie op duurzaamheid herplaatsing",
                "visie_reintegratie": "Visie op re-integratiemogelijkheden"
            }},
            "gesprek_werknemer": {{
                "visie_beperkingen": "Visie op eigen beperkingen",
                "visie_werk": "Visie op werk en re-integratie"
            }},
            "gesprek_gezamenlijk": "Samenvatting gezamenlijk gesprek"
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'gesprek_werkgever' in response:
                report.gesprek_werkgever = response['gesprek_werkgever']
                
            if 'gesprek_werknemer' in response:
                report.gesprek_werknemer = response['gesprek_werknemer']
                
            if 'gesprek_gezamenlijk' in response:
                report.gesprek_gezamenlijk = response['gesprek_gezamenlijk']
                
        except Exception as e:
            logger.error(f"Error generating conversations: {str(e)}")
            
        return report
    
    async def _generate_suitability_analysis(self, report: ADReport, context: str) -> ADReport:
        """Generate suitability analysis"""
        prompt = f"""
        Genereer geschiktheidsanalyse voor eigen werk in JSON:
        
        {{
            "analyses": [
                {{
                    "belastend_aspect": "Wat is belastend in het werk",
                    "belastbaarheid_werknemer": "Wat kan werknemer aan",
                    "conclusie": "Match/Geen match"
                }}
            ],
            "conclusie_eigen_werk": "Algemene conclusie over geschiktheid eigen werk"
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'analyses' in response:
                report.geschiktheid_eigen_werk = [
                    GeschiktheidAnalyse(**item) for item in response['analyses']
                ]
                
            if 'conclusie_eigen_werk' in response:
                report.conclusie_eigen_werk = response['conclusie_eigen_werk']
                
        except Exception as e:
            logger.error(f"Error generating suitability analysis: {str(e)}")
            
        return report
    
    async def _generate_adjustments(self, report: ADReport, context: str) -> ADReport:
        """Generate work adjustments"""
        prompt = f"""
        Beschrijf mogelijke aanpassingen voor het eigen werk.
        Denk aan: ergonomische aanpassingen, werktijden, takenpakket, werkplek, etc.
        
        Context: {context}
        """
        
        try:
            response = await self._generate_text(prompt)
            report.aanpassing_eigen_werk = response
        except:
            report.aanpassing_eigen_werk = "Te onderzoeken"
            
        return report
    
    async def _generate_alternatives(self, report: ADReport, context: str) -> ADReport:
        """Generate alternative work options"""
        prompt_intern = f"""
        Beschrijf mogelijkheden voor ander werk bij de eigen werkgever.
        
        Context: {context}
        """
        
        prompt_extern = f"""
        Beschrijf mogelijkheden voor werk bij een andere werkgever.
        Inclusief zoekrichting (aantal uren, mobiliteit, opleidingsniveau, affiniteit).
        
        Context: {context}
        """
        
        try:
            report.geschiktheid_ander_werk_intern = await self._generate_text(prompt_intern)
            report.geschiktheid_ander_werk_extern = await self._generate_text(prompt_extern)
        except:
            report.geschiktheid_ander_werk_intern = "Geen passende alternatieven gevonden"
            report.geschiktheid_ander_werk_extern = "Re-integratietraject tweede spoor adviseren"
            
        return report
    
    async def _generate_trajectory_plan(self, report: ADReport, context: str) -> ADReport:
        """Generate trajectory plan"""
        prompt = f"""
        Genereer trajectplan in JSON:
        
        {{
            "trajectplan": [
                {{
                    "actie": "Te ondernemen actie",
                    "verantwoordelijke": "Wie",
                    "termijn": "Wanneer",
                    "spoor": "1 of 2"
                }}
            ]
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'trajectplan' in response:
                report.trajectplan = [
                    TrajectplanItem(**item) for item in response['trajectplan']
                ]
        except:
            # Default plan
            report.trajectplan = [
                TrajectplanItem(
                    actie="Bespreek de rapportage met werknemer",
                    verantwoordelijke="Werkgever",
                    spoor="1"
                ),
                TrajectplanItem(
                    actie="Start re-integratie binnen spoor 1",
                    verantwoordelijke="Werkgever/Werknemer",
                    spoor="1"
                )
            ]
            
        return report
    
    async def _generate_conclusions(self, report: ADReport, context: str) -> ADReport:
        """Generate conclusions"""
        prompt = f"""
        Genereer conclusies in JSON:
        
        {{
            "conclusies": [
                {{
                    "conclusie": "Hoofdconclusie",
                    "toelichting": "Nadere toelichting indien nodig"
                }}
            ]
        }}
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            
            if 'conclusies' in response:
                report.conclusies = [
                    ConclusieItem(**item) for item in response['conclusies']
                ]
        except:
            # Use summary conclusions
            report.conclusies = [
                ConclusieItem(conclusie=c) for c in report.samenvatting_conclusie
            ]
            
        return report
    
    async def _generate_follow_up(self, report: ADReport, context: str) -> ADReport:
        """Generate follow-up steps"""
        prompt = f"""
        Genereer vervolgstappen als JSON array:
        ["stap 1", "stap 2", ...]
        
        Context: {context}
        """
        
        try:
            response = await self._generate_json(prompt)
            if isinstance(response, list):
                report.vervolg = response
        except:
            # Default follow-up
            report.vervolg = [
                "Het rapport wordt verstuurd aan werkgever en werknemer",
                "Het rapport wordt opgenomen in het werknemersdossier",
                "Het rapport wordt ter beschikking gesteld aan de bedrijfsarts"
            ]
            
        return report
    
    async def _generate_text(self, prompt: str) -> str:
        """Generate text response from LLM"""
        
        try:
            llm = create_llm_instance(
                temperature=0.3,
                max_tokens=2000
            )
            
            response = llm.generate_content([
                {
                    "role": "system",
                    "parts": ["Je bent een ervaren arbeidsdeskundige die professionele rapporten schrijft."]
                },
                {
                    "role": "user",
                    "parts": [prompt]
                }
            ])
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            return ""