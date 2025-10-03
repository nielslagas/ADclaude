"""
Unit tests for Audio API endpoints.
Tests audio upload, transcription, and processing functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from uuid import uuid4
from datetime import datetime
import io
import wave
import struct

from fastapi import status
from httpx import AsyncClient


@pytest.fixture
def mock_audio_file():
    """Create a mock WAV audio file."""
    # Create a simple WAV file in memory
    buffer = io.BytesIO()
    
    # Write WAV header
    buffer.write(b'RIFF')
    buffer.write(struct.pack('<I', 36))  # File size - 8
    buffer.write(b'WAVE')
    buffer.write(b'fmt ')
    buffer.write(struct.pack('<I', 16))  # Subchunk size
    buffer.write(struct.pack('<H', 1))   # Audio format (PCM)
    buffer.write(struct.pack('<H', 1))   # Number of channels
    buffer.write(struct.pack('<I', 44100))  # Sample rate
    buffer.write(struct.pack('<I', 88200))  # Byte rate
    buffer.write(struct.pack('<H', 2))   # Block align
    buffer.write(struct.pack('<H', 16))  # Bits per sample
    buffer.write(b'data')
    buffer.write(struct.pack('<I', 0))   # Data chunk size
    
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def mock_audio_data():
    return {
        "id": str(uuid4()),
        "case_id": str(uuid4()),
        "user_id": "test_user",
        "filename": "test_audio.wav",
        "storage_path": "/test/storage/audio/test_audio.wav",
        "mimetype": "audio/wav",
        "size": 44100,
        "duration": 10.5,
        "status": "uploaded",
        "transcription": None,
        "metadata": {
            "sample_rate": 44100,
            "channels": 1,
            "bitrate": 16
        },
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.audio
class TestAudioAPI:
    """Test cases for Audio API endpoints."""
    
    async def test_upload_audio_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_celery_task, mock_audio_file):
        """Test successful audio upload."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.audio.celery') as mock_celery, \
             patch('builtins.open', mock_open()) as mock_file:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="audio_task_123")
            
            files = {"file": ("recording.wav", mock_audio_file, "audio/wav")}
            data = {"case_id": case_id, "title": "Patient interview"}
            
            response = await async_client.post(
                "/api/v1/audio/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            result = response.json()
            assert "id" in result
            assert result["filename"] == "recording.wav"
            assert result["status"] == "uploaded"
    
    
    async def test_upload_audio_case_not_found(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_file):
        """Test audio upload with non-existent case."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = None
            
            files = {"file": ("recording.wav", mock_audio_file, "audio/wav")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/audio/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Case not found" in response.json()["detail"]
    
    
    async def test_upload_audio_invalid_format(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test upload of unsupported audio format."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            
            # Upload unsupported audio format
            invalid_audio = b"Invalid audio data"
            files = {"file": ("audio.xyz", invalid_audio, "audio/xyz")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/audio/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Unsupported audio format" in response.json()["detail"]
    
    
    async def test_get_audio_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data):
        """Test successful audio retrieval."""
        audio_id = mock_audio_data["id"]
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = mock_audio_data
            
            response = await async_client.get(
                f"/api/v1/audio/{audio_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["id"] == audio_id
            assert result["filename"] == "test_audio.wav"
            assert result["duration"] == 10.5
    
    
    async def test_get_audio_not_found(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test retrieval of non-existent audio file."""
        audio_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = None
            
            response = await async_client.get(
                f"/api/v1/audio/{audio_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    
    async def test_transcribe_audio_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data, mock_celery_task):
        """Test successful audio transcription."""
        audio_id = mock_audio_data["id"]
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.audio.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = mock_audio_data
            mock_celery.send_task.return_value = Mock(id="transcribe_task_123")
            
            response = await async_client.post(
                f"/api/v1/audio/{audio_id}/transcribe",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            result = response.json()
            assert "task_id" in result
            assert result["status"] == "transcribing"
    
    
    async def test_get_transcription_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data):
        """Test successful transcription retrieval."""
        audio_id = mock_audio_data["id"]
        transcription_text = "Dit is de transcriptie van het audio bestand met medische informatie."
        
        # Mock audio data with transcription
        audio_with_transcription = {
            **mock_audio_data,
            "transcription": transcription_text,
            "status": "transcribed"
        }
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = audio_with_transcription
            
            response = await async_client.get(
                f"/api/v1/audio/{audio_id}/transcription",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["transcription"] == transcription_text
            assert result["status"] == "transcribed"
    
    
    async def test_get_transcription_not_ready(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data):
        """Test transcription retrieval when not yet available."""
        audio_id = mock_audio_data["id"]
        
        # Audio without transcription
        audio_processing = {
            **mock_audio_data,
            "status": "transcribing",
            "transcription": None
        }
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = audio_processing
            
            response = await async_client.get(
                f"/api/v1/audio/{audio_id}/transcription",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
            result = response.json()
            assert result["status"] == "transcribing"
            assert "transcription" not in result or result["transcription"] is None
    
    
    async def test_get_case_audio_files(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data):
        """Test retrieval of audio files by case ID."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case_audio_files.return_value = [mock_audio_data]
            
            response = await async_client.get(
                f"/api/v1/audio/case/{case_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert len(result) == 1
            assert result[0]["id"] == mock_audio_data["id"]
    
    
    async def test_delete_audio_success(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data):
        """Test successful audio deletion."""
        audio_id = mock_audio_data["id"]
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('os.remove') as mock_remove:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = mock_audio_data
            mock_db_service.delete_audio_file.return_value = True
            
            response = await async_client.delete(
                f"/api/v1/audio/{audio_id}",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_204_NO_CONTENT
            mock_remove.assert_called_once()  # File should be deleted from storage
    
    
    async def test_update_transcription(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_data):
        """Test manual transcription update."""
        audio_id = mock_audio_data["id"]
        new_transcription = "Gecorrigeerde transcriptie van het gesprek."
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = mock_audio_data
            mock_db_service.update_audio_transcription.return_value = {
                **mock_audio_data,
                "transcription": new_transcription,
                "status": "transcribed"
            }
            
            update_data = {"transcription": new_transcription}
            
            response = await async_client.put(
                f"/api/v1/audio/{audio_id}/transcription",
                headers=auth_headers,
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert result["transcription"] == new_transcription
            assert result["status"] == "transcribed"
    
    
    @pytest.mark.parametrize("audio_format,mimetype,should_succeed", [
        ("wav", "audio/wav", True),
        ("mp3", "audio/mpeg", True),
        ("m4a", "audio/mp4", True),
        ("flac", "audio/flac", True),
        ("ogg", "audio/ogg", True),
        ("mp4", "video/mp4", False),  # Video format
        ("txt", "text/plain", False),  # Text format
        ("exe", "application/octet-stream", False)  # Executable
    ])
    async def test_audio_format_validation(self, async_client: AsyncClient, auth_headers, mock_db_service,
                                          audio_format, mimetype, should_succeed):
        """Test audio format validation for various formats."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.audio.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="format_task")
            
            audio_content = b"Mock audio content"
            filename = f"test.{audio_format}"
            files = {"file": (filename, audio_content, mimetype)}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/audio/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            if should_succeed:
                assert response.status_code == status.HTTP_201_CREATED
            else:
                assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    
    async def test_large_audio_file_handling(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test handling of large audio files."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            
            # Create a large audio file (100MB simulated)
            large_audio = b"x" * (100 * 1024 * 1024)  # 100MB
            files = {"file": ("large_audio.wav", large_audio, "audio/wav")}
            data = {"case_id": case_id}
            
            response = await async_client.post(
                "/api/v1/audio/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            # Should reject files that are too large
            assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    
    
    async def test_whisper_integration(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test Whisper transcription integration."""
        audio_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('app.tasks.process_audio_tasks.audio_transcriber.transcribe_audio') as mock_whisper:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_audio = {
                "id": audio_id,
                "user_id": "test_user",
                "storage_path": "/path/to/audio.wav",
                "status": "uploaded"
            }
            mock_db_service.get_audio_file.return_value = mock_audio
            
            # Mock Whisper transcription result
            mock_whisper.return_value = {
                "text": "Dit is een medisch consult met de patiënt over rugklachten.",
                "language": "dutch",
                "confidence": 0.95,
                "segments": [
                    {"start": 0.0, "end": 3.5, "text": "Dit is een medisch consult"},
                    {"start": 3.5, "end": 7.0, "text": "met de patiënt over rugklachten."}
                ]
            }
            
            response = await async_client.post(
                f"/api/v1/audio/{audio_id}/transcribe",
                headers=auth_headers,
                json={"provider": "whisper", "language": "nl"}
            )
            
            assert response.status_code == status.HTTP_202_ACCEPTED
    
    
    async def test_audio_metadata_extraction(self, async_client: AsyncClient, auth_headers, mock_db_service, mock_audio_file):
        """Test extraction of audio metadata."""
        case_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.audio.celery') as mock_celery, \
             patch('builtins.open', mock_open()):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_case.return_value = {"id": case_id, "user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="metadata_task")
            
            # Mock audio file creation with metadata
            def mock_create_audio(*args, **kwargs):
                return {
                    "id": str(uuid4()),
                    "filename": kwargs.get("filename", "test.wav"),
                    "duration": 15.3,
                    "metadata": {
                        "sample_rate": 44100,
                        "channels": 2,
                        "bitrate": 320,
                        "format": "WAV",
                        "quality": "high"
                    }
                }
            
            mock_db_service.create_audio_file.side_effect = mock_create_audio
            
            files = {"file": ("interview.wav", mock_audio_file, "audio/wav")}
            data = {"case_id": case_id, "title": "Patient Interview"}
            
            response = await async_client.post(
                "/api/v1/audio/upload",
                headers={"Authorization": auth_headers["Authorization"]},
                files=files,
                data=data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            result = response.json()
            assert "metadata" in result
            assert result["metadata"]["sample_rate"] == 44100
            assert result["duration"] == 15.3
    
    
    @pytest.mark.performance
    async def test_concurrent_transcriptions(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test performance with concurrent transcription requests."""
        audio_ids = [str(uuid4()) for _ in range(3)]
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service), \
             patch('app.api.v1.endpoints.audio.celery') as mock_celery:
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_celery.send_task.return_value = Mock(id="concurrent_transcribe")
            
            # Mock audio files for each ID
            def mock_get_audio(audio_id, user_id):
                return {
                    "id": audio_id,
                    "user_id": user_id,
                    "status": "uploaded",
                    "storage_path": f"/path/to/{audio_id}.wav"
                }
            
            mock_db_service.get_audio_file.side_effect = mock_get_audio
            
            import asyncio
            import time
            
            async def transcribe_audio(audio_id):
                return await async_client.post(
                    f"/api/v1/audio/{audio_id}/transcribe",
                    headers=auth_headers
                )
            
            start_time = time.time()
            tasks = [transcribe_audio(audio_id) for audio_id in audio_ids]
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # All transcription requests should succeed
            for response in responses:
                assert response.status_code == status.HTTP_202_ACCEPTED
            
            # Should handle concurrent requests efficiently
            total_time = end_time - start_time
            assert total_time < 3.0  # Should complete within 3 seconds
    
    
    async def test_transcription_quality_validation(self, async_client: AsyncClient, auth_headers, mock_db_service):
        """Test transcription quality validation and correction."""
        audio_id = str(uuid4())
        
        with patch('app.api.v1.endpoints.audio.verify_token') as mock_auth, \
             patch('app.api.v1.endpoints.audio.db_service', mock_db_service):
            
            mock_auth.return_value = {"user_id": "test_user"}
            mock_db_service.get_audio_file.return_value = {
                "id": audio_id,
                "user_id": "test_user",
                "transcription": "Patient heeft pijn in de rog",  # Intentional typo
                "confidence": 0.85
            }
            
            # Test quality check endpoint
            response = await async_client.post(
                f"/api/v1/audio/{audio_id}/quality-check",
                headers=auth_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            result = response.json()
            assert "quality_score" in result
            assert "suggestions" in result
            # Should detect the typo "rog" -> "rug"
            assert any("rog" in suggestion.lower() for suggestion in result.get("suggestions", []))