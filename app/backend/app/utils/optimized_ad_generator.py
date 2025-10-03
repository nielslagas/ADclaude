"""
Optimized AD Report Generator - Combines multiple sections per LLM call
Reduces from 18 calls to approximately 5-6 strategic calls
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.utils.llm_provider import create_llm_instance
from app.models.ad_report_structure import (
    ADReport, Bedrijfsgegevens, Contactgegevens, OnderzoekGegevens,
    Opleiding, Arbeidsverleden, Bekwaamheden, FMLRubriek, FMLRubriekItem,
    Belastbaarheid, FunctieGegevens, FunctieBelasting, GeschiktheidAnalyse,
    VraagstellingItem, ConclusieItem, TrajectplanItem, BeperkingMate
)

logger = logging.getLogger(__name__)

class OptimizedADGenerator:
    """Generates complete AD reports with optimized LLM calls"""
    
    def __init__(self, temperature: float = 0.2, max_tokens: int = 8000):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.llm = None
        
    def _get_llm(self):
        """Get or create LLM instance"""
        if not self.llm:
            self.llm = create_llm_instance(
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        return self.llm
        
    def generate_complete_report(self, context: str, case_data: Dict[str, Any]) -> ADReport:
        """
        Generate complete AD report with optimized LLM calls
        
        Args:
            context: Document context from RAG pipeline
            case_data: Case information
            
        Returns:
            Complete ADReport object
        """
        logger.info("Starting optimized AD report generation")
        
        # Initialize report structure
        report = self._initialize_report(case_data)
        
        # Generate sections in batches for efficiency
        # Batch 1: Metadata and basic info (gegevens sections)
        metadata_sections = self._generate_metadata_sections(context, case_data)
        self._update_report_metadata(report, metadata_sections)
        
        # Batch 2: Introduction sections (samenvatting, vraagstelling, activiteiten)
        intro_sections = self._generate_introduction_sections(context, case_data)
        self._update_report_introduction(report, intro_sections)
        
        # Batch 3: Data collection (voorgeschiedenis, werknemer info, belastbaarheid)
        data_sections = self._generate_data_sections(context, case_data)
        self._update_report_data(report, data_sections)
        
        # Batch 4: Analysis (geschiktheid, visie arbeidsdeskundige)
        analysis_sections = self._generate_analysis_sections(context, case_data)
        self._update_report_analysis(report, analysis_sections)
        
        # Batch 5: Conclusions and follow-up (conclusie, trajectplan, vervolg)
        conclusion_sections = self._generate_conclusion_sections(context, case_data)
        self._update_report_conclusions(report, conclusion_sections)
        
        logger.info("Completed optimized AD report generation")
        return report
        
    def _initialize_report(self, case_data: Dict[str, Any]) -> ADReport:
        """Initialize report with base data"""
        return ADReport(
            titel="Arbeidsdeskundig rapport",
            versie="1.0",
            template="standaard",
            opdrachtgever=Bedrijfsgegevens(
                naam_bedrijf=case_data.get('company_name', '[Te vullen]')
            ),
            werknemer=Contactgegevens(
                naam=case_data.get('client_name', '[Te vullen]')
            ),
            adviseur=Contactgegevens(
                naam="P.R.J. Peters",
                functie="Gecertificeerd Register Arbeidsdeskundige"
            ),
            onderzoek=OnderzoekGegevens(
                datum_onderzoek=datetime.now().strftime("%d-%m-%Y"),
                datum_rapportage=datetime.now().strftime("%d-%m-%Y")
            ),
            samenvatting_vraagstelling=[],
            samenvatting_conclusie=[],
            vraagstelling=[],
            ondernomen_activiteiten=[],
            voorgeschiedenis="",
            verzuimhistorie="",
            opleidingen=[],
            arbeidsverleden_lijst=[],
            bekwaamheden=Bekwaamheden(),
            belastbaarheid=Belastbaarheid(
                datum_beoordeling="",
                beoordelaar="",
                fml_rubrieken=[]
            ),
            eigen_functie=FunctieGegevens(
                naam_functie="",
                arbeidspatroon="",
                overeenkomst="",
                aantal_uren="",
                functieomschrijving=""
            ),
            functiebelasting=[],
            geschiktheid_eigen_werk=[],
            conclusie_eigen_werk="",
            aanpassing_eigen_werk="",
            geschiktheid_ander_werk_intern="",
            geschiktheid_ander_werk_extern="",
            visie_duurzaamheid="",
            trajectplan=[],
            conclusies=[],
            vervolg=[]
        )
        
    def _generate_metadata_sections(self, context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata sections (werkgever, werknemer, adviseur gegevens)"""
        prompt = f"""
        Analyseer de documenten en genereer de volgende secties voor een arbeidsdeskundig rapport.
        
        Context documenten:
        {context[:4000]}
        
        Case informatie:
        - Client: {case_data.get('client_name', 'Onbekend')}
        - Werkgever: {case_data.get('company_name', 'Onbekend')}
        
        Genereer JSON met de volgende structuur:
        {{
            "werkgever": {{
                "naam_bedrijf": "Bedrijfsnaam",
                "contactpersoon": "Naam contactpersoon",
                "functie_contactpersoon": "Functie",
                "adres": "Straatnaam en nummer",
                "postcode": "Postcode",
                "woonplaats": "Plaats",
                "telefoonnummer": "Telefoonnummer",
                "email": "Email adres",
                "aard_bedrijf": "Beschrijving bedrijfsactiviteiten",
                "omvang_bedrijf": "Omvang/locaties",
                "aantal_werknemers": "Aantal medewerkers",
                "website": "Website URL"
            }},
            "werknemer": {{
                "naam": "Volledige naam",
                "geboortedatum": "DD-MM-JJJJ",
                "adres": "Straatnaam en nummer",
                "postcode": "Postcode",
                "woonplaats": "Plaats",
                "telefoonnummer": "Telefoonnummer",
                "email": "Email adres"
            }}
        }}
        
        BELANGRIJK: Baseer alle informatie op de documenten. Gebruik "Niet beschikbaar" voor ontbrekende gegevens.
        """
        
        try:
            llm = self._get_llm()
            response = llm.generate_content([
                {"role": "system", "parts": ["Je bent een arbeidsdeskundige die gestructureerde rapporten maakt."]},
                {"role": "user", "parts": [prompt]}
            ])
            
            data = json.loads(response.text)
            logger.info("Generated metadata sections successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error generating metadata sections: {e}")
            return {}
            
    def _generate_introduction_sections(self, context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate introduction sections (samenvatting, vraagstelling, activiteiten)"""
        prompt = f"""
        Genereer de introductiesecties van het arbeidsdeskundig rapport.
        
        Context documenten:
        {context[:4000]}
        
        Genereer JSON met:
        {{
            "samenvatting_vraagstelling": [
                "Kan werknemer het eigen werk nog uitvoeren?",
                "Is het eigen werk met aanpassingen passend te maken?",
                "Kan werknemer ander werk bij eigen werkgever uitvoeren?",
                "Zijn er mogelijkheden voor externe re-integratie?"
            ],
            "samenvatting_conclusie": [
                "Hoofdconclusie regel 1",
                "Hoofdconclusie regel 2"
            ],
            "vraagstelling": [
                {{"vraag": "Kan werknemer het eigen werk nog uitvoeren?", "antwoord": null}},
                {{"vraag": "Is het eigen werk met aanpassingen passend te maken?", "antwoord": null}},
                {{"vraag": "Kan werknemer ander werk bij eigen werkgever uitvoeren?", "antwoord": null}},
                {{"vraag": "Zijn er mogelijkheden voor externe re-integratie?", "antwoord": null}}
            ],
            "ondernomen_activiteiten": [
                "Voorbereiding en dossieronderzoek",
                "Bestuderen medische informatie",
                "Gesprek met werknemer",
                "Gesprek met werkgever",
                "Werkplekonderzoek",
                "Rapportage opstellen"
            ]
        }}
        """
        
        try:
            llm = self._get_llm()
            response = llm.generate_content([
                {"role": "system", "parts": ["Je bent een arbeidsdeskundige die professionele rapporten schrijft."]},
                {"role": "user", "parts": [prompt]}
            ])
            
            data = json.loads(response.text)
            logger.info("Generated introduction sections successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error generating introduction sections: {e}")
            return {}
            
    def _generate_data_sections(self, context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data collection sections"""
        prompt = f"""
        Analyseer de documenten en genereer de gegevensverzameling secties.
        
        Context documenten:
        {context[:6000]}
        
        Genereer JSON met:
        {{
            "voorgeschiedenis": "Beschrijving dienstverband en achtergrond",
            "verzuimhistorie": "Uitvalmoment en verzuimverloop",
            "opleidingen": [
                {{"naam": "Opleiding", "richting": "Richting", "diploma_certificaat": "Diploma", "jaar": "Jaar"}}
            ],
            "arbeidsverleden": [
                {{"periode": "Van-tot", "werkgever": "Bedrijf", "functie": "Functietitel"}}
            ],
            "bekwaamheden": {{
                "computervaardigheden": "Niveau",
                "taalvaardigheid": "Nederlands/Engels",
                "rijbewijs": "Categorie B",
                "overige": "Andere vaardigheden"
            }},
            "belastbaarheid": {{
                "datum_beoordeling": "DD-MM-JJJJ",
                "beoordelaar": "Naam bedrijfsarts",
                "rubrieken": [
                    {{
                        "rubriek": "I: Persoonlijk functioneren",
                        "mate": "Beperkt/Niet beperkt",
                        "items": ["Concentratie beperkt", "Aandacht verdelen moeilijk"]
                    }},
                    {{
                        "rubriek": "II: Sociaal functioneren",
                        "mate": "Niet beperkt",
                        "items": []
                    }},
                    {{
                        "rubriek": "VI: Werktijden",
                        "mate": "Beperkt",
                        "items": ["Maximaal 6 uur per dag"]
                    }}
                ],
                "prognose": "Verwachting voor herstel"
            }},
            "eigen_functie": {{
                "naam": "Functietitel",
                "arbeidspatroon": "Dagvenster",
                "overeenkomst": "Vast/Tijdelijk",
                "uren": "32 uur",
                "salaris": "€ bedrag",
                "omschrijving": "Functieomschrijving",
                "belasting": [
                    {{"taak": "Administratieve taken", "percentage": "60%", "aspecten": "Concentratie, PC werk"}},
                    {{"taak": "Overleg", "percentage": "40%", "aspecten": "Communicatie, samenwerking"}}
                ]
            }}
        }}
        """
        
        try:
            llm = self._get_llm()
            response = llm.generate_content([
                {"role": "system", "parts": ["Je bent een arbeidsdeskundige die gedetailleerde functieanalyses maakt."]},
                {"role": "user", "parts": [prompt]}
            ])
            
            data = json.loads(response.text)
            logger.info("Generated data sections successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error generating data sections: {e}")
            return {}
            
    def _generate_analysis_sections(self, context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis sections (geschiktheid, visie)"""
        prompt = f"""
        Genereer de arbeidsdeskundige analyse secties.
        
        Context documenten:
        {context[:6000]}
        
        Genereer JSON met:
        {{
            "geschiktheid_eigen_werk": [
                {{
                    "belastend_aspect": "Concentratie vereist voor administratie",
                    "belastbaarheid": "Beperkte concentratie door vermoeidheid",
                    "conclusie": "Overschrijding belastbaarheid"
                }},
                {{
                    "belastend_aspect": "8 uur per dag werken",
                    "belastbaarheid": "Maximaal 6 uur belastbaar",
                    "conclusie": "Urenbeperking aanwezig"
                }}
            ],
            "conclusie_eigen_werk": "Werknemer is momenteel ongeschikt voor eigen werk in volle omvang",
            "aanpassing_eigen_werk": "Aanpassingen: aangepaste werktijden, rustige werkplek, duidelijk takenpakket",
            "geschiktheid_ander_werk_intern": "Geen passende andere functies binnen bedrijf beschikbaar",
            "geschiktheid_ander_werk_extern": "Re-integratie 2e spoor mogelijk in administratieve functies",
            "zoekrichting": {{
                "uren": "24-32 uur",
                "niveau": "MBO+",
                "mobiliteit": "Regionaal",
                "sectoren": "Administratief, ondersteunend"
            }},
            "visie_duurzaamheid": "Met juiste aanpassingen en behandeling is duurzame terugkeer mogelijk",
            "gesprek_werkgever": {{
                "visie_functioneren": "Werknemer heeft moeite met takenoverzicht",
                "visie_duurzaamheid": "Bereid tot aanpassingen",
                "visie_reintegratie": "Voorkeur voor behoud werknemer"
            }},
            "gesprek_werknemer": {{
                "visie_beperkingen": "Vooral vermoeidheid en concentratieproblemen",
                "visie_werk": "Gemotiveerd voor terugkeer",
                "visie_reintegratie": "Voorkeur voor eigen werk met aanpassingen"
            }}
        }}
        """
        
        try:
            llm = self._get_llm()
            response = llm.generate_content([
                {"role": "system", "parts": ["Je bent een arbeidsdeskundige die geschiktheidsanalyses uitvoert."]},
                {"role": "user", "parts": [prompt]}
            ])
            
            data = json.loads(response.text)
            logger.info("Generated analysis sections successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error generating analysis sections: {e}")
            return {}
            
    def _generate_conclusion_sections(self, context: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conclusion sections"""
        prompt = f"""
        Genereer de conclusie en vervolgsecties van het rapport.
        
        Context documenten:
        {context[:4000]}
        
        Genereer JSON met:
        {{
            "trajectplan": [
                {{
                    "actie": "Takenpakket helder omschrijven",
                    "verantwoordelijke": "Werkgever en werknemer",
                    "termijn": "Binnen 2 weken",
                    "spoor": "1"
                }},
                {{
                    "actie": "Werkplekaanpassingen realiseren",
                    "verantwoordelijke": "Werkgever",
                    "termijn": "Binnen 4 weken",
                    "spoor": "1"
                }},
                {{
                    "actie": "Start re-integratietraject 2e spoor",
                    "verantwoordelijke": "Re-integratiebedrijf",
                    "termijn": "Direct",
                    "spoor": "2"
                }}
            ],
            "conclusies": [
                {{"conclusie": "Werknemer is momenteel ongeschikt voor eigen werk", "toelichting": "Door overschrijding belastbaarheid"}},
                {{"conclusie": "Eigen werk is mogelijk passend te maken", "toelichting": "Met aanpassingen en duidelijk takenpakket"}},
                {{"conclusie": "Geen ander passend werk intern", "toelichting": "Functies sluiten niet aan bij mogelijkheden"}},
                {{"conclusie": "2e spoor traject geïndiceerd", "toelichting": "Naast spoor 1 activiteiten"}}
            ],
            "vervolg": [
                "Rapport bespreken met werknemer en werkgever",
                "Implementeren voorgestelde aanpassingen",
                "Start re-integratietraject 2e spoor",
                "Evaluatie over 8 weken",
                "Rapport toevoegen aan dossier"
            ]
        }}
        """
        
        try:
            llm = self._get_llm()
            response = llm.generate_content([
                {"role": "system", "parts": ["Je bent een arbeidsdeskundige die heldere conclusies en adviezen formuleert."]},
                {"role": "user", "parts": [prompt]}
            ])
            
            data = json.loads(response.text)
            logger.info("Generated conclusion sections successfully")
            return data
            
        except Exception as e:
            logger.error(f"Error generating conclusion sections: {e}")
            return {}
            
    def _update_report_metadata(self, report: ADReport, data: Dict[str, Any]):
        """Update report with metadata sections"""
        if 'werkgever' in data:
            wg = data['werkgever']
            report.opdrachtgever = Bedrijfsgegevens(
                naam_bedrijf=wg.get('naam_bedrijf', ''),
                contactpersoon=wg.get('contactpersoon'),
                functie_contactpersoon=wg.get('functie_contactpersoon'),
                adres=wg.get('adres'),
                postcode=wg.get('postcode'),
                woonplaats=wg.get('woonplaats'),
                telefoonnummer=wg.get('telefoonnummer'),
                email=wg.get('email'),
                aard_bedrijf=wg.get('aard_bedrijf'),
                omvang_bedrijf=wg.get('omvang_bedrijf'),
                aantal_werknemers=wg.get('aantal_werknemers'),
                website=wg.get('website')
            )
            
        if 'werknemer' in data:
            wn = data['werknemer']
            report.werknemer = Contactgegevens(
                naam=wn.get('naam', ''),
                geboortedatum=wn.get('geboortedatum'),
                adres=wn.get('adres'),
                postcode=wn.get('postcode'),
                woonplaats=wn.get('woonplaats'),
                telefoonnummer=wn.get('telefoonnummer'),
                email=wn.get('email')
            )
            
    def _update_report_introduction(self, report: ADReport, data: Dict[str, Any]):
        """Update report with introduction sections"""
        if 'samenvatting_vraagstelling' in data:
            report.samenvatting_vraagstelling = data['samenvatting_vraagstelling']
            
        if 'samenvatting_conclusie' in data:
            report.samenvatting_conclusie = data['samenvatting_conclusie']
            
        if 'vraagstelling' in data:
            report.vraagstelling = [
                VraagstellingItem(
                    vraag=item.get('vraag', ''),
                    antwoord=item.get('antwoord')
                )
                for item in data['vraagstelling']
            ]
            
        if 'ondernomen_activiteiten' in data:
            report.ondernomen_activiteiten = data['ondernomen_activiteiten']
            
    def _update_report_data(self, report: ADReport, data: Dict[str, Any]):
        """Update report with data collection sections"""
        if 'voorgeschiedenis' in data:
            report.voorgeschiedenis = data['voorgeschiedenis']
            
        if 'verzuimhistorie' in data:
            report.verzuimhistorie = data['verzuimhistorie']
            
        if 'opleidingen' in data:
            report.opleidingen = [
                Opleiding(
                    naam=opl.get('naam', ''),
                    richting=opl.get('richting'),
                    diploma_certificaat=opl.get('diploma_certificaat'),
                    jaar=opl.get('jaar')
                )
                for opl in data['opleidingen']
            ]
            
        if 'arbeidsverleden' in data:
            report.arbeidsverleden_lijst = [
                Arbeidsverleden(
                    periode=av.get('periode', ''),
                    werkgever=av.get('werkgever', ''),
                    functie=av.get('functie', '')
                )
                for av in data['arbeidsverleden']
            ]
            
        if 'bekwaamheden' in data:
            bek = data['bekwaamheden']
            report.bekwaamheden = Bekwaamheden(
                computervaardigheden=bek.get('computervaardigheden'),
                taalvaardigheid=bek.get('taalvaardigheid'),
                rijbewijs=bek.get('rijbewijs'),
                overige=bek.get('overige')
            )
            
        if 'belastbaarheid' in data:
            bel = data['belastbaarheid']
            rubrieken = []
            for rub in bel.get('rubrieken', []):
                items = [
                    FMLRubriekItem(beschrijving=item)
                    for item in rub.get('items', [])
                ]
                rubrieken.append(FMLRubriek(
                    rubriek_nummer=rub.get('rubriek', 'I').split(':')[0],
                    rubriek_naam=rub.get('rubriek', ''),
                    mate_beperking=self._parse_beperking_mate(rub.get('mate', 'Niet beperkt')),
                    items=items
                ))
            
            report.belastbaarheid = Belastbaarheid(
                datum_beoordeling=bel.get('datum_beoordeling', ''),
                beoordelaar=bel.get('beoordelaar', ''),
                fml_rubrieken=rubrieken,
                prognose=bel.get('prognose')
            )
            
        if 'eigen_functie' in data:
            ef = data['eigen_functie']
            report.eigen_functie = FunctieGegevens(
                naam_functie=ef.get('naam', ''),
                arbeidspatroon=ef.get('arbeidspatroon', ''),
                overeenkomst=ef.get('overeenkomst', ''),
                aantal_uren=ef.get('uren', ''),
                salaris=ef.get('salaris'),
                functieomschrijving=ef.get('omschrijving', '')
            )
            
            if 'belasting' in ef:
                report.functiebelasting = [
                    FunctieBelasting(
                        taak=fb.get('taak', ''),
                        percentage=fb.get('percentage', ''),
                        belastende_aspecten=fb.get('aspecten', '')
                    )
                    for fb in ef['belasting']
                ]
                
    def _update_report_analysis(self, report: ADReport, data: Dict[str, Any]):
        """Update report with analysis sections"""
        if 'geschiktheid_eigen_werk' in data:
            report.geschiktheid_eigen_werk = [
                GeschiktheidAnalyse(
                    belastend_aspect=ga.get('belastend_aspect', ''),
                    belastbaarheid_werknemer=ga.get('belastbaarheid', ''),
                    conclusie=ga.get('conclusie', '')
                )
                for ga in data['geschiktheid_eigen_werk']
            ]
            
        if 'conclusie_eigen_werk' in data:
            report.conclusie_eigen_werk = data['conclusie_eigen_werk']
            
        if 'aanpassing_eigen_werk' in data:
            report.aanpassing_eigen_werk = data['aanpassing_eigen_werk']
            
        if 'geschiktheid_ander_werk_intern' in data:
            report.geschiktheid_ander_werk_intern = data['geschiktheid_ander_werk_intern']
            
        if 'geschiktheid_ander_werk_extern' in data:
            report.geschiktheid_ander_werk_extern = data['geschiktheid_ander_werk_extern']
            
        if 'zoekrichting' in data:
            report.zoekrichting = data['zoekrichting']
            
        if 'visie_duurzaamheid' in data:
            report.visie_duurzaamheid = data['visie_duurzaamheid']
            
        if 'gesprek_werkgever' in data:
            report.gesprek_werkgever = data['gesprek_werkgever']
            
        if 'gesprek_werknemer' in data:
            report.gesprek_werknemer = data['gesprek_werknemer']
            
    def _update_report_conclusions(self, report: ADReport, data: Dict[str, Any]):
        """Update report with conclusion sections"""
        if 'trajectplan' in data:
            report.trajectplan = [
                TrajectplanItem(
                    actie=tp.get('actie', ''),
                    verantwoordelijke=tp.get('verantwoordelijke'),
                    termijn=tp.get('termijn'),
                    spoor=tp.get('spoor')
                )
                for tp in data['trajectplan']
            ]
            
        if 'conclusies' in data:
            report.conclusies = [
                ConclusieItem(
                    conclusie=c.get('conclusie', ''),
                    toelichting=c.get('toelichting')
                )
                for c in data['conclusies']
            ]
            
        if 'vervolg' in data:
            report.vervolg = data['vervolg']
            
    def _parse_beperking_mate(self, mate_str: str) -> BeperkingMate:
        """Parse beperking mate from string"""
        mate_lower = mate_str.lower()
        if 'sterk' in mate_lower:
            return BeperkingMate.STERK_BEPERKT
        elif 'beperkt' in mate_lower and 'niet' not in mate_lower:
            return BeperkingMate.BEPERKT
        else:
            return BeperkingMate.NIET_BEPERKT