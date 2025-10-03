"""
AD Report Structure - Standardized data model for Arbeidsdeskundig reports
Based on professional AD report format standards
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Enums for standardized values
class BeperkingMate(str, Enum):
    """Mate van beperking volgens FML standaard"""
    NIET_BEPERKT = "Niet beperkt"
    BEPERKT = "Beperkt"
    STERK_BEPERKT = "Sterk beperkt"

class GeschiktheidNiveau(str, Enum):
    """Geschiktheid niveau voor werk"""
    GESCHIKT = "Geschikt"
    ONGESCHIKT = "Ongeschikt"
    GEDEELTELIJK = "Gedeeltelijk geschikt"
    MET_AANPASSINGEN = "Geschikt met aanpassingen"

# Data models for report sections
class Contactgegevens(BaseModel):
    """Contact information structure"""
    naam: str
    functie: Optional[str] = None
    adres: Optional[str] = None
    postcode: Optional[str] = None
    woonplaats: Optional[str] = None
    telefoonnummer: Optional[str] = None
    email: Optional[str] = None
    geboortedatum: Optional[str] = None

class Bedrijfsgegevens(BaseModel):
    """Company information structure"""
    naam_bedrijf: str
    contactpersoon: Optional[str] = None
    functie_contactpersoon: Optional[str] = None
    adres: Optional[str] = None
    postcode: Optional[str] = None
    woonplaats: Optional[str] = None
    telefoonnummer: Optional[str] = None
    email: Optional[str] = None
    aard_bedrijf: Optional[str] = None
    omvang_bedrijf: Optional[str] = None
    aantal_werknemers: Optional[str] = None
    functies_expertises: Optional[str] = None
    website: Optional[str] = None

class OnderzoekGegevens(BaseModel):
    """Investigation metadata"""
    datum_onderzoek: str
    datum_rapportage: str
    locatie_onderzoek: Optional[str] = None

class Opleiding(BaseModel):
    """Education/training record"""
    naam: str
    richting: Optional[str] = None
    diploma_certificaat: Optional[str] = None
    jaar: Optional[str] = None

class Arbeidsverleden(BaseModel):
    """Work history record"""
    periode: str
    werkgever: str
    functie: str

class Bekwaamheden(BaseModel):
    """Skills and capabilities"""
    computervaardigheden: Optional[str] = None
    taalvaardigheid: Optional[str] = None
    rijbewijs: Optional[str] = None
    overige: Optional[str] = None

class FMLRubriekItem(BaseModel):
    """FML Rubriek detail item"""
    nummer: Optional[str] = None  # e.g., "2."
    beschrijving: str
    specifieke_voorwaarden: Optional[str] = None

class FMLRubriek(BaseModel):
    """FML Rubriek structure"""
    rubriek_nummer: str  # I, II, III, IV, V, VI
    rubriek_naam: str
    mate_beperking: BeperkingMate
    items: List[FMLRubriekItem] = Field(default_factory=list)
    toelichting: Optional[str] = None

class Belastbaarheid(BaseModel):
    """Functional capacity assessment (FML)"""
    datum_beoordeling: str
    beoordelaar: str
    fml_rubrieken: List[FMLRubriek]
    prognose: Optional[str] = None
    energetische_beperking: Optional[str] = None

class FunctieGegevens(BaseModel):
    """Job information"""
    naam_functie: str
    arbeidspatroon: str
    overeenkomst: str
    aantal_uren: str
    salaris: Optional[str] = None
    functieomschrijving: str

class FunctieBelasting(BaseModel):
    """Job workload analysis"""
    taak: str
    percentage: str
    belastende_aspecten: str

class GeschiktheidAnalyse(BaseModel):
    """Suitability analysis item"""
    belastend_aspect: str
    belastbaarheid_werknemer: str
    conclusie: str

class VraagstellingItem(BaseModel):
    """Research question"""
    vraag: str
    antwoord: Optional[str] = None

class ConclusieItem(BaseModel):
    """Conclusion item"""
    conclusie: str
    toelichting: Optional[str] = None

class TrajectplanItem(BaseModel):
    """Action plan item"""
    actie: str
    verantwoordelijke: Optional[str] = None
    termijn: Optional[str] = None
    spoor: Optional[str] = None  # "1" of "2"

# Main report structure
class ADReport(BaseModel):
    """Complete Arbeidsdeskundig Report Structure"""
    
    # Metadata
    titel: str = "Arbeidsdeskundig rapport"
    versie: str = "1.0"
    template: str = "standaard"  # Voor template keuze
    
    # Gegevens secties (tabellen)
    opdrachtgever: Bedrijfsgegevens
    werknemer: Contactgegevens
    adviseur: Contactgegevens
    onderzoek: OnderzoekGegevens
    
    # Samenvatting
    samenvatting_vraagstelling: List[str]
    samenvatting_conclusie: List[str]
    
    # Hoofdsecties
    # 1. Vraagstelling
    vraagstelling: List[VraagstellingItem]
    
    # 2. Ondernomen activiteiten
    ondernomen_activiteiten: List[str]
    
    # 3. Gegevensverzameling
    # 3.1 Voorgeschiedenis
    voorgeschiedenis: str
    verzuimhistorie: str
    
    # 3.2 Gegevens werkgever (al in opdrachtgever)
    
    # 3.3 Gegevens werknemer
    opleidingen: List[Opleiding]
    arbeidsverleden_lijst: List[Arbeidsverleden]
    bekwaamheden: Bekwaamheden
    
    # 3.4 Belastbaarheid
    belastbaarheid: Belastbaarheid
    
    # 3.5 Eigen functie
    eigen_functie: FunctieGegevens
    functiebelasting: List[FunctieBelasting]
    
    # 3.6 Gesprek werkgever
    gesprek_werkgever: Dict[str, str] = Field(default_factory=dict)
    # Keys: algemeen, visie_functioneren, visie_duurzaamheid, visie_reintegratie
    
    # 3.7 Gesprek werknemer  
    gesprek_werknemer: Dict[str, str] = Field(default_factory=dict)
    # Keys: visie_beperkingen, visie_werk, visie_reintegratie
    
    # 3.8 Gesprek gezamenlijk
    gesprek_gezamenlijk: Optional[str] = None
    
    # 4. Visie arbeidsdeskundige
    # 4.1 Geschiktheid eigen werk
    geschiktheid_eigen_werk: List[GeschiktheidAnalyse]
    conclusie_eigen_werk: str
    
    # 4.2 Aanpassing eigen werk
    aanpassing_eigen_werk: str
    
    # 4.3 Geschiktheid ander werk eigen werkgever
    geschiktheid_ander_werk_intern: str
    
    # 4.4 Geschiktheid ander werk andere werkgever
    geschiktheid_ander_werk_extern: str
    zoekrichting: Optional[Dict[str, str]] = None
    
    # 4.5 Visie duurzaamheid
    visie_duurzaamheid: str
    
    # 5. Trajectplan
    trajectplan: List[TrajectplanItem]
    
    # 6. Conclusie
    conclusies: List[ConclusieItem]
    
    # 7. Vervolg
    vervolg: List[str]
    
    # Optionele secties
    bijlagen: List[str] = Field(default_factory=list)
    opmerkingen: Optional[str] = None
    disclaimer: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "titel": "Arbeidsdeskundig rapport",
                "werknemer": {
                    "naam": "De heer A.C. Blonk",
                    "geboortedatum": "02-03-1965"
                },
                "opdrachtgever": {
                    "naam_bedrijf": "Versluys Groep / Bodegraven",
                    "contactpersoon": "Mevrouw Isabel Hurenkamp"
                }
            }
        }

# Helper class for generating report from context
class ADReportGenerator:
    """Helper to generate AD report structure from document context"""
    
    @staticmethod
    def create_empty_report() -> ADReport:
        """Create empty report structure with defaults"""
        return ADReport(
            opdrachtgever=Bedrijfsgegevens(naam_bedrijf="[Te vullen]"),
            werknemer=Contactgegevens(naam="[Te vullen]"),
            adviseur=Contactgegevens(naam="[Arbeidsdeskundige]"),
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
    
    @staticmethod
    def get_fml_rubrieken_template() -> List[FMLRubriek]:
        """Get standard FML rubrieken structure"""
        return [
            FMLRubriek(
                rubriek_nummer="I",
                rubriek_naam="Persoonlijk functioneren",
                mate_beperking=BeperkingMate.NIET_BEPERKT,
                items=[]
            ),
            FMLRubriek(
                rubriek_nummer="II", 
                rubriek_naam="Sociaal functioneren",
                mate_beperking=BeperkingMate.NIET_BEPERKT,
                items=[]
            ),
            FMLRubriek(
                rubriek_nummer="III",
                rubriek_naam="Aanpassing aan fysieke omgevingseisen",
                mate_beperking=BeperkingMate.NIET_BEPERKT,
                items=[]
            ),
            FMLRubriek(
                rubriek_nummer="IV",
                rubriek_naam="Dynamische handelingen",
                mate_beperking=BeperkingMate.NIET_BEPERKT,
                items=[]
            ),
            FMLRubriek(
                rubriek_nummer="V",
                rubriek_naam="Statische houdingen",
                mate_beperking=BeperkingMate.NIET_BEPERKT,
                items=[]
            ),
            FMLRubriek(
                rubriek_nummer="VI",
                rubriek_naam="Werktijden",
                mate_beperking=BeperkingMate.NIET_BEPERKT,
                items=[]
            )
        ]