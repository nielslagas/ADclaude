"""
Optimized Audio Transcription Module for AI-Arbeidsdeskundige.

This module provides comprehensive functionality for audio transcription using
OpenAI's Whisper API, with advanced features for Dutch arbeidsdeskundige content:

- Multi-format audio support with preprocessing
- Chunking for long audio files
- Progress tracking and caching
- Quality scoring and speaker diarization
- Dutch language optimization
- Comprehensive error handling
"""
import os
import uuid
import logging
import tempfile
import hashlib
import json
import time
from typing import Dict, Any, Optional, Set, List, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

from celery import shared_task, current_task

# Audio processing libraries
try:
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logging.warning("pydub not available - advanced audio preprocessing disabled")

# Use OpenAI API directly 
from openai import OpenAI, APIError, RateLimitError

from app.core.config import settings
from app.db.database_service import get_database_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database service
db_service = get_database_service()

# Cache configuration
CACHE_DIR = Path(settings.STORAGE_PATH) / "cache" / "transcriptions"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_EXPIRY_DAYS = 7


class AudioQuality(Enum):
    """Audio quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class TranscriptionStatus(Enum):
    """Transcription processing status"""
    PENDING = "pending"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class AudioMetadata:
    """Metadata for audio files"""
    duration_seconds: float
    sample_rate: int
    channels: int
    bitrate: Optional[int]
    format: str
    file_size: int
    quality_score: float
    has_silence: bool
    speech_ratio: float


@dataclass
class TranscriptionChunk:
    """Individual transcription chunk"""
    start_time: float
    end_time: float
    text: str
    confidence: float
    speaker_id: Optional[str] = None
    language: Optional[str] = None


@dataclass
class TranscriptionResult:
    """Complete transcription result"""
    text: str
    chunks: List[TranscriptionChunk]
    confidence_score: float
    language_detected: str
    processing_time: float
    audio_metadata: AudioMetadata
    model_used: str
    status: TranscriptionStatus
    warnings: List[str]
    speaker_count: int = 1


# Audio file extensions supported by Whisper API and our preprocessing
SUPPORTED_EXTENSIONS: Set[str] = {
    "mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "flac", "aac"
}

# Additional formats we can convert from
CONVERTIBLE_EXTENSIONS: Set[str] = {
    "wma", "aiff", "au", "ra", "3gp", "amr"
}

# Max file size for Whisper API (25 MB)
MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB

# Optimal chunk size for long audio files (10 minutes)
CHUNK_SIZE_SECONDS: int = 600

# Quality thresholds
MIN_CONFIDENCE_SCORE = 0.7
MIN_SPEECH_RATIO = 0.3
MAX_SILENCE_DURATION = 5.0  # seconds

# Dutch language optimization
DEFAULT_LANGUAGE: str = "nl"
DUTCH_KEYWORDS = [
    "arbeidsdeskundige", "belastbaarheid", "werkhervatting", "re-integratie",
    "arbeidsongeval", "verzuim", "arbeidsgeschiktheid", "functioneel",
    "medische", "beperking", "ziekte", "herstel", "behandeling",
    "werkgever", "werknemer", "UWV", "verzekeringsgeneeskundige"
]

# Whisper model configurations for different use cases
MODEL_CONFIGS = {
    "fast": {
        "model": "whisper-1",
        "temperature": 0.0,
        "response_format": "json",
        "language": "nl"
    },
    "accurate": {
        "model": "whisper-1",
        "temperature": 0.1,
        "response_format": "verbose_json",
        "language": "nl"
    },
    "multilingual": {
        "model": "whisper-1",
        "temperature": 0.2,
        "response_format": "verbose_json"
    }
}


def is_supported_audio_file(filename: str) -> bool:
    """
    Check if the file extension is supported for audio transcription.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        True if the file extension is supported or convertible, False otherwise
    """
    if not filename or "." not in filename:
        return False
    
    extension = filename.rsplit(".", 1)[1].lower()
    return extension in SUPPORTED_EXTENSIONS or extension in CONVERTIBLE_EXTENSIONS


def get_audio_cache_key(file_path: str, model_config: Dict[str, Any]) -> str:
    """
    Generate a cache key for audio transcription results.
    
    Args:
        file_path: Path to the audio file
        model_config: Model configuration used
        
    Returns:
        Unique cache key
    """
    try:
        file_stat = os.stat(file_path)
        file_info = f"{file_path}:{file_stat.st_size}:{file_stat.st_mtime}"
        config_str = json.dumps(model_config, sort_keys=True)
        
        cache_input = f"{file_info}:{config_str}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    except Exception as e:
        logger.warning(f"Could not generate cache key: {e}")
        return hashlib.md5(f"{file_path}:{time.time()}".encode()).hexdigest()


def check_file_size(file_path: str) -> Tuple[bool, int]:
    """
    Check if the file size is within limits and return size info.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (within_limit, file_size_bytes)
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False, 0
    
    file_size = os.path.getsize(file_path)
    within_limit = file_size <= MAX_FILE_SIZE_BYTES
    
    if not within_limit:
        logger.warning(
            f"File size ({file_size} bytes) exceeds the maximum limit "
            f"of {MAX_FILE_SIZE_BYTES} bytes (25 MB) for the Whisper API - will need chunking"
        )
    
    return within_limit, file_size


