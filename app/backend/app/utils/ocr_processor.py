"""
OCR (Optical Character Recognition) utility for extracting text from images and scanned documents.
Uses Tesseract OCR with Dutch and English language support.

This module provides functions to:
- Extract text from image files (JPG, PNG, TIFF)
- Extract text from scanned PDF files
- Check Tesseract availability

Requirements:
- System: tesseract-ocr must be installed
- Python: pytesseract, pillow, pdf2image
- Language packs: tesseract-ocr-nld (Dutch), tesseract-ocr-eng (English)

Installation:
    Ubuntu/Debian:
        sudo apt-get install tesseract-ocr tesseract-ocr-nld tesseract-ocr-eng poppler-utils

    MacOS:
        brew install tesseract tesseract-lang poppler

    Windows:
        Download from: https://github.com/UB-Mannheim/tesseract/wiki
        Add to PATH: C:\\Program Files\\Tesseract-OCR

Usage:
    from app.utils.ocr_processor import extract_text_with_ocr, ocr_pdf

    # Extract from image
    with open("document.jpg", "rb") as f:
        text = extract_text_with_ocr(f.read())

    # Extract from scanned PDF
    with open("scanned.pdf", "rb") as f:
        text = ocr_pdf(f.read())
"""

import pytesseract
from PIL import Image
import io
import logging
from typing import Optional, Tuple
import time

logger = logging.getLogger(__name__)


def extract_text_with_ocr(
    file_content: bytes,
    language: str = "nld+eng",
    config: str = "--psm 1",
    dpi: int = 300
) -> str:
    """
    Extract text from image using Tesseract OCR.

    Args:
        file_content: Image file bytes (PNG, JPG, TIFF, etc.)
        language: Tesseract language codes
                 - "nld" = Dutch only
                 - "eng" = English only
                 - "nld+eng" = Dutch + English (default)
        config: Tesseract config string
                --psm 1 = Automatic page segmentation with OSD (Orientation and Script Detection)
                --psm 3 = Fully automatic page segmentation (default)
                --psm 6 = Assume uniform block of text
        dpi: DPI resolution for OCR (higher = better quality, slower)

    Returns:
        Extracted text string (empty string if OCR fails)

    Example:
        with open("medical_report.jpg", "rb") as f:
            text = extract_text_with_ocr(f.read(), language="nld")
    """
    start_time = time.time()

    try:
        logger.info(f"Starting OCR with language={language}, config='{config}', dpi={dpi}")

        # Open image from bytes
        image = Image.open(io.BytesIO(file_content))

        # Log image info
        logger.debug(f"Image size: {image.size}, mode: {image.mode}, format: {image.format}")

        # Convert to RGB if necessary (some PDFs convert to CMYK)
        if image.mode not in ('RGB', 'L', 'P'):
            logger.debug(f"Converting image from {image.mode} to RGB")
            image = image.convert('RGB')

        # Enhance image quality if needed
        # Note: Could add preprocessing here (deskew, denoise, etc.)

        # Extract text with Tesseract
        text = pytesseract.image_to_string(
            image,
            lang=language,
            config=config
        )

        # Calculate processing time
        elapsed = time.time() - start_time

        if text.strip():
            logger.info(f"OCR extracted {len(text)} characters in {elapsed:.2f}s")
        else:
            logger.warning(f"OCR completed but no text extracted (elapsed: {elapsed:.2f}s)")

        return text

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract OCR is not installed or not in PATH")
        logger.error("Install: sudo apt-get install tesseract-ocr tesseract-ocr-nld")
        return ""
    except Exception as e:
        logger.error(f"OCR failed: {type(e).__name__}: {e}")
        return ""


def ocr_pdf(
    file_content: bytes,
    language: str = "nld+eng",
    dpi: int = 300,
    max_pages: Optional[int] = None
) -> str:
    """
    Extract text from scanned PDF using OCR.

    Converts each PDF page to an image and runs Tesseract OCR on it.
    This is significantly slower than regular PDF text extraction but works
    for scanned documents without embedded text.

    Args:
        file_content: PDF file bytes
        language: Tesseract language codes (e.g., "nld+eng")
        dpi: DPI resolution for image conversion (200-300 recommended)
        max_pages: Maximum number of pages to process (None = all pages)

    Returns:
        Extracted text from all pages, separated by page markers

    Example:
        with open("scanned_report.pdf", "rb") as f:
            text = ocr_pdf(f.read(), language="nld", dpi=300)

    Note:
        This function requires poppler-utils to be installed:
        - Ubuntu/Debian: sudo apt-get install poppler-utils
        - MacOS: brew install poppler
    """
    start_time = time.time()

    try:
        from pdf2image import convert_from_bytes

        logger.info(f"Converting PDF to images for OCR (dpi={dpi})")

        # Convert PDF to images (one per page)
        images = convert_from_bytes(
            file_content,
            dpi=dpi,
            fmt='png'  # PNG format for better quality
        )

        total_pages = len(images)
        logger.info(f"PDF converted to {total_pages} images")

        # Limit pages if specified
        if max_pages:
            images = images[:max_pages]
            logger.info(f"Processing limited to first {max_pages} pages")

        # OCR each page
        text_pages = []
        total_chars = 0

        for page_num, image in enumerate(images, 1):
            page_start = time.time()
            logger.debug(f"OCR processing page {page_num}/{len(images)}")

            # Run OCR on page image
            text = pytesseract.image_to_string(
                image,
                lang=language,
                config="--psm 1"  # Automatic page segmentation with OSD
            )

            page_elapsed = time.time() - page_start

            if text.strip():
                text_pages.append(
                    f"--- Pagina {page_num} van {len(images)} (OCR) ---\n{text}"
                )
                total_chars += len(text)
                logger.debug(
                    f"Page {page_num}: extracted {len(text)} chars in {page_elapsed:.2f}s"
                )
            else:
                logger.warning(f"Page {page_num}: no text extracted (possibly blank page)")
                text_pages.append(
                    f"--- Pagina {page_num} van {len(images)} (OCR) ---\n[Geen tekst gedetecteerd]"
                )

        # Combine all pages
        result = "\n\n".join(text_pages)
        elapsed = time.time() - start_time

        logger.info(
            f"OCR complete: {total_chars} total characters from {len(images)} pages "
            f"in {elapsed:.2f}s (avg {elapsed/len(images):.2f}s/page)"
        )

        return result

    except ImportError:
        logger.error("pdf2image not installed - cannot convert PDF to images")
        logger.error("Install: pip install pdf2image")
        logger.error("System dependency: sudo apt-get install poppler-utils")
        return ""
    except Exception as e:
        logger.error(f"PDF OCR failed: {type(e).__name__}: {e}")
        return ""


