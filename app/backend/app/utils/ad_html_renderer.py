"""
AD Report HTML Renderer - Converts structured AD report to professional HTML
Follows exact format from professional AD report examples
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.ad_report_structure import ADReport, FMLRubriek, BeperkingMate

logger = logging.getLogger(__name__)

class ADHtmlRenderer:
    """Renders ADReport objects to professional HTML format"""
    
    @staticmethod
    def render_complete_report(report: ADReport) -> str:
        """
        Render complete AD report to HTML
        
        Args:
            report: ADReport object with all data
            
        Returns:
            HTML string of complete report
        """
        sections = []
        
        # Title page
        sections.append(ADHtmlRenderer._render_title_page(report))
        
        # Metadata tables
        sections.append(ADHtmlRenderer._render_metadata_tables(report))
        
        # Samenvatting
        sections.append(ADHtmlRenderer._render_samenvatting(report))
        
        # Main sections
        sections.append(ADHtmlRenderer._render_main_sections(report))
        
        # Wrap in HTML document structure
        html = f"""
        <div class="ad-report">
            <style>{ADHtmlRenderer._get_styles()}</style>
            {''.join(sections)}
        </div>
        """
        
        return html
        
    @staticmethod
    def _get_styles() -> str:
        """Get CSS styles for AD report - Improved for professional Dutch AD reports"""
        return """
        .ad-report {
            font-family: 'Times New Roman', 'Liberation Serif', serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #1f2937;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: white;
        }
        
        /* Title page styling */
        .ad-report h1 {
            font-size: 18pt;
            font-weight: bold;
            text-align: center;
            margin: 30px 0 25px 0;
            color: #1e40af;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid #1e40af;
            padding-bottom: 10px;
        }
        
        /* Main section headers (numbered) */
        .ad-report h2 {
            font-size: 14pt;
            font-weight: bold;
            margin: 30px 0 15px 0;
            color: #1e40af;
            border-bottom: 2px solid #1e40af;
            padding-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Subsection headers */
        .ad-report h3 {
            font-size: 12pt;
            font-weight: bold;
            margin: 20px 0 10px 0;
            color: #2563eb;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 4px;
        }
        
        /* Minor headers */
        .ad-report h4 {
            font-size: 11pt;
            font-weight: bold;
            font-style: italic;
            margin: 15px 0 8px 0;
            color: #3b82f6;
        }
        
        /* Professional table styling */
        .ad-report table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 10pt;
            border: 2px solid #1e40af;
        }
        
        /* Metadata tables (gegevens sections) */
        .ad-report table.metadata-table {
            border: 2px solid #1e40af;
            margin-bottom: 25px;
        }
        
        .ad-report table.metadata-table td {
            padding: 12px 15px;
            border: 1px solid #1e40af;
            vertical-align: top;
            line-height: 1.3;
        }
        
        .ad-report table.metadata-table td:first-child {
            font-weight: bold;
            background-color: #eff6ff;
            width: 40%;
            color: #1e40af;
        }
        
        .ad-report table.metadata-table td:last-child {
            background-color: white;
        }
        
        /* FML and analysis tables */
        .ad-report table.fml-table {
            margin: 25px 0;
            border: 2px solid #1e40af;
        }
        
        .ad-report table.fml-table th {
            background-color: #1e40af;
            font-weight: bold;
            text-align: left;
            padding: 12px 15px;
            border: 1px solid #1e40af;
            color: white;
            font-size: 11pt;
        }
        
        .ad-report table.fml-table td {
            padding: 10px 15px;
            border: 1px solid #1e40af;
            vertical-align: top;
            background-color: white;
            line-height: 1.3;
        }
        
        /* Alternating row colors for better readability */
        .ad-report table.fml-table tr:nth-child(even) td {
            background-color: #f8fafc;
        }
        
        .ad-report .section-box {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 4px;
            padding: 15px;
            margin: 15px 0;
        }
        
        .ad-report ul {
            margin: 10px 0;
            padding-left: 25px;
        }
        
        .ad-report ul li {
            margin: 5px 0;
        }
        
        .ad-report .numbered-item {
            margin: 10px 0;
            text-indent: -20px;
            padding-left: 20px;
        }
        
        .ad-report .page-break {
            page-break-after: always;
            margin: 40px 0;
        }
        
        .ad-report .title-page {
            text-align: center;
            padding: 100px 20px;
        }
        
        .ad-report .title-page h1 {
            font-size: 24pt;
            margin-bottom: 40px;
        }
        
        .ad-report .title-page .client-name {
            font-size: 18pt;
            margin: 20px 0;
        }
        
        .ad-report .title-page .advisor-info {
            margin-top: 60px;
            font-size: 12pt;
        }
        
        .ad-report em {
            font-style: italic;
        }
        
        .ad-report strong {
            font-weight: bold;
        }
        """
        
    @staticmethod
    def _render_title_page(report: ADReport) -> str:
        """Render title page"""
        return f"""
        <div class="title-page">
            <h1>{report.titel}</h1>
            <div class="client-name">{report.werknemer.naam}</div>
            <div class="advisor-info">
                <div>{report.adviseur.naam}</div>
                <div>{report.adviseur.functie or 'Gecertificeerd Register Arbeidsdeskundige'}</div>
                <div>Vector Arbeidsdeskundig Advies</div>
            </div>
        </div>
        <div class="page-break"></div>
        """
        
    @staticmethod
    def _render_metadata_tables(report: ADReport) -> str:
        """Render metadata tables section"""
        html = "<h1>Arbeidsdeskundig re-integratieonderzoek</h1>"
        
        # Opdrachtgever table
        html += """
        <h2>Gegevens opdrachtgever</h2>
        <table class="metadata-table">
        """
        
        fields = [
            ("Naam bedrijf", report.opdrachtgever.naam_bedrijf),
            ("Contactpersoon", report.opdrachtgever.contactpersoon),
            ("Functie", report.opdrachtgever.functie_contactpersoon),
            ("Adres", report.opdrachtgever.adres),
            ("PC/Woonplaats", f"{report.opdrachtgever.postcode}  {report.opdrachtgever.woonplaats}" 
             if report.opdrachtgever.postcode else report.opdrachtgever.woonplaats),
            ("Telefoonnummer", report.opdrachtgever.telefoonnummer),
            ("E-mailadres", f'<a href="mailto:{report.opdrachtgever.email}">{report.opdrachtgever.email}</a>' 
             if report.opdrachtgever.email else None),
        ]
        
        for label, value in fields:
            if value:
                html += f"<tr><td>{label}</td><td>{value or 'Niet beschikbaar'}</td></tr>"
        
        html += "</table>"
        
        # Werknemer table
        html += """
        <h2>Gegevens werknemer</h2>
        <table class="metadata-table">
        """
        
        fields = [
            ("Naam", report.werknemer.naam),
            ("Geboortedatum", report.werknemer.geboortedatum),
            ("Adres", report.werknemer.adres),
            ("PC/Woonplaats", f"{report.werknemer.postcode}  {report.werknemer.woonplaats}" 
             if report.werknemer.postcode else report.werknemer.woonplaats),
            ("Telefoonnummer", report.werknemer.telefoonnummer),
            ("E-mailadres", f'<a href="mailto:{report.werknemer.email}">{report.werknemer.email}</a>' 
             if report.werknemer.email else None),
        ]
        
        for label, value in fields:
            if value:
                html += f"<tr><td>{label}</td><td>{value or 'Niet beschikbaar'}</td></tr>"
        
        html += "</table>"
        
        # Adviseur table
        html += """
        <h2>Gegevens adviseur</h2>
        <table class="metadata-table">
        """
        
        fields = [
            ("Naam arbeidsdeskundige", report.adviseur.naam),
            ("Telefoonnummer bedrijf", report.adviseur.telefoonnummer or "06-81034165"),
        ]
        
        for label, value in fields:
            if value:
                html += f"<tr><td>{label}</td><td>{value}</td></tr>"
        
        html += "</table>"
        
        # Onderzoek table
        html += """
        <h2>Gegevens onderzoek</h2>
        <table class="metadata-table">
        """
        
        fields = [
            ("Datum onderzoek", report.onderzoek.datum_onderzoek),
            ("Datum rapportage", report.onderzoek.datum_rapportage),
        ]
        
        for label, value in fields:
            html += f"<tr><td>{label}</td><td>{value}</td></tr>"
        
        html += "</table>"
        
        return html
        
    @staticmethod
    def _render_samenvatting(report: ADReport) -> str:
        """Render samenvatting section"""
        html = "<h1><em>Samenvatting</em></h1>"
        
        # Vraagstelling
        html += "<h2>Vraagstelling</h2><ul>"
        for vraag in report.samenvatting_vraagstelling:
            html += f"<li>{vraag}</li>"
        html += "</ul>"
        
        # Conclusie
        html += "<h2>Conclusie</h2><ul>"
        for conclusie in report.samenvatting_conclusie:
            html += f"<li>{conclusie}</li>"
        html += "</ul>"
        
        return html
        
    @staticmethod
    def _render_main_sections(report: ADReport) -> str:
        """Render all main numbered sections"""
        html = "<h1><em>Rapportage</em></h1>"
        
        # 1. Vraagstelling
        html += "<h2>1. Vraagstelling</h2><ul>"
        for item in report.vraagstelling:
            html += f"<li>{item.vraag}</li>"
        html += "</ul>"
        
        # 2. Ondernomen activiteiten
        html += "<h2>2. Ondernomen activiteiten</h2><ul>"
        for activiteit in report.ondernomen_activiteiten:
            html += f"<li>{activiteit}</li>"
        html += "</ul>"
        
        # 3. Gegevensverzameling
        html += "<h2>3. Gegevensverzameling</h2>"
        
        # 3.1 Voorgeschiedenis
        html += "<h3>3.1 Voorgeschiedenis</h3>"
        html += f"<p>{report.voorgeschiedenis}</p>"
        
        html += "<h4>Verzuimhistorie</h4>"
        html += f"<p>{report.verzuimhistorie}</p>"
        
        # 3.2 Gegevens werkgever
        html += "<h3>3.2 Gegevens werkgever</h3>"
        html += '<table class="metadata-table">'
        
        fields = [
            ("Aard bedrijf", report.opdrachtgever.aard_bedrijf),
            ("Omvang bedrijf", report.opdrachtgever.omvang_bedrijf),
            ("Aantal werknemers", report.opdrachtgever.aantal_werknemers),
            ("Functies, aantal werknemers per functie", report.opdrachtgever.functies_expertises),
            ("Overige informatie", f'<a href="{report.opdrachtgever.website}">{report.opdrachtgever.website}</a>' 
             if report.opdrachtgever.website else None),
        ]
        
        for label, value in fields:
            if value:
                html += f"<tr><td>{label}</td><td>{value}</td></tr>"
        
        html += "</table>"
        
        # 3.3 Gegevens werknemer
        html += "<h3>3.3 Gegevens werknemer</h3>"
        
        # Opleidingen table
        if report.opleidingen:
            html += """
            <table class="fml-table">
            <thead>
                <tr>
                    <th>Opleidingen / cursussen</th>
                    <th>Richting</th>
                    <th>Diploma / certificaat / jaar</th>
                </tr>
            </thead>
            <tbody>
            """
            
            for opl in report.opleidingen:
                html += f"""
                <tr>
                    <td>{opl.naam}</td>
                    <td>{opl.richting or '-'}</td>
                    <td>{opl.diploma_certificaat or ''} {opl.jaar or ''}</td>
                </tr>
                """
            
            html += "</tbody></table>"
        
        # Arbeidsverleden table
        if report.arbeidsverleden_lijst:
            html += """
            <table class="fml-table">
            <thead>
                <tr>
                    <th>Arbeidsverleden van / tot</th>
                    <th>Werkgever</th>
                    <th>Functie</th>
                </tr>
            </thead>
            <tbody>
            """
            
            for av in report.arbeidsverleden_lijst:
                html += f"""
                <tr>
                    <td>{av.periode}</td>
                    <td>{av.werkgever}</td>
                    <td>{av.functie}</td>
                </tr>
                """
            
            html += "</tbody></table>"
        
        # Bekwaamheden
        html += "<h4>Bekwaamheden</h4>"
        html += '<table class="metadata-table">'
        
        if report.bekwaamheden:
            fields = [
                ("Computervaardigheden", report.bekwaamheden.computervaardigheden),
                ("Taalvaardigheid", report.bekwaamheden.taalvaardigheid),
                ("Rijbewijs / categorie", report.bekwaamheden.rijbewijs),
            ]
            
            for label, value in fields:
                if value:
                    html += f"<tr><td>{label}</td><td>{value}</td></tr>"
        
        html += "</table>"
        
        # 3.4 Belastbaarheid
        html += ADHtmlRenderer._render_belastbaarheid(report)
        
        # 3.5 Eigen functie
        html += ADHtmlRenderer._render_eigen_functie(report)
        
        # 3.6 Gesprek met werkgever
        if report.gesprek_werkgever:
            html += "<h3>3.6 Gesprek met de werkgever</h3>"
            
            for key, value in report.gesprek_werkgever.items():
                if value:
                    title = key.replace('_', ' ').title()
                    html += f"<h4><em>{title}</em></h4>"
                    html += f"<p>{value}</p>"
        
        # 3.7 Gesprek met werknemer
        if report.gesprek_werknemer:
            html += "<h3>3.7 Gesprek met werknemer</h3>"
            
            for key, value in report.gesprek_werknemer.items():
                if value:
                    title = key.replace('_', ' ').title()
                    html += f"<h4><em>{title}</em></h4>"
                    html += f"<p>{value}</p>"
        
        # 3.8 Gesprek gezamenlijk
        if report.gesprek_gezamenlijk:
            html += "<h3>3.8 Gesprek met de werkgever en werknemer gezamenlijk</h3>"
            html += f"<p>{report.gesprek_gezamenlijk}</p>"
        
        # 4. Visie arbeidsdeskundige
        html += ADHtmlRenderer._render_visie_arbeidsdeskundige(report)
        
        # 5. Trajectplan
        html += ADHtmlRenderer._render_trajectplan(report)
        
        # 6. Conclusie
        html += ADHtmlRenderer._render_conclusie(report)
        
        # 7. Vervolg
        html += ADHtmlRenderer._render_vervolg(report)
        
        return html
        
    @staticmethod
    def _render_belastbaarheid(report: ADReport) -> str:
        """Render belastbaarheid section"""
        html = "<h3>3.4 Belastbaarheid van werknemer</h3>"
        
        if report.belastbaarheid:
            html += f"""
            <p>De belastbaarheid is op {report.belastbaarheid.datum_beoordeling} door 
            bedrijfsarts {report.belastbaarheid.beoordelaar} weergegeven in een 
            functionelemogelijkhedenlijst (FML). Uit de FML van werknemer blijkt dat de 
            belastbaarheid in vergelijking met een gezond persoon tussen 16 en 65 jaar 
            beperkt is op de volgende aspecten:</p>
            """
            
            # FML table
            html += """
            <table class="fml-table">
            <thead>
                <tr>
                    <th colspan="3">Rubriek</th>
                    <th>Mate van beperking</th>
                </tr>
            </thead>
            <tbody>
            """
            
            for rubriek in report.belastbaarheid.fml_rubrieken:
                if rubriek.mate_beperking != BeperkingMate.NIET_BEPERKT or rubriek.items:
                    html += f"""
                    <tr>
                        <td colspan="3"><strong>Rubriek {rubriek.rubriek_nummer}: {rubriek.rubriek_naam}</strong></td>
                        <td><strong>{rubriek.mate_beperking.value}</strong></td>
                    </tr>
                    """
                    
                    for item in rubriek.items:
                        html += f"""
                        <tr>
                            <td>{item.nummer or ''}</td>
                            <td colspan="2">{item.beschrijving}</td>
                            <td>{rubriek.mate_beperking.value}</td>
                        </tr>
                        """
            
            html += "</tbody></table>"
            
            if report.belastbaarheid.prognose:
                html += f"<p><strong>Prognose:</strong> {report.belastbaarheid.prognose}</p>"
        
        return html
        
    @staticmethod
    def _render_eigen_functie(report: ADReport) -> str:
        """Render eigen functie section"""
        html = "<h3>3.5 Eigen functie werknemer</h3>"
        
        if report.eigen_functie:
            html += '<table class="metadata-table">'
            
            fields = [
                ("Naam functie", report.eigen_functie.naam_functie),
                ("Arbeidspatroon", report.eigen_functie.arbeidspatroon),
                ("Overeenkomst", report.eigen_functie.overeenkomst),
                ("Aantal uren", report.eigen_functie.aantal_uren),
                ("Brutosalaris", report.eigen_functie.salaris),
                ("Functieomschrijving", report.eigen_functie.functieomschrijving),
            ]
            
            for label, value in fields:
                if value:
                    html += f"<tr><td>{label}</td><td>{value}</td></tr>"
            
            html += "</table>"
            
            # Functiebelasting table
            if report.functiebelasting:
                html += "<h4>Functiebelasting <em>(gerelateerd aan de belastbaarheid van werknemer)</em></h4>"
                html += """
                <table class="fml-table">
                <thead>
                    <tr>
                        <th>Taken</th>
                        <th>%</th>
                        <th>Belastende aspecten</th>
                    </tr>
                </thead>
                <tbody>
                """
                
                for fb in report.functiebelasting:
                    html += f"""
                    <tr>
                        <td>{fb.taak}</td>
                        <td>{fb.percentage}</td>
                        <td>{fb.belastende_aspecten}</td>
                    </tr>
                    """
                
                html += "</tbody></table>"
        
        return html
        
    @staticmethod
    def _render_visie_arbeidsdeskundige(report: ADReport) -> str:
        """Render visie arbeidsdeskundige section"""
        html = "<h2>4. Visie arbeidsdeskundige</h2>"
        
        # 4.1 Geschiktheid voor eigen werk
        html += "<h3>4.1 Geschiktheid voor eigen werk</h3>"
        
        if report.geschiktheid_eigen_werk:
            html += "<p>Uit het onderzoek blijkt dat er een overschrijding van de belastbaarheid plaatsvindt op de punten:</p>"
            html += """
            <table class="fml-table">
            <thead>
                <tr>
                    <th>Belastend aspect</th>
                    <th>Belastbaarheid</th>
                </tr>
            </thead>
            <tbody>
            """
            
            for ga in report.geschiktheid_eigen_werk:
                html += f"""
                <tr>
                    <td>{ga.belastend_aspect}</td>
                    <td>{ga.belastbaarheid_werknemer}</td>
                </tr>
                """
            
            html += "</tbody></table>"
        
        if report.conclusie_eigen_werk:
            html += f"<p>{report.conclusie_eigen_werk}</p>"
        
        # 4.2 Aanpassing eigen werk
        if report.aanpassing_eigen_werk:
            html += "<h3>4.2 Aanpassing eigen werk</h3>"
            html += f"<p>{report.aanpassing_eigen_werk}</p>"
        
        # 4.3 Geschiktheid voor ander werk bij eigen werkgever
        if report.geschiktheid_ander_werk_intern:
            html += "<h3>4.3 Geschiktheid voor ander werk bij eigen werkgever</h3>"
            html += f"<p>{report.geschiktheid_ander_werk_intern}</p>"
        
        # 4.4 Geschiktheid voor ander werk bij andere werkgever
        if report.geschiktheid_ander_werk_extern:
            html += "<h3>4.4 Geschiktheid voor ander werk bij andere werkgever</h3>"
            html += f"<p>{report.geschiktheid_ander_werk_extern}</p>"
            
            if report.zoekrichting:
                html += "<h4>Zoekrichting</h4>"
                html += '<table class="metadata-table">'
                
                for key, value in report.zoekrichting.items():
                    label = key.replace('_', ' ').title()
                    html += f"<tr><td>{label}</td><td>{value}</td></tr>"
                
                html += "</table>"
        
        # 4.5 Visie op duurzaamheid
        if report.visie_duurzaamheid:
            html += "<h3>4.5 Visie van de arbeidsdeskundige op de duurzaamheid van het te behalen re-integratieresultaat</h3>"
            html += f"<p>{report.visie_duurzaamheid}</p>"
        
        return html
        
    @staticmethod
    def _render_trajectplan(report: ADReport) -> str:
        """Render trajectplan section"""
        html = "<h2>5. Trajectplan</h2>"
        
        if report.trajectplan:
            html += "<ul>"
            for item in report.trajectplan:
                spoor = f" (Spoor {item.spoor})" if item.spoor else ""
                html += f"<li>{item.actie}{spoor}"
                if item.verantwoordelijke:
                    html += f" - Verantwoordelijke: {item.verantwoordelijke}"
                if item.termijn:
                    html += f" - Termijn: {item.termijn}"
                html += "</li>"
            html += "</ul>"
        
        return html
        
    @staticmethod
    def _render_conclusie(report: ADReport) -> str:
        """Render conclusie section"""
        html = "<h2>6. Conclusie</h2>"
        
        if report.conclusies:
            html += "<ul>"
            for item in report.conclusies:
                html += f"<li>{item.conclusie}"
                if item.toelichting:
                    html += f"<br/>{item.toelichting}"
                html += "</li>"
            html += "</ul>"
        
        return html
        
    @staticmethod
    def _render_vervolg(report: ADReport) -> str:
        """Render vervolg section"""
        html = "<h2>7. Vervolg</h2>"
        
        if report.vervolg:
            html += "<ul>"
            for item in report.vervolg:
                html += f"<li>{item}</li>"
            html += "</ul>"
        
        # Footer
        html += """
        <div style="margin-top: 40px;">
            <p>Patrick Peters<br/>
            Gecertificeerd registerarbeidsdeskundige<br/>
            Vector Arbeidsdeskundig Advies</p>
            
            <p style="font-size: 9pt; font-style: italic; margin-top: 30px;">
            * Dit rapport is tot stand gekomen na gesprekken met werkgever en werknemer en is gebaseerd op de huidige situatie. 
            Werkgever en werknemer kunnen aan de inhoud van dit rapport geen rechten ontlenen.<br/>
            * Voor actuele informatie over regelingen en voorzieningen verwijzen wij naar de sites van UWV (www.uwv.nl), 
            UWV WERKbedrijf (www.werk.nl) en de Belastingdienst (www.belastingdienst.nl).<br/>
            * Aan digitale versies van het rapport kunnen geen rechten worden ontleend en deze mogen niet aan derden worden verstuurd.
            </p>
        </div>
        """
        
        return html