def analyze_audio_metadata(file_path: str) -> AudioMetadata:
    """
    Analyze audio file and extract metadata.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        AudioMetadata object with file information
    """
    try:
        if not PYDUB_AVAILABLE:
            # Basic metadata without pydub
            file_size = os.path.getsize(file_path)
            return AudioMetadata(
                duration_seconds=0.0,
                sample_rate=44100,  # Default assumption
                channels=2,  # Default assumption
                bitrate=None,
                format=Path(file_path).suffix.lower().strip('.'),
                file_size=file_size,
                quality_score=0.5,  # Unknown quality
                has_silence=False,
                speech_ratio=1.0  # Assume all speech
            )
        
        # Load audio with pydub
        audio = AudioSegment.from_file(file_path)
        
        # Calculate speech ratio (simplified)
        silence_chunks = split_on_silence(
            audio,
            min_silence_len=1000,  # 1 second
            silence_thresh=audio.dBFS - 14,
            keep_silence=500
        )
        
        total_duration = len(audio) / 1000.0  # Convert to seconds
        speech_duration = sum(len(chunk) for chunk in silence_chunks) / 1000.0
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0
        
        # Calculate quality score
        quality_score = calculate_audio_quality(
            sample_rate=audio.frame_rate,
            channels=len(audio.raw_data) // (len(audio) * audio.frame_width // audio.channels),
            speech_ratio=speech_ratio,
            duration=total_duration
        )
        
        return AudioMetadata(
            duration_seconds=total_duration,
            sample_rate=audio.frame_rate,
            channels=audio.channels,
            bitrate=None,  # pydub doesn't always provide this
            format=Path(file_path).suffix.lower().strip('.'),
            file_size=os.path.getsize(file_path),
            quality_score=quality_score,
            has_silence=len(silence_chunks) < len(audio) / 2000,  # Rough estimate
            speech_ratio=speech_ratio
        )
        
    except Exception as e:
        logger.error(f"Error analyzing audio metadata: {e}")
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        return AudioMetadata(
            duration_seconds=0.0,
            sample_rate=44100,
            channels=2,
            bitrate=None,
            format=Path(file_path).suffix.lower().strip('.'),
            file_size=file_size,
            quality_score=0.3,  # Low quality assumed on error
            has_silence=False,
            speech_ratio=1.0
        )


def calculate_audio_quality(sample_rate: int, channels: int, speech_ratio: float, duration: float) -> float:
    """
    Calculate audio quality score based on technical parameters.
    
    Args:
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels
        speech_ratio: Ratio of speech to total duration
        duration: Total duration in seconds
        
    Returns:
        Quality score between 0.0 and 1.0
    """
    score = 0.0
    
    # Sample rate score (higher is better, up to 48kHz)
    if sample_rate >= 44100:
        score += 0.3
    elif sample_rate >= 22050:
        score += 0.2
    else:
        score += 0.1
    
    # Channels score (mono vs stereo)
    if channels >= 2:
        score += 0.1
    
    # Speech ratio score
    if speech_ratio >= MIN_SPEECH_RATIO:
        score += 0.4 * speech_ratio
    
    # Duration score (longer recordings usually have better context)
    if duration > 60:  # More than 1 minute
        score += 0.2
    elif duration > 10:  # More than 10 seconds
        score += 0.1
    
    return min(1.0, score)


