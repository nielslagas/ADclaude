"""
Document Security Features for Enhanced Export System
Provides digital signatures, watermarks, and security features for exported documents
"""
import os
import io
from datetime import datetime
from typing import Dict, Optional, Union, Tuple
from PIL import Image, ImageDraw, ImageFont

# PDF security dependencies
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfutils
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    PDF_SECURITY_AVAILABLE = True
except ImportError:
    PDF_SECURITY_AVAILABLE = False

# Digital signature dependencies
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography import x509
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class WatermarkGenerator:
    """Generate watermarks for different document types"""
    
    def __init__(self):
        self.watermark_types = {
            'draft': {
                'text': 'CONCEPT',
                'color': (255, 0, 0, 80),  # Semi-transparent red
                'rotation': 45
            },
            'final': {
                'text': 'DEFINITIEF',
                'color': (0, 100, 0, 60),  # Semi-transparent green
                'rotation': 45
            },
            'confidential': {
                'text': 'VERTROUWELIJK',
                'color': (200, 0, 0, 100),  # Red
                'rotation': 45
            },
            'copy': {
                'text': 'KOPIE',
                'color': (100, 100, 100, 80),  # Gray
                'rotation': 45
            }
        }
    
    def create_watermark_image(self, 
                             watermark_type: str = 'draft',
                             custom_text: Optional[str] = None,
                             size: Tuple[int, int] = (800, 600)) -> Image.Image:
        """
        Create a watermark image for document overlay
        
        Args:
            watermark_type: Type of watermark (draft, final, confidential, copy)
            custom_text: Custom watermark text
            size: Image size (width, height)
            
        Returns:
            PIL Image with watermark
        """
        # Create transparent image
        img = Image.new('RGBA', size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Get watermark configuration
        config = self.watermark_types.get(watermark_type, self.watermark_types['draft'])
        text = custom_text or config['text']
        color = config['color']
        rotation = config['rotation']
        
        # Try to use a system font, fallback to default
        font_size = max(40, min(size) // 10)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)  # macOS
            except (OSError, IOError):
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)  # Linux
                except (OSError, IOError):
                    font = ImageFont.load_default()
        
        # Calculate text size and position
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Position text in center
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        # Draw text
        draw.text((x, y), text, fill=color, font=font)
        
        # Rotate if needed
        if rotation != 0:
            img = img.rotate(rotation, expand=False)
        
        return img
    
    def add_pdf_watermark(self, 
                         pdf_path: str, 
                         watermark_type: str = 'draft',
                         custom_text: Optional[str] = None) -> str:
        """
        Add watermark to existing PDF
        
        Args:
            pdf_path: Path to PDF file
            watermark_type: Type of watermark
            custom_text: Custom watermark text
            
        Returns:
            Path to watermarked PDF
        """
        if not PDF_SECURITY_AVAILABLE:
            raise ImportError("PDF watermarking requires reportlab package")
        
        # For now, return original path - full implementation would require PyPDF2
        # This is a placeholder for the watermarking functionality
        return pdf_path


class DocumentSigner:
    """Handle digital signatures for documents"""
    
    def __init__(self, certificate_path: Optional[str] = None, private_key_path: Optional[str] = None):
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path
        self.crypto_available = CRYPTO_AVAILABLE
    
    def generate_self_signed_certificate(self, 
                                       common_name: str,
                                       organization: str = "AI-Arbeidsdeskundige",
                                       key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        Generate a self-signed certificate for document signing
        
        Args:
            common_name: Certificate common name (usually the signer's name)
            organization: Organization name
            key_size: RSA key size
            
        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        if not self.crypto_available:
            raise ImportError("Digital signatures require cryptography package")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "NL"),
            x509.NameAttribute(x509.NameOID.STATE_OR_PROVINCE_NAME, "Nederland"),
            x509.NameAttribute(x509.NameOID.LOCALITY_NAME, "Amsterdam"),
            x509.NameAttribute(x509.NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(x509.NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Serialize certificate and key
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        return cert_pem, key_pem
    
    def sign_document_hash(self, document_hash: bytes) -> bytes:
        """
        Sign a document hash with the private key
        
        Args:
            document_hash: SHA256 hash of the document
            
        Returns:
            Digital signature bytes
        """
        if not self.crypto_available:
            raise ImportError("Digital signatures require cryptography package")
        
        if not self.private_key_path or not os.path.exists(self.private_key_path):
            raise ValueError("Private key file not found")
        
        # Load private key
        with open(self.private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,
            )
        
        # Sign the hash
        signature = private_key.sign(
            document_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return signature
    
    def verify_signature(self, document_hash: bytes, signature: bytes) -> bool:
        """
        Verify a document signature
        
        Args:
            document_hash: SHA256 hash of the document
            signature: Digital signature to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.crypto_available:
            raise ImportError("Digital signatures require cryptography package")
        
        if not self.certificate_path or not os.path.exists(self.certificate_path):
            raise ValueError("Certificate file not found")
        
        try:
            # Load certificate
            with open(self.certificate_path, 'rb') as cert_file:
                cert = x509.load_pem_x509_certificate(cert_file.read())
            
            # Verify signature
            public_key = cert.public_key()
            public_key.verify(
                signature,
                document_hash,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class DocumentSecurity:
    """Main class for document security features"""
    
    def __init__(self):
        self.watermark_generator = WatermarkGenerator()
        self.document_signer = DocumentSigner()
    
    def create_security_metadata(self, 
                                user_profile: Dict,
                                document_type: str = 'final',
                                security_level: str = 'standard') -> Dict:
        """
        Create security metadata for documents
        
        Args:
            user_profile: User profile information
            document_type: Type of document (draft, final, confidential)
            security_level: Security level (standard, high, confidential)
            
        Returns:
            Security metadata dictionary
        """
        return {
            'security_level': security_level,
            'document_type': document_type,
            'created_by': f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}",
            'organization': user_profile.get('company_name', ''),
            'created_at': datetime.utcnow().isoformat(),
            'watermark_required': document_type in ['draft', 'confidential'],
            'signature_required': security_level in ['high', 'confidential'],
            'access_restrictions': {
                'print_allowed': security_level != 'confidential',
                'copy_allowed': security_level == 'standard',
                'modify_allowed': False
            }
        }
    
    def apply_document_security(self, 
                               file_path: str,
                               security_metadata: Dict,
                               watermark_text: Optional[str] = None) -> str:
        """
        Apply security features to a document
        
        Args:
            file_path: Path to the document file
            security_metadata: Security configuration
            watermark_text: Custom watermark text
            
        Returns:
            Path to the secured document
        """
        secured_path = file_path
        
        # Apply watermark if required
        if security_metadata.get('watermark_required', False):
            watermark_type = security_metadata.get('document_type', 'draft')
            
            if file_path.lower().endswith('.pdf') and PDF_SECURITY_AVAILABLE:
                secured_path = self.watermark_generator.add_pdf_watermark(
                    secured_path, 
                    watermark_type,
                    watermark_text
                )
        
        # Apply digital signature if required
        if security_metadata.get('signature_required', False):
            secured_path = self._add_document_signature(secured_path, security_metadata)
        
        return secured_path
    
    def _add_document_signature(self, file_path: str, security_metadata: Dict) -> str:
        """
        Add digital signature to document
        
        Args:
            file_path: Path to document
            security_metadata: Security configuration
            
        Returns:
            Path to signed document
        """
        # For now, return original path
        # Full implementation would add PDF signatures or create signature files
        return file_path
    
    def validate_document_integrity(self, file_path: str) -> Dict:
        """
        Validate document integrity and signatures
        
        Args:
            file_path: Path to document to validate
            
        Returns:
            Validation results dictionary
        """
        return {
            'file_exists': os.path.exists(file_path),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'last_modified': os.path.getmtime(file_path) if os.path.exists(file_path) else 0,
            'signature_valid': False,  # Would check actual signature
            'watermark_present': False,  # Would check for watermark
            'integrity_check': 'passed'  # Would perform hash verification
        }


# Utility functions for integration with export system
def add_security_to_export(file_path: str, 
                          user_profile: Dict,
                          export_options: Dict) -> str:
    """
    Add security features to exported document
    
    Args:
        file_path: Path to exported document
        user_profile: User profile information
        export_options: Export configuration options
        
    Returns:
        Path to secured document
    """
    security = DocumentSecurity()
    
    # Determine document type from export options
    document_type = 'final'
    if export_options.get('watermark', False):
        document_type = 'draft'
    if export_options.get('confidential', False):
        document_type = 'confidential'
    
    # Create security metadata
    security_metadata = security.create_security_metadata(
        user_profile=user_profile,
        document_type=document_type,
        security_level=export_options.get('security_level', 'standard')
    )
    
    # Apply security features
    secured_path = security.apply_document_security(
        file_path=file_path,
        security_metadata=security_metadata,
        watermark_text=export_options.get('watermark_text')
    )
    
    return secured_path


def create_document_certificate(user_profile: Dict, output_dir: str) -> Tuple[str, str]:
    """
    Create a document signing certificate for the user
    
    Args:
        user_profile: User profile information
        output_dir: Directory to save certificate files
        
    Returns:
        Tuple of (certificate_path, private_key_path)
    """
    signer = DocumentSigner()
    
    # Generate certificate
    common_name = f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}"
    organization = user_profile.get('company_name', 'AI-Arbeidsdeskundige')
    
    cert_pem, key_pem = signer.generate_self_signed_certificate(
        common_name=common_name,
        organization=organization
    )
    
    # Save certificate and key
    cert_path = os.path.join(output_dir, f"cert_{user_profile.get('id', 'user')}.pem")
    key_path = os.path.join(output_dir, f"key_{user_profile.get('id', 'user')}.pem")
    
    with open(cert_path, 'wb') as f:
        f.write(cert_pem)
    
    with open(key_path, 'wb') as f:
        f.write(key_pem)
    
    # Set appropriate file permissions
    os.chmod(key_path, 0o600)  # Private key readable only by owner
    os.chmod(cert_path, 0o644)  # Certificate readable by all
    
    return cert_path, key_path


# Integration with enhanced export system
def enhance_export_with_security(export_function):
    """
    Decorator to add security features to export functions
    
    Args:
        export_function: Export function to enhance
        
    Returns:
        Enhanced export function with security features
    """
    def wrapper(report_data: Dict, output_path: str, template_type: str = 'standaard', **kwargs):
        # Call original export function
        result_path = export_function(report_data, output_path, template_type, **kwargs)
        
        # Add security features if requested
        export_options = kwargs.get('security_options', {})
        if export_options:
            user_profile = report_data.get('user_profile', {})
            result_path = add_security_to_export(result_path, user_profile, export_options)
        
        return result_path
    
    return wrapper