"""
Tests for the main DubplateAuthenticator module.
"""

import numpy as np
import pytest

from dubplate_auth.core.authenticator import (
    DubplateAuthenticator,
    AuthenticationResult,
    AuthenticationStatus,
    VerificationResult
)
from dubplate_auth.core.ai_detector import AudioOrigin


class TestDubplateAuthenticator:
    """Test cases for DubplateAuthenticator class."""
    
    @pytest.fixture
    def authenticator(self):
        """Create an authenticator instance."""
        return DubplateAuthenticator(
            secret_key="test_secret",
            ai_sensitivity=0.7
        )
    
    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio for testing."""
        sr = 22050
        duration = 3.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        # Create audio with some complexity
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio += 0.3 * np.sin(2 * np.pi * 880 * t)
        audio += 0.1 * np.random.randn(len(audio))  # Add some noise
        
        return audio.astype(np.float32), sr
    
    def test_authenticate(self, authenticator, sample_audio):
        """Test basic authentication."""
        audio_data, sr = sample_audio
        result = authenticator.authenticate(audio_data, sr)
        
        assert isinstance(result, AuthenticationResult)
        assert isinstance(result.status, AuthenticationStatus)
        assert 0.0 <= result.confidence <= 1.0
        assert result.fingerprint is not None
        assert result.ai_detection is not None
        assert result.timestamp is not None
    
    def test_authenticate_with_artist_id(self, authenticator, sample_audio):
        """Test authentication with expected artist ID."""
        audio_data, sr = sample_audio
        result = authenticator.authenticate(
            audio_data, sr, 
            expected_artist_id="artist_001"
        )
        
        assert isinstance(result, AuthenticationResult)
        assert "artist_verified" in result.details
    
    def test_verify_legacy_no_reference(self, authenticator, sample_audio):
        """Test legacy verification with no registered references."""
        audio_data, sr = sample_audio
        result = authenticator.verify_legacy(audio_data, sr)
        
        assert isinstance(result, VerificationResult)
        assert not result.verified  # No references registered
        assert result.match_score == 0.0
    
    def test_register_and_verify_reference(self, authenticator, sample_audio):
        """Test registering and verifying against a reference."""
        audio_data, sr = sample_audio
        
        # Register reference
        success = authenticator.register_reference(
            audio_data, sr, "ref_001", {"title": "Test Dub"}
        )
        assert success
        
        # Verify against reference
        result = authenticator.verify_legacy(audio_data, sr, "ref_001")
        
        assert result.match_score > 0.9  # Same audio should match highly
    
    def test_watermark_new(self, authenticator, sample_audio):
        """Test watermarking new dubplate."""
        audio_data, sr = sample_audio
        
        result = authenticator.watermark_new(
            audio_data=audio_data,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist"
        )
        
        assert result.success
        assert result.watermark_info is not None
        assert result.audio_data is not None
    
    def test_get_fingerprint(self, authenticator, sample_audio):
        """Test getting audio fingerprint."""
        audio_data, sr = sample_audio
        fp = authenticator.get_fingerprint(audio_data, sr)
        
        assert fp.fingerprint_hash is not None
        assert fp.duration > 0
    
    def test_compare_audio_same(self, authenticator, sample_audio):
        """Test comparing same audio."""
        audio_data, sr = sample_audio
        
        similarity = authenticator.compare_audio(audio_data, audio_data, sr)
        
        assert similarity == 1.0
    
    def test_compare_audio_different(self, authenticator):
        """Test comparing different audio."""
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        audio1 = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio2 = 0.5 * np.sin(2 * np.pi * 880 * t)
        
        similarity = authenticator.compare_audio(audio1, audio2, sr)
        
        assert similarity < 1.0


class TestAuthenticationStatus:
    """Test AuthenticationStatus enum."""
    
    def test_enum_values(self):
        """Test that all expected status values exist."""
        assert AuthenticationStatus.AUTHENTIC.value == "authentic"
        assert AuthenticationStatus.LIKELY_AUTHENTIC.value == "likely_authentic"
        assert AuthenticationStatus.SUSPICIOUS.value == "suspicious"
        assert AuthenticationStatus.AI_GENERATED.value == "ai_generated"
        assert AuthenticationStatus.SOUND_ALIKE.value == "sound_alike"
        assert AuthenticationStatus.UNVERIFIED.value == "unverified"
        assert AuthenticationStatus.LEGACY_VERIFIED.value == "legacy_verified"
        assert AuthenticationStatus.LEGACY_UNVERIFIED.value == "legacy_unverified"


class TestIntegration:
    """Integration tests for the full authentication workflow."""
    
    @pytest.fixture
    def authenticator(self):
        """Create an authenticator instance."""
        return DubplateAuthenticator(secret_key="integration_test_key")
    
    def test_full_workflow(self, authenticator):
        """Test the full dubplate authentication workflow."""
        sr = 22050
        duration = 5.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        # Create original dubplate audio
        original_audio = (
            0.5 * np.sin(2 * np.pi * 440 * t) +
            0.3 * np.sin(2 * np.pi * 880 * t) +
            0.1 * np.random.randn(len(t))
        ).astype(np.float32)
        
        # Step 1: Watermark the new dubplate
        watermark_result = authenticator.watermark_new(
            audio_data=original_audio,
            sr=sr,
            artist_id="test_artist_001",
            artist_name="Integration Test Artist",
            metadata={"sound_system": "Test Sound", "year": 2024}
        )
        
        assert watermark_result.success
        watermarked_audio = watermark_result.audio_data
        
        # Step 2: Get fingerprint of the watermarked audio
        fingerprint = authenticator.get_fingerprint(watermarked_audio, sr)
        assert fingerprint.fingerprint_hash is not None
        
        # Step 3: Register as reference for future verification
        authenticator.register_reference(
            watermarked_audio, sr, "ref_integration_test"
        )
        
        # Step 4: Authenticate the watermarked audio
        auth_result = authenticator.authenticate(
            watermarked_audio, sr, 
            expected_artist_id="test_artist_001"
        )
        
        assert auth_result.status in [
            AuthenticationStatus.AUTHENTIC,
            AuthenticationStatus.LIKELY_AUTHENTIC,
            AuthenticationStatus.UNVERIFIED
        ]
        
        # Step 5: Verify as legacy dubplate
        verify_result = authenticator.verify_legacy(
            watermarked_audio, sr, "ref_integration_test"
        )
        
        assert verify_result.match_score > 0.9
