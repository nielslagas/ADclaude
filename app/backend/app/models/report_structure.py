"""
Pydantic models for structured report output.
Defines the exact structure that LLM should generate for consistent formatting.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class TableRowType(str, Enum):
    HEADER = "header"
    DATA = "data"

class TableRow(BaseModel):
    type: TableRowType = TableRowType.DATA
    cells: List[str] = Field(..., description="List of cell contents")

class Table(BaseModel):
    headers: List[str] = Field(..., description="Table header columns")
    rows: List[List[str]] = Field(..., description="Table data rows")
    caption: Optional[str] = Field(None, description="Optional table caption")

class TextBlock(BaseModel):
    content: str = Field(..., description="Text content")
    type: str = Field("paragraph", description="Type: paragraph, list, emphasis")

class ReportSection(BaseModel):
    title: str = Field(..., description="Section title with numbering (e.g., '3.2 Gegevens werkgever')")
    content: List[TextBlock] = Field(default_factory=list, description="Text blocks in section")
    tables: List[Table] = Field(default_factory=list, description="Tables in section")
    subsections: Dict[str, 'ReportSection'] = Field(default_factory=dict, description="Nested subsections")

class GegevensWerkgever(BaseModel):
    """3.2 Gegevens werkgever section structure"""
    aard_bedrijf: str = Field(..., description="Type of business and activities")
    omvang_bedrijf: str = Field(..., description="Size and locations of company")
    aantal_werknemers: str = Field(..., description="Number of employees")
    functies_expertises: str = Field(..., description="Available functions and expertise")
    overige_informatie: str = Field(..., description="Additional company information")

class GegevensWerknemer(BaseModel):
    """3.3 Gegevens werknemer section structure"""
    opleidingen: List[Dict[str, str]] = Field(default_factory=list, description="Education and courses")
    arbeidsverleden: List[Dict[str, str]] = Field(default_factory=list, description="Work history")
    bekwaamheden: Dict[str, str] = Field(default_factory=dict, description="Skills and capabilities")

class BelastbaarheidItem(BaseModel):
    rubriek: str = Field(..., description="FML category (e.g., 'Rubriek I: Persoonlijk functioneren')")
    aspecten: List[str] = Field(default_factory=list, description="Specific limitations or capabilities")
    mate_beperking: str = Field(..., description="Level of limitation: Niet beperkt, Beperkt, Sterk beperkt")

class Belastbaarheid(BaseModel):
    """3.4 Belastbaarheid van werknemer section structure"""
    datum_beoordeling: str = Field(..., description="Date of FML assessment")
    beoordelaar: str = Field(..., description="Name of assessing professional")
    beperkingen: List[BelastbaarheidItem] = Field(default_factory=list, description="List of limitations")
    prognose: Optional[str] = Field(None, description="Prognosis of capability development")

class FunctieGegevens(BaseModel):
    """Function details structure"""
    naam_functie: str = Field(..., description="Job title")
    arbeidspatroon: str = Field(..., description="Work pattern/schedule")
    overeenkomst: str = Field(..., description="Contract type")
    aantal_uren: str = Field(..., description="Number of hours per week")
    salaris: Optional[str] = Field(None, description="Salary information")

class FunctieBelasting(BaseModel):
    """Function workload structure"""
    taak: str = Field(..., description="Task description")
    percentage: str = Field(..., description="Percentage of time spent")
    belastende_aspecten: str = Field(..., description="Demanding aspects of the task")

class EigenFunctie(BaseModel):
    """3.5 Eigen functie werknemer section structure"""
    functie_gegevens: FunctieGegevens = Field(..., description="Basic function information")
    functieomschrijving: str = Field(..., description="Detailed job description")
    functiebelasting: List[FunctieBelasting] = Field(default_factory=list, description="Workload breakdown")

class GeschiktheidAnalyse(BaseModel):
    """Analysis of suitability for work"""
    belastend_aspect: str = Field(..., description="Demanding aspect of work")
    belastbaarheid_werknemer: str = Field(..., description="Employee's capability")
    match_niveau: str = Field(..., description="Suitability level: Voldoende, Onvoldoende, Gedeeltelijk")

class Conclusie(BaseModel):
    """Conclusion structure"""
    eigen_werk: str = Field(..., description="Suitability for current job")
    eigen_werk_aanpassingen: str = Field(..., description="Suitability with adjustments")
    ander_werk_intern: str = Field(..., description="Suitability for other work at same employer")
    extern_werk: str = Field(..., description="Suitability for work elsewhere")

class Vervolgstap(BaseModel):
    """Follow-up step"""
    actie: str = Field(..., description="Action to be taken")
    verantwoordelijke: str = Field(..., description="Responsible party")
    termijn: Optional[str] = Field(None, description="Timeframe")

class StructuredReport(BaseModel):
    """Complete structured report model"""
    # Header information
    titel: str = Field("Arbeidsdeskundig rapport", description="Report title")
    werknemer_naam: str = Field(..., description="Employee name")
    werkgever_naam: str = Field(..., description="Employer name")
    datum_onderzoek: str = Field(..., description="Investigation date")
    datum_rapportage: str = Field(..., description="Report date")
    
    # Main sections
    samenvatting: Dict[str, str] = Field(default_factory=dict, description="Executive summary")
    vraagstelling: List[str] = Field(default_factory=list, description="Research questions")
    conclusie: Conclusie = Field(..., description="Main conclusions")
    
    # Detailed sections
    ondernomen_activiteiten: List[str] = Field(default_factory=list, description="Activities undertaken")
    voorgeschiedenis: str = Field(..., description="Background and history")
    gegevens_werkgever: GegevensWerkgever = Field(..., description="Employer information")
    gegevens_werknemer: GegevensWerknemer = Field(..., description="Employee information") 
    belastbaarheid: Belastbaarheid = Field(..., description="Functional capacity assessment")
    eigen_functie: EigenFunctie = Field(..., description="Current job analysis")
    
    # Analysis sections
    geschiktheid_analyses: List[GeschiktheidAnalyse] = Field(default_factory=list, description="Suitability analyses")
    aanpassingsmogelijkheden: List[str] = Field(default_factory=list, description="Possible adjustments")
    interne_alternatieven: List[str] = Field(default_factory=list, description="Internal alternatives")
    externe_mogelijkheden: List[str] = Field(default_factory=list, description="External possibilities")
    
    # Planning
    trajectplan: List[Vervolgstap] = Field(default_factory=list, description="Action plan")
    vervolg: List[str] = Field(default_factory=list, description="Next steps")

# Allow forward references for nested models
ReportSection.model_rebuild()