def extract_text_with_confidence(
    file_content: bytes,
    language: str = "nld+eng",
    min_confidence: float = 60.0
) -> Tuple[str, float]:
    """
    Extract text from image with confidence scoring.

    This function provides OCR results along with a confidence score,
    which can be used to determine if the OCR quality is acceptable.

    Args:
        file_content: Image file bytes
        language: Tesseract language codes
        min_confidence: Minimum confidence threshold (0-100)

    Returns:
        Tuple of (extracted_text, average_confidence)
        - extracted_text: Extracted text string
        - average_confidence: Average confidence score (0-100)

    Example:
        text, confidence = extract_text_with_confidence(image_bytes)
        if confidence >= 80:
            print(f"High quality OCR: {confidence:.1f}%")
        else:
            print(f"Low quality OCR: {confidence:.1f}% - manual review needed")
    """
    try:
        logger.info(f"Starting OCR with confidence scoring (min_confidence={min_confidence})")

        # Open image
        image = Image.open(io.BytesIO(file_content))

        # Convert to RGB if necessary
        if image.mode not in ('RGB', 'L', 'P'):
            image = image.convert('RGB')

        # Get detailed OCR data including confidence scores
        ocr_data = pytesseract.image_to_data(
            image,
            lang=language,
            output_type=pytesseract.Output.DICT
        )

        # Extract text and calculate average confidence
        text_parts = []
        confidences = []

        for i, text in enumerate(ocr_data['text']):
            conf = int(ocr_data['conf'][i])

            # Only include text with sufficient confidence
            if conf >= min_confidence and text.strip():
                text_parts.append(text)
                confidences.append(conf)

        # Combine text
        extracted_text = ' '.join(text_parts)

        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(
            f"OCR extracted {len(extracted_text)} characters "
            f"with average confidence {avg_confidence:.1f}%"
        )

        return extracted_text, avg_confidence

    except Exception as e:
        logger.error(f"OCR with confidence failed: {e}")
        return "", 0.0


def is_tesseract_available() -> bool:
    """
    Check if Tesseract OCR is installed and accessible.

    This function verifies that:
    1. pytesseract can find the Tesseract executable
    2. Tesseract is properly configured
    3. At least one language pack is installed

    Returns:
        True if Tesseract is available and working, False otherwise

    Example:
        if is_tesseract_available():
            text = extract_text_with_ocr(image_bytes)
        else:
            print("Tesseract not installed - OCR unavailable")
    """
    try:
        # Get Tesseract version (this will fail if not installed)
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract OCR version: {version}")

        # Check available languages
        languages = pytesseract.get_languages()
        logger.info(f"Available Tesseract languages: {', '.join(languages)}")

        # Verify Dutch and English are available
        required_langs = ['nld', 'eng']
        missing_langs = [lang for lang in required_langs if lang not in languages]

        if missing_langs:
            logger.warning(
                f"Missing language packs: {', '.join(missing_langs)}. "
                f"Install: sudo apt-get install tesseract-ocr-{missing_langs[0]}"
            )

        return True

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract OCR is not installed or not in PATH")
        logger.error("Install instructions:")
        logger.error("  Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-nld tesseract-ocr-eng")
        logger.error("  MacOS: brew install tesseract tesseract-lang")
        logger.error("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except Exception as e:
        logger.error(f"Tesseract availability check failed: {e}")
        return False


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy.

    Applies various image enhancement techniques:
    - Grayscale conversion
    - Contrast enhancement
    - Noise reduction
    - Thresholding

    Args:
        image: PIL Image object

    Returns:
        Preprocessed PIL Image object

    Note:
        This is an advanced feature. Basic OCR often works without preprocessing.
    """
    try:
        from PIL import ImageEnhance, ImageFilter

        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Remove noise
        image = image.filter(ImageFilter.MedianFilter(size=3))

        # Apply threshold (convert to black and white)
        # This often improves OCR accuracy
        threshold = 128
        image = image.point(lambda p: 255 if p > threshold else 0)

        logger.debug("Image preprocessed for OCR")
        return image

    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}, using original image")
        return image
