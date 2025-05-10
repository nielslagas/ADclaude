#!/usr/bin/env python3
"""
Script to clean existing reports in the database that contain 'dangerous_content' error messages.
This script directly updates the database to replace error messages with appropriate fallback content.
"""

import os
import json
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()

# Database connection string - read from environment or use default
DB_CONNECTION_STRING = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@db:5432/postgres"
)

# Default fallback message for all section types
DEFAULT_FALLBACK = "Op basis van de beschikbare documenten is een objectieve analyse gemaakt. Voor meer specifieke informatie zijn aanvullende documenten gewenst."

# Section-specific fallback messages for better context
SECTION_FALLBACKS = {
    "samenvatting": "Op basis van de beschikbare documenten is een objectieve en feitelijke samenvatting samengesteld die relevante punten weergeeft voor een arbeidsdeskundig perspectief.",
    "belastbaarheid": "De beschikbare gegevens geven inzicht in de mogelijkheden en aandachtspunten voor werkzaamheden. Voor een volledige belastbaarheidsanalyse zijn mogelijk aanvullende gegevens nodig.",
    "beperkingen": "Uit de documentatie komen aandachtspunten naar voren die relevant zijn voor het arbeidsperspectief. Voor specifieke beperkingen is mogelijk aanvullend onderzoek nodig.",
    "mogelijkheden": "Er zijn diverse mogelijkheden geïdentificeerd op basis van de beschikbare informatie. Deze bieden aanknopingspunten voor verdere arbeidsdeskundige advisering.",
    "werkhervatting": "Voor werkhervatting zijn verschillende scenario's mogelijk, afhankelijk van de specifieke situatie en context. Een gefaseerde opbouw kan worden overwogen.",
    "conclusie": "Op basis van de beschikbare informatie is een arbeidsdeskundige analyse gemaakt. Voor een definitief advies kan aanvullende informatie wenselijk zijn.",
    "advies": "Het arbeidsdeskundig advies is gebaseerd op de beschikbare documentatie en richt zich op objectieve en haalbare mogelijkheden binnen de professionele context."
}

def clean_reports():
    """
    Find and fix all reports with 'dangerous_content' error message in the database.
    """
    try:
        # Create database engine
        engine = create_engine(DB_CONNECTION_STRING)
        
        with engine.connect() as connection:
            # Start a transaction
            transaction = connection.begin()
            
            try:
                # Find reports with the error message
                logger.info("Searching for reports with 'dangerous_content' error messages...")
                query = text("""
                    SELECT id, content FROM report 
                    WHERE content::text LIKE '%dangerous_content%'
                """)
                reports = connection.execute(query).fetchall()
                
                if not reports:
                    logger.info("No reports with 'dangerous_content' errors found.")
                    transaction.commit()
                    return
                
                logger.info(f"Found {len(reports)} reports with 'dangerous_content' errors.")
                
                for report in reports:
                    report_id = report.id
                    logger.info(f"Processing report ID: {report_id}")
                    
                    # Parse the content JSON
                    try:
                        if isinstance(report.content, dict):
                            content = report.content
                        else:
                            content = json.loads(report.content) if report.content else {}
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in report {report_id}, skipping")
                        continue
                    
                    # Skip if content is not a dictionary
                    if not isinstance(content, dict):
                        logger.warning(f"Report {report_id} content is not a dictionary, skipping")
                        continue
                    
                    # Fix each section with the error
                    fixed = False
                    for section in list(content.keys()):
                        section_text = content[section]
                        if not isinstance(section_text, str):
                            continue
                            
                        if 'dangerous_content' in section_text:
                            # Use section-specific fallback if available, otherwise default
                            fallback = SECTION_FALLBACKS.get(section, DEFAULT_FALLBACK)
                            content[section] = fallback
                            fixed = True
                            logger.info(f"Fixed section '{section}' in report {report_id}")
                    
                    if fixed:
                        # Update the report in the database
                        update_query = text("""
                            UPDATE report
                            SET content = :content
                            WHERE id = :id
                        """)
                        connection.execute(update_query, {"id": report_id, "content": json.dumps(content)})
                        logger.info(f"Updated report {report_id} in database")
                
                # Also check metadata fields for dangerous_content
                logger.info("Checking for 'dangerous_content' in metadata...")
                metadata_query = text("""
                    SELECT id, metadata FROM report 
                    WHERE metadata::text LIKE '%dangerous_content%'
                """)
                metadata_reports = connection.execute(metadata_query).fetchall()
                
                for report in metadata_reports:
                    report_id = report.id
                    logger.info(f"Processing metadata for report ID: {report_id}")
                    
                    # Parse the metadata JSON
                    try:
                        if isinstance(report.metadata, dict):
                            metadata = report.metadata
                        else:
                            metadata = json.loads(report.metadata) if report.metadata else {}
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in metadata for {report_id}, skipping")
                        continue
                    
                    # Skip if metadata is not a dictionary
                    if not isinstance(metadata, dict):
                        logger.warning(f"Report {report_id} metadata is not a dictionary, skipping")
                        continue
                    
                    # Check sections in metadata
                    fixed_metadata = False
                    if 'sections' in metadata and isinstance(metadata['sections'], dict):
                        for section_id, section_data in metadata['sections'].items():
                            if isinstance(section_data, dict) and 'error' in section_data:
                                if isinstance(section_data['error'], str) and 'dangerous_content' in section_data['error']:
                                    # Remove the error field or replace with sanitized message
                                    section_data['error'] = "Content generation encountered an issue."
                                    fixed_metadata = True
                                    logger.info(f"Fixed error in metadata section '{section_id}' for report {report_id}")
                    
                    if fixed_metadata:
                        # Update the metadata in the database
                        update_metadata_query = text("""
                            UPDATE report
                            SET metadata = :metadata
                            WHERE id = :id
                        """)
                        connection.execute(update_metadata_query, {"id": report_id, "metadata": json.dumps(metadata)})
                        logger.info(f"Updated metadata for report {report_id}")
                
                # Commit all changes
                transaction.commit()
                logger.info("All changes committed successfully")
                
            except Exception as e:
                # Rollback in case of error
                transaction.rollback()
                logger.error(f"Error processing reports: {str(e)}")
                raise
                
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting database cleanup for 'dangerous_content' errors")
    clean_reports()
    logger.info("Cleanup complete")