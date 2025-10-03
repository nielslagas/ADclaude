"""
AD Report Renderer - Converts structured AD report data to formatted output
Supports multiple templates and output formats
"""
from typing import Dict, Any, Optional
from app.models.ad_report_structure import (
    ADReport, 
    FMLRubriek,
    BeperkingMate,
    GeschiktheidAnalyse,
    TrajectplanItem
)
from datetime import datetime
import json

class ADReportRenderer:
    """Renders AD Report data structure to various formats"""
    
    def __init__(self, template: str = "standaard"):
        """
        Initialize renderer with template choice
        
        Args:
            template: Template name (standaard, modern, compact)
        """
        self.template = template
        
    def render_markdown(self, report: ADReport) -> str:
        """
        Render report to Markdown format
        
        Args:
            report: ADReport data structure
            
        Returns:
            Formatted markdown string
        """
        md = []
        
        # Header
        md.append(f"**{report.titel}**")
        md.append(f"\t\t{report.werknemer.naam}\n")
        
        if report.adviseur.naam:
            md.append(f"{report.adviseur.naam}")
            if report.adviseur.functie:
                md.append(f"{report.adviseur.functie}")
        md.append("")
        
        # Subtitle
        md.append("**Arbeidsdeskundig re-integratieonderzoek**\n")
        
        # Gegevens opdrachtgever (tabel)
        md.append("**Gegevens opdrachtgever**\n")
        md.append("| Naam bedrijf | {} |".format(report.opdrachtgever.naam_bedrijf))
        md.append("| :---- | :---- |")
        if report.opdrachtgever.contactpersoon:
            md.append(f"| Contactpersoon | {report.opdrachtgever.contactpersoon} |")
        if report.opdrachtgever.functie_contactpersoon:
            md.append(f"| Functie | {report.opdrachtgever.functie_contactpersoon} |")
        if report.opdrachtgever.adres:
            md.append(f"| Adres | {report.opdrachtgever.adres} |")
        if report.opdrachtgever.postcode and report.opdrachtgever.woonplaats:
            md.append(f"| PC/Woonplaats | {report.opdrachtgever.postcode}  {report.opdrachtgever.woonplaats} |")
        if report.opdrachtgever.telefoonnummer:
            md.append(f"| Telefoonnummer | {report.opdrachtgever.telefoonnummer} |")
        if report.opdrachtgever.email:
            md.append(f"| E-mailadres | {report.opdrachtgever.email} |")
        md.append("")
        
        # Gegevens werknemer (tabel)
        md.append("**Gegevens werknemer**\n")
        md.append(f"| Naam | {report.werknemer.naam} |")
        md.append("| :---- | :---- |")
        if report.werknemer.geboortedatum:
            md.append(f"| Geboortedatum | {report.werknemer.geboortedatum} |")
        if report.werknemer.adres:
            md.append(f"| Adres | {report.werknemer.adres} |")
        if report.werknemer.postcode and report.werknemer.woonplaats:
            md.append(f"| PC/Woonplaats | {report.werknemer.postcode}  {report.werknemer.woonplaats} |")
        if report.werknemer.telefoonnummer:
            md.append(f"| Telefoonnummer | {report.werknemer.telefoonnummer} |")
        if report.werknemer.email:
            md.append(f"| E-mailadres | {report.werknemer.email} |")
        md.append("")
        
        # Gegevens adviseur (tabel)
        md.append("**Gegevens adviseur**\n")
        md.append(f"| Naam arbeidsdeskundige | {report.adviseur.naam} |")
        md.append("| :---- | :---- |")
        if report.adviseur.telefoonnummer:
            md.append(f"| Telefoonnummer bedrijf | {report.adviseur.telefoonnummer} |")
        md.append("")
        
        # Gegevens onderzoek (tabel)
        md.append("**Gegevens onderzoek**\n")
        md.append(f"| Datum onderzoek | {report.onderzoek.datum_onderzoek} |")
        md.append("| :---- | :---- |")
        md.append(f"| Datum rapportage | {report.onderzoek.datum_rapportage} |")
        md.append("")
        
        # Samenvatting
        md.append("***Samenvatting***\n")
        
        md.append("**Vraagstelling**\n")
        for vraag in report.samenvatting_vraagstelling:
            md.append(f"* {vraag}")
        md.append("")
        
        md.append("**Conclusie**\n")
        for conclusie in report.samenvatting_conclusie:
            md.append(f"* {conclusie}")
        md.append("")
        
        # Rapportage
        md.append("***Rapportage***\n")
        
        # 1. Vraagstelling
        md.append("**1. Vraagstelling**\n")
        for item in report.vraagstelling:
            md.append(f"* {item.vraag}")
        md.append("")
        
        # 2. Ondernomen activiteiten
        md.append("**2. Ondernomen activiteiten**\n")
        for activiteit in report.ondernomen_activiteiten:
            md.append(f"* {activiteit}")
        md.append("")
        
        # 3. Gegevensverzameling
        md.append("**3. Gegevensverzameling**\n")
        
        # 3.1 Voorgeschiedenis
        md.append("**3.1 Voorgeschiedenis**")
        md.append(report.voorgeschiedenis)
        md.append("")
        
        if report.verzuimhistorie:
            md.append("**Verzuimhistorie**")
            md.append(report.verzuimhistorie)
            md.append("")
        
        # 3.2 Gegevens werkgever
        md.append("**3.2 Gegevens werkgever**\n")
        md.append("| Aard bedrijf | {} |".format(report.opdrachtgever.aard_bedrijf or ""))
        md.append("| :---- | :---- |")
        md.append("| Omvang bedrijf | {} |".format(report.opdrachtgever.omvang_bedrijf or ""))
        md.append("| Aantal werknemers | {} |".format(report.opdrachtgever.aantal_werknemers or ""))
        md.append("| Functies, aantal werknemers per functie | {} |".format(report.opdrachtgever.functies_expertises or ""))
        if report.opdrachtgever.website:
            md.append("| Overige informatie | {} |".format(report.opdrachtgever.website))
        md.append("")
        
        # 3.3 Gegevens werknemer
        md.append("**3.3 Gegevens werknemer**\n")
        
        # Opleidingen tabel
        if report.opleidingen:
            md.append("| Opleidingen / cursussen | Richting | Diploma / certificaat / jaar |")
            md.append("| :---- | :---- | :---- |")
            for opl in report.opleidingen:
                md.append(f"| {opl.naam} | {opl.richting or ''} | {opl.diploma_certificaat or ''} {opl.jaar or ''} |")
        
        # Arbeidsverleden tabel
        if report.arbeidsverleden_lijst:
            md.append("| **Arbeidsverleden van / tot** | **Werkgever** | **Functie** |")
            for werk in report.arbeidsverleden_lijst:
                md.append(f"| {werk.periode} | {werk.werkgever} | {werk.functie} |")
        
        # Bekwaamheden
        if report.bekwaamheden:
            md.append("| **Bekwaamheden** |  |  |")
            if report.bekwaamheden.computervaardigheden:
                md.append(f"| Computervaardigheden | {report.bekwaamheden.computervaardigheden} |  |")
            if report.bekwaamheden.taalvaardigheid:
                md.append(f"| Taalvaardigheid | {report.bekwaamheden.taalvaardigheid} |  |")
            if report.bekwaamheden.rijbewijs:
                md.append(f"| Rijbewijs / categorie | {report.bekwaamheden.rijbewijs} |  |")
        md.append("")
        
        # 3.4 Belastbaarheid
        md.append("**3.4 Belastbaarheid van werknemer**")
        md.append(f"De belastbaarheid is op {report.belastbaarheid.datum_beoordeling} door {report.belastbaarheid.beoordelaar} weergegeven in een functionelemogelijkhedenlijst (FML). Uit de FML van werknemer blijkt dat de belastbaarheid in vergelijking met een gezond persoon tussen 16 en 65 jaar beperkt is op de volgende aspecten:\n")
        
        # FML Rubrieken
        md.append("|  |  |  |  |")
        md.append("| :---- | :---- | :---- | :---- |")
        
        for rubriek in report.belastbaarheid.fml_rubrieken:
            md.append(f"| **Rubriek {rubriek.rubriek_nummer}: {rubriek.rubriek_naam}** |  |  | **{rubriek.mate_beperking}** |")
            for item in rubriek.items:
                nummer = f"{item.nummer} " if item.nummer else ""
                md.append(f"| {nummer} | {item.beschrijving} |  | {'Beperkt' if rubriek.mate_beperking != BeperkingMate.NIET_BEPERKT else ''} |")
            md.append("|  |  |  |  |")
        
        if report.belastbaarheid.prognose:
            md.append("")
            md.append(report.belastbaarheid.prognose)
        md.append("")
        
        # 3.5 Eigen functie
        md.append("**3.5 Eigen functie werknemer**\n")
        md.append(f"| Naam functie | {report.eigen_functie.naam_functie} |")
        md.append("| :---- | :---- |")
        md.append(f"| Arbeidspatroon | {report.eigen_functie.arbeidspatroon} |")
        md.append(f"| Overeenkomst | {report.eigen_functie.overeenkomst} |")
        md.append(f"| Aantal uren | {report.eigen_functie.aantal_uren} |")
        if report.eigen_functie.salaris:
            md.append(f"| Brutosalaris | {report.eigen_functie.salaris} |")
        md.append(f"| Functie- omschrijving | {report.eigen_functie.functieomschrijving} |")
        md.append("")
        
        # Functiebelasting
        if report.functiebelasting:
            md.append("Functiebelasting (*gerelateerd aan de belastbaarheid van werknemer)*\n")
            md.append("| Taken | % | Belastende aspecten |")
            md.append("| :---- | :---- | :---- |")
            for belasting in report.functiebelasting:
                md.append(f"| {belasting.taak} | {belasting.percentage} | {belasting.belastende_aspecten} |")
            md.append("")
        
        # 3.6 Gesprek met werkgever
        if report.gesprek_werkgever:
            md.append("**3.6 Gesprek met de werkgever**\n")
            for key, value in report.gesprek_werkgever.items():
                if key == "algemeen":
                    md.append("*Algemeen*")
                elif key == "visie_functioneren":
                    md.append("*Visie werkgever op functioneren werknemer vóór uitval*")
                elif key == "visie_duurzaamheid":
                    md.append("*Visie werkgever op de duurzaamheid van een herplaatsing*")
                elif key == "visie_reintegratie":
                    md.append("*Visie werkgever op re-integratiemogelijkheden voor werknemer binnen het bedrijf*")
                md.append(value)
                md.append("")
        
        # 3.7 Gesprek met werknemer
        if report.gesprek_werknemer:
            md.append("**3.7 Gesprek met werknemer**\n")
            for key, value in report.gesprek_werknemer.items():
                if key == "visie_beperkingen":
                    md.append("*Visie op beperkingen en mogelijkheden*")
                elif key == "visie_werk":
                    md.append("*Visie werknemer op het werk en de re-integratiemogelijkheden*")
                md.append(value)
                md.append("")
        
        # 3.8 Gesprek gezamenlijk
        if report.gesprek_gezamenlijk:
            md.append("**3.8 Gesprek met de werkgever en werknemer gezamenlijk**")
            md.append(report.gesprek_gezamenlijk)
            md.append("")
        
        # 4. Visie arbeidsdeskundige
        md.append("**4. Visie arbeidsdeskundige**\n")
        
        # 4.1 Geschiktheid eigen werk
        md.append("**4.1 Geschiktheid voor eigen werk**\n")
        if report.geschiktheid_eigen_werk:
            md.append("Uit het onderzoek blijkt dat er een overschrijding van de belastbaarheid plaatsvindt op de punten:\n")
            md.append("| Belastend aspect | Belastbaarheid |")
            md.append("| :---- | :---- |")
            for analyse in report.geschiktheid_eigen_werk:
                md.append(f"| {analyse.belastend_aspect} | {analyse.belastbaarheid_werknemer} |")
            md.append("")
        
        if report.conclusie_eigen_werk:
            md.append(report.conclusie_eigen_werk)
            md.append("")
        
        # 4.2 Aanpassing eigen werk
        md.append("**4.2 Aanpassing eigen werk**")
        md.append(report.aanpassing_eigen_werk)
        md.append("")
        
        # 4.3 Geschiktheid ander werk intern
        md.append("**4.3 Geschiktheid voor ander werk bij eigen werkgever**")
        md.append(report.geschiktheid_ander_werk_intern)
        md.append("")
        
        # 4.4 Geschiktheid ander werk extern
        md.append("**4.4 Geschiktheid voor ander werk bij andere werkgever**")
        md.append(report.geschiktheid_ander_werk_extern)
        
        if report.zoekrichting:
            md.append("Zoekrichting")
            for key, value in report.zoekrichting.items():
                md.append(f"{key}\t:\t{value}")
        md.append("")
        
        # 4.5 Visie duurzaamheid
        md.append("**4.5 Visie van de arbeidsdeskundige op de duurzaamheid van het te behalen**")
        md.append("**re-integratieresultaat**")
        md.append(report.visie_duurzaamheid)
        md.append("")
        
        # 5. Trajectplan
        md.append("**5. Trajectplan**\n")
        for item in report.trajectplan:
            spoor_text = f" (Spoor {item.spoor})" if item.spoor else ""
            md.append(f"* {item.actie}{spoor_text}")
        md.append("")
        
        # 6. Conclusie
        md.append("**6. Conclusie**\n")
        for item in report.conclusies:
            md.append(f"* {item.conclusie}")
            if item.toelichting:
                md.append(f"  {item.toelichting}")
        md.append("")
        
        # 7. Vervolg
        md.append("**7. Vervolg**\n")
        for item in report.vervolg:
            md.append(f"* {item}")
        md.append("")
        
        # Footer
        if report.adviseur.naam:
            md.append(report.adviseur.naam)
            if report.adviseur.functie:
                md.append(report.adviseur.functie)
        
        # Disclaimer
        if report.disclaimer:
            md.append("")
            md.append(report.disclaimer)
        
        return "\n".join(md)
    
    def render_html(self, report: ADReport) -> str:
        """
        Render report to HTML format with CSS styling
        
        Args:
            report: ADReport data structure
            
        Returns:
            HTML string with embedded CSS
        """
        # Convert to markdown first, then to HTML with styling
        markdown_content = self.render_markdown(report)
        
        # Basic HTML template with CSS
        html = f"""
        <!DOCTYPE html>
        <html lang="nl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{report.titel} - {report.werknemer.naam}</title>
            <style>
                body {{
                    font-family: 'Times New Roman', serif;
                    font-size: 11pt;
                    line-height: 1.25;
                    color: #000;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                
                h1, h2, h3 {{
                    color: #1e40af;
                    margin-top: 16pt;
                    margin-bottom: 8pt;
                }}
                
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                
                td, th {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                
                th {{
                    background-color: #f5f5f5;
                    font-weight: bold;
                }}
                
                td:first-child {{
                    font-weight: bold;
                    width: 30%;
                }}
                
                ul {{
                    margin-left: 20px;
                }}
                
                .section-number {{
                    font-weight: bold;
                    color: #1e40af;
                }}
                
                .subsection {{
                    margin-left: 20px;
                }}
                
                @media print {{
                    body {{
                        font-size: 10pt;
                    }}
                }}
            </style>
        </head>
        <body>
            {self._markdown_to_html(markdown_content)}
        </body>
        </html>
        """
        return html
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML (basic implementation)"""
        # This is a simplified converter - in production use a proper markdown library
        html_lines = []
        lines = markdown.split('\n')
        in_table = False
        
        for line in lines:
            # Headers
            if line.startswith('**') and line.endswith('**'):
                text = line[2:-2]
                if any(char.isdigit() and line.startswith(f'**{char}') for char in '1234567'):
                    html_lines.append(f'<h2 class="section-number">{text}</h2>')
                else:
                    html_lines.append(f'<h3>{text}</h3>')
            # Tables
            elif line.startswith('|'):
                if not in_table:
                    html_lines.append('<table>')
                    in_table = True
                
                if ':----' in line:
                    continue  # Skip separator line
                    
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                row_html = '<tr>'
                for cell in cells:
                    row_html += f'<td>{cell}</td>'
                row_html += '</tr>'
                html_lines.append(row_html)
            else:
                if in_table and line.strip() == '':
                    html_lines.append('</table>')
                    in_table = False
                
                # Bullets
                if line.startswith('* '):
                    if not html_lines[-1].startswith('<ul>'):
                        html_lines.append('<ul>')
                    html_lines.append(f'<li>{line[2:]}</li>')
                elif html_lines and html_lines[-1].endswith('</li>') and not line.startswith('* '):
                    html_lines.append('</ul>')
                    if line.strip():
                        html_lines.append(f'<p>{line}</p>')
                # Regular paragraphs
                elif line.strip():
                    html_lines.append(f'<p>{line}</p>')
        
        return '\n'.join(html_lines)
    
    def render_json(self, report: ADReport) -> str:
        """
        Render report to JSON format
        
        Args:
            report: ADReport data structure
            
        Returns:
            JSON string
        """
        return json.dumps(report.dict(), indent=2, ensure_ascii=False)