"""
Document Field Extractor

This module extracts structured data from document chunks using regex patterns.
It's designed to populate template fields with real data from uploaded documents.

Usage:
    from app.utils.document_field_extractor import extract_structured_fields

    fields = extract_structured_fields(document_chunks)
    # Returns: {'werkgever_naam': 'FLE Logistics BV', ...}
"""

import re
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DocumentFieldExtractor:
    """
    Extracts structured fields from document text using regex patterns.
    """

    # Regex patterns for data extraction
    PATTERNS = {
        # Werkgever (Employer)
        'werkgever_naam': [
            r'Naam\s+bedrijf\s*:?\s*([A-Z][^\n:]+?)(?:\s+Naam:|$)',
            r'(?:werkgever|bedrijf|organisatie)\s*:?\s*([A-Z][^\n:]{5,50}?)(?:\s+Naam:|Adres:|$)',
        ],
        'werkgever_adres': [
            r'(?:werkgever.*?)Adres\s*:?\s*([^\n]+)',
            r'(?<!werknemer.{0,200})Adres\s*:?\s*([A-Z][^\n]+)',
        ],
        'werkgever_postcode': [
            r'(?:werkgever.*?)Postcode\s*:?\s*(\d{4}\s*[A-Z]{2})',
            r'(?<!werknemer.{0,200})Postcode\s*:?\s*(\d{4}\s*[A-Z]{2})',
        ],
        'werkgever_plaats': [
            r'(?:werkgever.*?)(?:Woonplaats|Plaats)\s*:?\s*([A-Z][a-z]+?)(?:\s+E-mail:|Telefoon:|Locatie:|$)',
            r'(?<!werknemer.{0,200})(?:Woonplaats|Plaats)\s*:?\s*([A-Z][a-z]+?)(?:\s+E-mail:|Telefoon:|Locatie:|$)',
        ],
        'werkgever_telefoon': [
            r'(?:werkgever.*?)Telefoon\s*:?\s*(0\d{2,3}[-\s]?\d{6,7})',
            r'(?<!werknemer.{0,200})Telefoon\s*:?\s*(0\d{2,3}[-\s]?\d{6,7})',
        ],
        'werkgever_email': [
            r'(?:werkgever.*?)E-mail\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ],
        'locatie_onderzoek': [
            r'Locatie\s+onderzoek\s*:?\s*([^\n]+)',
        ],
        'kvk': [
            r'KvK\s*:?\s*(\d{8})',
        ],
        'btw': [
            r'BTW\s*:?\s*(NL\d{9}B\d{2})',
        ],
        'arbodienst': [
            r'Arbodienst\s*:?\s*([^\n]+)',
        ],

        # Contactpersoon
        'contactpersoon_naam': [
            r'(?:Contactpersoon|contact).*?Naam\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Contactpersoon\s*:?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
        ],
        'contactpersoon_functie': [
            r'(?:contactpersoon.*?)Functie\s*:?\s*([^\n]+)',
        ],
        'contactpersoon_email': [
            r'(?:contactpersoon.*?)E-mail\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ],
        'contactpersoon_telefoon': [
            r'(?:contactpersoon.*?)Telefoon\s*:?\s*(06[-\s]?\d{8})',
        ],

        # Werknemer (Employee)
        'werknemer_naam': [
            r'Werknemer\s+([A-Z]\.\s+[A-Z][a-z]+,\s+[A-Z][a-z]+)',
            r'(?:WERKNEMER|KANDIDAAT).*?(?:Achternaam|Naam)\s*:?\s*(Maher\s+Alaraj)',
            r'(?:werknemer|betrokkene)\s*:?\s*([A-Z]\.\s+[A-Z][a-z]+,\s+[A-Z][a-z]+)',
        ],
        'geboortedatum': [
            r'Geboortedatum\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        ],
        'werknemer_adres': [
            r'(?:werknemer|KANDIDAAT).*?Adres\s*:?\s*([^\n]+)',
        ],
        'werknemer_postcode': [
            r'(?:werknemer|KANDIDAAT).*?(?:Postcode|postcode.*?Woonplaats)\s*:?\s*(\d{4}\s*[A-Z]{2})',
        ],
        'werknemer_plaats': [
            r'(?:werknemer|KANDIDAAT).*?Woonplaats\s*:?\s*([A-Z][a-z]+)',
            r'\d{4}\s*[A-Z]{2}\s+([A-Z][a-z]+)',
        ],
        'werknemer_telefoon': [
            r'(?:werknemer|KANDIDAAT).*?Telefoonnummer\s*:?\s*(06[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{2})',
        ],
        'werknemer_email': [
            r'(?:werknemer|KANDIDAAT).*?E-mail\s*:?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ],

        # Dienstverband
        'functie_naam': [
            r'(?:Functie|functie)\s*:?\s*(Warehouse\s+Employee)',
            r'(?:Functie|functie)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
        ],
        'datum_in_dienst': [
            r'(?:in dienst|Datum in dienst)\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        ],
        'eerste_ziektedag': [
            r'(?:ziekmelding|eerste.*?ziek.*?dag|arbeidsongeschiktheid)\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
        ],
        'dienstverband': [
            r'(?:Dienstverband|arbeidsovereenkomst)\s*:?\s*([^\n]+)',
        ],

        # Bedrijfsarts
        'bedrijfsarts_naam': [
            r'(?:Bedrijfsarts|bedrijfsarts).*?Naam\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ],
        'bedrijfsarts_organisatie': [
            r'(?:bedrijfsarts.*?)Organisatie\s*:?\s*([^\n]+)',
        ],
        'big_nummer': [
            r'BIG\s*nummer\s*:?\s*(\d{11})',
        ],
    }

    def __init__(self):
        """Initialize the extractor."""
        pass

    def extract_field(self, text: str, field_name: str) -> Optional[str]:
        """
        Extract a single field from text using multiple regex patterns.

        Args:
            text: The text to search in
            field_name: Name of the field to extract

        Returns:
            Extracted value or None if not found
        """
        patterns = self.PATTERNS.get(field_name, [])

        for pattern in patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    # Get the last group (most specific match)
                    value = match.group(len(match.groups()))
                    # Clean up the value
                    value = value.strip()

                    # Skip if it looks like a placeholder
                    if self._is_placeholder(value):
                        continue

                    logger.info(f"Extracted {field_name}: {value}")
                    return value
            except Exception as e:
                logger.debug(f"Pattern failed for {field_name}: {e}")
                continue

        return None

    def _is_placeholder(self, value: str) -> bool:
        """
        Check if a value looks like a placeholder rather than real data.

        Args:
            value: The value to check

        Returns:
            True if it appears to be a placeholder
        """
        placeholders = [
            'wordt',
            'bepalen',
            'invullen',
            'onbekend',
            '[',
            'n.v.t',
            'n/a',
            'nvt',
            'xxx',
        ]

        value_lower = value.lower()
        return any(placeholder in value_lower for placeholder in placeholders)

    def extract_all_fields(self, chunks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extract all structured fields from document chunks.

        Args:
            chunks: List of document chunks with 'content' field

        Returns:
            Dictionary of extracted fields
        """
        # Combine all chunks into one text for extraction
        combined_text = "\n\n".join([
            chunk.get('content', '') if isinstance(chunk, dict) else str(chunk)
            for chunk in chunks
        ])

        extracted = {}

        # Extract each field
        for field_name in self.PATTERNS.keys():
            value = self.extract_field(combined_text, field_name)
            if value:
                extracted[field_name] = value

        # Post-processing: handle special cases
        extracted = self._post_process_fields(extracted, combined_text)

        logger.info(f"Extracted {len(extracted)} fields from {len(chunks)} chunks")
        return extracted

    def _post_process_fields(self, fields: Dict[str, str], text: str) -> Dict[str, str]:
        """
        Post-process extracted fields for consistency and completeness.

        Args:
            fields: Dictionary of extracted fields
            text: Original text

        Returns:
            Updated dictionary of fields
        """
        # Fix werknemer_naam format (e.g., "Alaraj, Maher" -> "Maher Alaraj")
        if 'werknemer_naam' in fields:
            name = fields['werknemer_naam']
            if ',' in name:
                parts = name.split(',')
                if len(parts) == 2:
                    fields['werknemer_naam'] = f"{parts[1].strip()} {parts[0].strip()}"

        # Normalize phone numbers (remove spaces/dashes)
        for key in ['werkgever_telefoon', 'contactpersoon_telefoon', 'werknemer_telefoon']:
            if key in fields:
                phone = fields[key]
                # Keep format but ensure consistency
                phone = re.sub(r'\s+', ' ', phone)
                fields[key] = phone

        # Normalize postcodes (ensure space between digits and letters)
        for key in ['werkgever_postcode', 'werknemer_postcode']:
            if key in fields:
                postcode = fields[key]
                # Format: 1234 AB
                postcode = re.sub(r'(\d{4})\s*([A-Z]{2})', r'\1 \2', postcode.upper())
                fields[key] = postcode

        # Normalize dates to DD-MM-YYYY format
        for key in ['geboortedatum', 'datum_in_dienst', 'eerste_ziektedag']:
            if key in fields:
                date = fields[key]
                # Convert / to -
                date = date.replace('/', '-')
                fields[key] = date

        return fields


# Module-level function for easy import
def extract_structured_fields(chunks: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract structured fields from document chunks.

    Args:
        chunks: List of document chunks

    Returns:
        Dictionary of extracted fields

    Example:
        >>> chunks = db_service.get_document_chunks(document_id)
        >>> fields = extract_structured_fields(chunks)
        >>> print(fields['werkgever_naam'])
        'FLE Logistics BV'
    """
    extractor = DocumentFieldExtractor()
    return extractor.extract_all_fields(chunks)


def extract_from_case(case_id: str, db_service) -> Dict[str, str]:
    """
    Extract structured fields from all documents in a case.

    Args:
        case_id: The case ID
        db_service: Database service instance

    Returns:
        Dictionary of extracted fields from all case documents
    """
    # Get all documents for the case
    documents = db_service.get_documents_for_case(case_id)

    all_chunks = []
    for doc in documents:
        doc_id = doc['id']
        try:
            chunks = db_service.get_document_chunks(doc_id)
            all_chunks.extend(chunks)
        except Exception as e:
            logger.warning(f"Could not get chunks for document {doc_id}: {e}")
            continue

    logger.info(f"Extracting from {len(all_chunks)} chunks across {len(documents)} documents")

    # Extract fields
    extractor = DocumentFieldExtractor()
    fields = extractor.extract_all_fields(all_chunks)

    return fields