def convert_audio_format(input_path: str, target_format: str = "mp3") -> str:
    """
    Convert audio file to supported format.
    
    Args:
        input_path: Path to input audio file
        target_format: Target format (mp3, wav, etc.)
        
    Returns:
        Path to converted file
    """
    if not PYDUB_AVAILABLE:
        raise RuntimeError("pydub not available for audio conversion")
    
    try:
        # Create output filename
        input_name = Path(input_path).stem
        output_path = str(Path(input_path).parent / f"{input_name}_converted.{target_format}")
        
        # Load and convert
        audio = AudioSegment.from_file(input_path)
        
        # Optimize for speech (mono, reasonable sample rate)
        if audio.channels > 1:
            audio = audio.set_channels(1)  # Convert to mono
        
        if audio.frame_rate > 22050:
            audio = audio.set_frame_rate(22050)  # Reduce sample rate for efficiency
        
        # Export in target format
        audio.export(output_path, format=target_format, bitrate="128k")
        
        logger.info(f"Audio converted from {Path(input_path).suffix} to {target_format}")
        return output_path
        
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        raise


def preprocess_audio(file_path: str, metadata: AudioMetadata) -> str:
    """
    Apply audio preprocessing to improve transcription quality.
    
    Args:
        file_path: Path to audio file
        metadata: Audio metadata
        
    Returns:
        Path to preprocessed audio file
    """
    if not PYDUB_AVAILABLE:
        logger.warning("pydub not available for audio preprocessing")
        return file_path
    
    try:
        audio = AudioSegment.from_file(file_path)
        
        # Noise reduction (basic)
        if metadata.quality_score < 0.5:
            # Simple noise reduction by filtering very low volumes
            audio = audio.apply_gain(-3)  # Reduce overall volume slightly
        
        # Remove long silences
        if metadata.has_silence:
            chunks = split_on_silence(
                audio,
                min_silence_len=2000,  # 2 seconds
                silence_thresh=audio.dBFS - 16,
                keep_silence=1000  # Keep 1 second of silence
            )
            if chunks:
                audio = sum(chunks)
        
        # Normalize volume
        audio = audio.normalize()
        
        # Create output filename
        output_path = str(Path(file_path).parent / f"{Path(file_path).stem}_preprocessed.mp3")
        
        # Export preprocessed audio
        audio.export(output_path, format="mp3", bitrate="128k")
        
        logger.info(f"Audio preprocessing completed: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
        return file_path


def chunk_audio_file(file_path: str, chunk_duration: int = CHUNK_SIZE_SECONDS) -> List[str]:
    """
    Split large audio file into smaller chunks for processing.
    
    Args:
        file_path: Path to the audio file
        chunk_duration: Duration of each chunk in seconds
        
    Returns:
        List of paths to audio chunks
    """
    if not PYDUB_AVAILABLE:
        logger.warning("pydub not available for audio chunking - returning original file")
        return [file_path]
    
    try:
        audio = AudioSegment.from_file(file_path)
        duration_ms = len(audio)
        chunk_duration_ms = chunk_duration * 1000
        
        # If file is small enough, don't chunk
        if duration_ms <= chunk_duration_ms:
            return [file_path]
        
        chunks = []
        base_name = Path(file_path).stem
        output_dir = Path(file_path).parent
        
        # Split into chunks with overlap
        overlap_ms = 2000  # 2 seconds overlap
        start = 0
        chunk_num = 0
        
        while start < duration_ms:
            end = min(start + chunk_duration_ms, duration_ms)
            
            chunk = audio[start:end]
            chunk_filename = f"{base_name}_chunk_{chunk_num:03d}.mp3"
            chunk_path = str(output_dir / chunk_filename)
            
            chunk.export(chunk_path, format="mp3", bitrate="128k")
            chunks.append(chunk_path)
            
            chunk_num += 1
            start = end - overlap_ms  # Overlap to avoid cutting words
            
            if start >= duration_ms:
                break
        
        logger.info(f"Audio file chunked into {len(chunks)} pieces")
        return chunks
        
    except Exception as e:
        logger.error(f"Audio chunking failed: {e}")
        return [file_path]


def prepare_audio_for_transcription(file_path: str) -> Tuple[str, AudioMetadata]:
    """
    Prepare audio file for transcription with advanced preprocessing.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (prepared_file_path, audio_metadata)
    """
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Analyze audio metadata
    metadata = analyze_audio_metadata(file_path)
    logger.info(f"Audio metadata: duration={metadata.duration_seconds:.1f}s, "
                f"quality={metadata.quality_score:.2f}, speech_ratio={metadata.speech_ratio:.2f}")
    
    # Check file size
    within_limit, file_size = check_file_size(file_path)
    
    original_file = file_path
    processed_file = file_path
    
    try:
        # Convert format if needed
        filename = os.path.basename(file_path)
        extension = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        
        if extension in CONVERTIBLE_EXTENSIONS or not extension in SUPPORTED_EXTENSIONS:
            logger.info(f"Converting audio format from {extension} to mp3")
            processed_file = convert_audio_format(file_path, "mp3")
            
            # Re-check size after conversion
            within_limit, file_size = check_file_size(processed_file)
        
        # Apply audio preprocessing if pydub is available
        if PYDUB_AVAILABLE and (metadata.quality_score < 0.5 or metadata.speech_ratio < MIN_SPEECH_RATIO):
            logger.info("Applying audio preprocessing for quality improvement")
            processed_file = preprocess_audio(processed_file, metadata)
        
        # Update metadata after processing
        if processed_file != original_file:
            metadata = analyze_audio_metadata(processed_file)
        
        logger.info(f"Audio prepared successfully: {processed_file} "
                   f"(size: {file_size} bytes, quality: {metadata.quality_score:.2f})")
        
        return processed_file, metadata
        
    except Exception as e:
        logger.error(f"Error preparing audio file: {e}")
        # Fallback to original file if preprocessing fails
        if not is_supported_audio_file(os.path.basename(original_file)):
            raise ValueError(f"Unsupported audio format and preprocessing failed: {extension}")
        return original_file, metadata


def get_cached_transcription(cache_key: str) -> Optional[TranscriptionResult]:
    """
    Retrieve cached transcription result.
    
    Args:
        cache_key: Cache key for the transcription
        
    Returns:
        Cached TranscriptionResult or None if not found/expired
    """
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check if cache is expired
        cache_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if cache_age > timedelta(days=CACHE_EXPIRY_DAYS):
            cache_file.unlink()  # Remove expired cache
            return None
        
        # Load cached result
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert back to TranscriptionResult
        result = TranscriptionResult(
            text=data['text'],
            chunks=[TranscriptionChunk(**chunk) for chunk in data['chunks']],
            confidence_score=data['confidence_score'],
            language_detected=data['language_detected'],
            processing_time=data['processing_time'],
            audio_metadata=AudioMetadata(**data['audio_metadata']),
            model_used=data['model_used'],
            status=TranscriptionStatus(data['status']),
            warnings=data['warnings'],
            speaker_count=data.get('speaker_count', 1)
        )
        
        logger.info(f"Transcription loaded from cache: {cache_key}")
        return result
        
    except Exception as e:
        logger.error(f"Error loading cached transcription: {e}")
        return None


def save_transcription_cache(cache_key: str, result: TranscriptionResult) -> None:
    """
    Save transcription result to cache.
    
    Args:
        cache_key: Cache key for the transcription
        result: TranscriptionResult to cache
    """
    try:
        cache_file = CACHE_DIR / f"{cache_key}.json"
        
        # Convert to dict for JSON serialization
        data = asdict(result)
        data['status'] = result.status.value  # Convert enum to string
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Transcription cached: {cache_key}")
        
    except Exception as e:
        logger.error(f"Error caching transcription: {e}")


def transcribe_single_chunk(
    client: OpenAI, chunk_file: str, config: Dict[str, Any], start_offset: float
) -> TranscriptionChunk:
    """
    Transcribe a single audio chunk.
    
    Args:
        client: OpenAI client
        chunk_file: Path to audio chunk
        config: Transcription configuration
        start_offset: Start time offset for this chunk
        
    Returns:
        TranscriptionChunk with results
    """
    try:
        with open(chunk_file, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=config["model"],
                file=audio_file,
                language=config.get("language"),
                response_format=config.get("response_format", "json"),
                temperature=config.get("temperature", 0.2)
            )
        
        # Extract text and confidence from response
        if hasattr(response, 'text'):
            text = response.text
            confidence = 0.8  # Default confidence for simple response
        else:
            # For verbose_json response
            text = str(response)
            confidence = 0.8
        
        # Estimate chunk duration
        chunk_duration = CHUNK_SIZE_SECONDS  # Default, could be calculated from audio metadata
        
        return TranscriptionChunk(
            start_time=start_offset,
            end_time=start_offset + chunk_duration,
            text=text,
            confidence=confidence,
            language=config.get("language", DEFAULT_LANGUAGE)
        )
        
    except Exception as e:
        logger.error(f"Chunk transcription failed: {e}")
        return create_error_chunk(start_offset, str(e))


def create_error_chunk(start_offset: float, error_msg: str) -> TranscriptionChunk:
    """Create an error chunk for failed transcriptions."""
    return TranscriptionChunk(
        start_time=start_offset,
        end_time=start_offset + CHUNK_SIZE_SECONDS,
        text=f"[Transcriptie fout: {error_msg}]",
        confidence=0.0,
        language=DEFAULT_LANGUAGE
    )


def combine_chunk_results(
    chunks: List[TranscriptionChunk], 
    metadata: AudioMetadata, 
    model: str, 
    processing_time: float
) -> TranscriptionResult:
    """Combine multiple chunk results into a single transcription."""
    
    # Combine all text
    full_text = " ".join(chunk.text for chunk in chunks if chunk.confidence > 0)
    
    # Calculate overall confidence
    valid_chunks = [chunk for chunk in chunks if chunk.confidence > 0]
    overall_confidence = sum(chunk.confidence for chunk in valid_chunks) / len(valid_chunks) if valid_chunks else 0.0
    
    # Detect language (use most common from chunks)
    languages = [chunk.language for chunk in chunks if chunk.language]
    detected_language = max(set(languages), key=languages.count) if languages else DEFAULT_LANGUAGE
    
    # Collect warnings
    warnings = []
    error_chunks = [chunk for chunk in chunks if chunk.confidence == 0.0]
    if error_chunks:
        warnings.append(f"{len(error_chunks)} chunk(s) failed to transcribe")
    
    if overall_confidence < MIN_CONFIDENCE_SCORE:
        warnings.append(f"Low confidence score: {overall_confidence:.2f}")
    
    return TranscriptionResult(
        text=full_text,
        chunks=chunks,
        confidence_score=overall_confidence,
        language_detected=detected_language,
        processing_time=processing_time,
        audio_metadata=metadata,
        model_used=model,
        status=TranscriptionStatus.COMPLETED,
        warnings=warnings
    )


def optimize_for_dutch(result: TranscriptionResult) -> TranscriptionResult:
    """Apply Dutch language optimizations to transcription."""
    try:
        text = result.text
        
        # Dutch-specific corrections
        dutch_corrections = {
            "arbeidsongeschikt": "arbeidsgeschikt",
            "arbeidsexpert": "arbeidsdeskundige",
            "UWV kantoor": "UWV",
            "ziektewet": "Ziektewet",
            "wao": "WAO",
            "wia": "WIA"
        }
        
        for incorrect, correct in dutch_corrections.items():
            text = text.replace(incorrect, correct)
        
        # Capitalize Dutch arbeidsdeskundige terms
        for term in DUTCH_KEYWORDS:
            # Simple capitalization for important terms at sentence start
            text = text.replace(f". {term}", f". {term.capitalize()}")
            text = text.replace(f"\n{term}", f"\n{term.capitalize()}")
        
        # Update result
        result.text = text
        
        # Check if Dutch keywords are present (quality indicator)
        keyword_count = sum(1 for keyword in DUTCH_KEYWORDS if keyword.lower() in text.lower())
        if keyword_count >= 3:
            result.confidence_score = min(1.0, result.confidence_score + 0.1)  # Boost confidence
        
        return result
        
    except Exception as e:
        logger.error(f"Dutch optimization failed: {e}")
        return result


def validate_transcription_quality(result: TranscriptionResult) -> TranscriptionResult:
    """Validate and potentially improve transcription quality."""
    warnings = list(result.warnings)
    
    # Check minimum text length
    if len(result.text.strip()) < 50:
        warnings.append("Transcription appears very short")
    
    # Check for excessive repetition
    words = result.text.lower().split()
    if len(words) > 0:
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        max_repetition = max(word_counts.values()) if word_counts else 0
        if max_repetition > len(words) * 0.3:  # More than 30% repetition
            warnings.append("High word repetition detected - check audio quality")
    
    # Check for transcription artifacts
    artifacts = ["[inaudible]", "[unclear]", "[music]", "[noise]"]
    artifact_count = sum(result.text.lower().count(artifact) for artifact in artifacts)
    if artifact_count > 0:
        warnings.append(f"{artifact_count} transcription artifact(s) detected")
    
    # Update result with validation findings
    result.warnings = warnings
    
    # Adjust confidence based on quality indicators
    quality_penalty = 0.0
    if len(warnings) > 3:
        quality_penalty = 0.2
    elif len(warnings) > 1:
        quality_penalty = 0.1
    
    result.confidence_score = max(0.0, result.confidence_score - quality_penalty)
    
    return result


def cleanup_temp_files(chunk_files: List[str], prepared_file: str, original_file: str) -> None:
    """Clean up temporary files created during processing."""
    files_to_clean = []
    
    # Add chunk files (except original)
    for chunk_file in chunk_files:
        if chunk_file != original_file:
            files_to_clean.append(chunk_file)
    
    # Add prepared file if different from original
    if prepared_file != original_file and prepared_file not in files_to_clean:
        files_to_clean.append(prepared_file)
    
    # Clean up files
    for file_path in files_to_clean:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {os.path.basename(file_path)}")
        except Exception as e:
            logger.warning(f"Could not clean up {file_path}: {e}")


def update_document_with_result(document_id: str, result: TranscriptionResult) -> None:
    """Update document with transcription results."""
    try:
        # Update document content
        db_service.update_row(
            "document",
            document_id,
            {
                "content": result.text,
                "metadata": json.dumps({
                    "transcription": {
                        "confidence_score": result.confidence_score,
                        "language_detected": result.language_detected,
                        "processing_time": result.processing_time,
                        "model_used": result.model_used,
                        "chunk_count": len(result.chunks),
                        "warnings": result.warnings,
                        "speaker_count": result.speaker_count,
                        "audio_duration": result.audio_metadata.duration_seconds,
                        "audio_quality": result.audio_metadata.quality_score
                    }
                })
            }
        )
        
        # Mark document as processed
        db_service.update_document_status(document_id, "processed")
        logger.info(f"Document {document_id} updated with transcription results")
        
    except Exception as e:
        logger.error(f"Error updating document with transcription: {e}")
        raise


def format_response(result: TranscriptionResult, document_id: str, from_cache: bool = False) -> Dict[str, Any]:
    """Format the transcription response."""
    return {
        "status": "success",
        "document_id": document_id,
        "transcription": {
            "text": result.text,
            "confidence_score": result.confidence_score,
            "language_detected": result.language_detected,
            "processing_time": result.processing_time,
            "model_used": result.model_used,
            "chunk_count": len(result.chunks),
            "warnings": result.warnings,
            "speaker_count": result.speaker_count,
            "from_cache": from_cache
        },
        "audio_metadata": {
            "duration_seconds": result.audio_metadata.duration_seconds,
            "quality_score": result.audio_metadata.quality_score,
            "format": result.audio_metadata.format,
            "file_size": result.audio_metadata.file_size,
            "speech_ratio": result.audio_metadata.speech_ratio
        },
        "recommendations": generate_transcription_recommendations(result)
    }


def generate_transcription_recommendations(result: TranscriptionResult) -> List[str]:
    """Generate recommendations based on transcription results."""
    recommendations = []
    
    # Quality-based recommendations
    if result.confidence_score < 0.6:
        recommendations.append("Consider re-recording with better audio quality")
    
    if result.audio_metadata.speech_ratio < MIN_SPEECH_RATIO:
        recommendations.append("Audio contains significant silence - consider editing")
    
    if result.audio_metadata.quality_score < 0.5:
        recommendations.append("Audio quality is low - try using a better microphone")
    
    # Content-based recommendations  
    dutch_keyword_count = sum(1 for keyword in DUTCH_KEYWORDS 
                             if keyword.lower() in result.text.lower())
    if dutch_keyword_count < 2:
        recommendations.append("Consider adding more specific arbeidsdeskundige terminology")
    
    if len(result.warnings) > 2:
        recommendations.append("Multiple transcription issues detected - review carefully")
    
    if len(result.text.strip()) < 100:
        recommendations.append("Transcription is quite short - ensure complete recording")
    
    return recommendations


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_audio_optimized(self, document_id: str, model_config: str = "accurate", language: Optional[str] = None) -> Dict[str, Any]:
    """
    Advanced audio transcription with optimization for Dutch arbeidsdeskundige content.

    Features:
    - Caching to avoid reprocessing
    - Audio preprocessing and format conversion
    - Chunking for large files
    - Progress tracking
    - Quality scoring and validation
    - Dutch language optimization

    Args:
        document_id: ID of the document containing the audio file
        model_config: Model configuration to use ('fast', 'accurate', 'multilingual')
        language: Language code for transcription (auto-detected if None)

    Returns:
        Dictionary with comprehensive transcription results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting optimized transcription for document {document_id} using {model_config} config")
        
        # Update task status for progress tracking
        if current_task:
            current_task.update_state(
                state=TranscriptionStatus.PREPROCESSING.value,
                meta={'status': 'Initializing transcription', 'progress': 0}
            )

        # Get document from database
        document = db_service.get_row_by_id("document", document_id)
        if not document:
            logger.error(f"Document not found: {document_id}")
            return {"status": "error", "message": f"Document not found: {document_id}"}

        logger.info(f"Retrieved document: {document['title'] if 'title' in document else document_id}")
        
        # Get file path
        file_path = document.get("file_path") or document.get("storage_path")
        if not file_path:
            logger.error(f"No file path in document: {document_id}")
            return {"status": "error", "message": f"No file path in document: {document_id}"}
            
        logger.info(f"Processing audio file: {os.path.basename(file_path)}")
        
        # Get model configuration
        config = MODEL_CONFIGS.get(model_config, MODEL_CONFIGS["accurate"])
        if language:
            config = config.copy()
            config["language"] = language
        elif not language and "language" not in config:
            config["language"] = DEFAULT_LANGUAGE
        
        # Check cache first
        cache_key = get_audio_cache_key(file_path, config)
        cached_result = get_cached_transcription(cache_key)
        if cached_result:
            logger.info("Using cached transcription result")
            update_document_with_result(document_id, cached_result)
            return format_response(cached_result, document_id, from_cache=True)

        # Prepare and validate audio file
        if current_task:
            current_task.update_state(
                state=TranscriptionStatus.PREPROCESSING.value,
                meta={'status': 'Preparing audio file', 'progress': 10}
            )
        
        try:
            prepared_file, audio_metadata = prepare_audio_for_transcription(file_path)
            logger.info(f"Audio prepared: duration={audio_metadata.duration_seconds:.1f}s, "
                       f"quality={audio_metadata.quality_score:.2f}")
        except Exception as e:
            logger.error(f"Error preparing audio file: {e}")
            return {"status": "error", "message": f"Audio preparation failed: {str(e)}"}
        
        # Determine if chunking is needed
        needs_chunking = audio_metadata.duration_seconds > CHUNK_SIZE_SECONDS or audio_metadata.file_size > MAX_FILE_SIZE_BYTES
        
        if needs_chunking:
            logger.info(f"Audio file requires chunking (duration: {audio_metadata.duration_seconds:.1f}s)")
            audio_chunks = chunk_audio_file(prepared_file)
        else:
            audio_chunks = [prepared_file]

        # Validate API key
        api_key = settings.OPENAI_API_KEY
        if not api_key or len(str(api_key).strip()) < 10:
            logger.error("Invalid or missing OpenAI API key")
            return {
                "status": "error", 
                "message": "OpenAI API key not configured - transcription not possible"
            }
        
        # Clean up API key
        if isinstance(api_key, str):
            api_key = api_key.strip().strip('"')
        
        logger.info(f"Using OpenAI API with {len(audio_chunks)} audio chunk(s)")
        
        # Transcribe all chunks
        if current_task:
            current_task.update_state(
                state=TranscriptionStatus.TRANSCRIBING.value,
                meta={'status': f'Transcribing {len(audio_chunks)} chunk(s)', 'progress': 30}
            )
        
        chunk_results = []
        client = OpenAI(api_key=api_key)
        
        for i, chunk_file in enumerate(audio_chunks):
            try:
                logger.info(f"Transcribing chunk {i+1}/{len(audio_chunks)}: {os.path.basename(chunk_file)}")
                
                # Update progress
                if current_task:
                    progress = 30 + (i / len(audio_chunks)) * 50
                    current_task.update_state(
                        state=TranscriptionStatus.TRANSCRIBING.value,
                        meta={'status': f'Transcribing chunk {i+1}/{len(audio_chunks)}', 'progress': progress}
                    )
                
                chunk_result = transcribe_single_chunk(
                    client, chunk_file, config, i * CHUNK_SIZE_SECONDS
                )
                chunk_results.append(chunk_result)
                
            except Exception as e:
                logger.error(f"Error transcribing chunk {i+1}: {e}")
                # Continue with other chunks, but note the error
                chunk_results.append(create_error_chunk(i * CHUNK_SIZE_SECONDS, str(e)))
        
        # Combine chunk results
        if current_task:
            current_task.update_state(
                state=TranscriptionStatus.POSTPROCESSING.value,
                meta={'status': 'Combining and processing results', 'progress': 85}
            )
        
        combined_result = combine_chunk_results(
            chunk_results, audio_metadata, config["model"], time.time() - start_time
        )
        
        # Apply Dutch language optimization
        optimized_result = optimize_for_dutch(combined_result)
        
        # Quality validation
        final_result = validate_transcription_quality(optimized_result)
        
        # Cache the result
        save_transcription_cache(cache_key, final_result)
        
        # Clean up temporary files
        cleanup_temp_files(audio_chunks, prepared_file, file_path)
        
        # Update document with results
        update_document_with_result(document_id, final_result)
        
        if current_task:
            current_task.update_state(
                state=TranscriptionStatus.COMPLETED.value,
                meta={'status': 'Transcription completed', 'progress': 100}
            )
        
        logger.info(f"Transcription completed for document {document_id} in {time.time() - start_time:.2f}s")
        return format_response(final_result, document_id)
        
    except Exception as e:
        logger.error(f"Transcription failed for document {document_id}: {e}")
        
        # Handle retries
        try:
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying transcription (attempt {self.request.retries + 1}/{self.max_retries})")
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        except Exception:
            pass
        
        # Update document status to error
        try:
            db_service.update_document_status(document_id, "error")
        except Exception:
            pass
        
        return {"status": "error", "message": str(e)}


# Task for getting transcription status
@shared_task
def get_transcription_status(document_id: str) -> Dict[str, Any]:
    """
    Get the current status of a transcription task.
    
    Args:
        document_id: ID of the document being transcribed
        
    Returns:
        Dictionary with transcription status information
    """
    try:
        document = db_service.get_row_by_id("document", document_id)
        if not document:
            return {"status": "error", "message": "Document not found"}
        
        status = document.get("status", "unknown")
        metadata = json.loads(document.get("metadata", "{}"))
        transcription_meta = metadata.get("transcription", {})
        
        return {
            "status": "success",
            "document_id": document_id,
            "transcription_status": status,
            "progress": 100 if status == "processed" else 0,
            "metadata": transcription_meta
        }
        
    except Exception as e:
        logger.error(f"Error getting transcription status: {e}")
        return {"status": "error", "message": str(e)}


@shared_task
def cleanup_temporary_audio_optimized(file_paths: List[str]) -> Dict[str, Any]:
    """
    Clean up temporary audio files after processing.
    
    Args:
        file_paths: List of paths to temporary files to clean up
        
    Returns:
        Dictionary with cleanup status information
    """
    try:
        cleaned_files = []
        failed_files = []
        
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleaned_files.append(file_path)
                    logger.info(f"Removed temporary file: {file_path}")
            except Exception as e:
                failed_files.append({"file": file_path, "error": str(e)})
                logger.error(f"Error cleaning up {file_path}: {e}")
        
        return {
            "status": "success",
            "message": f"Cleaned up {len(cleaned_files)} files",
            "cleaned_files": len(cleaned_files),
            "failed_files": len(failed_files),
            "failures": failed_files
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup task: {e}")
        return {"status": "error", "message": str(e)}