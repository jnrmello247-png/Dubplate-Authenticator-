"""
Tests for the AudioFingerprint module.
"""

import numpy as np
import pytest

from dubplate_auth.core.fingerprint import AudioFingerprint, FingerprintResult


class TestAudioFingerprint:
    """Test cases for AudioFingerprint class."""
    
    @pytest.fixture
    def fingerprinter(self):
        """Create a fingerprinter instance."""
        return AudioFingerprint()
    
    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio data."""
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        # Create a simple test signal with multiple frequencies
        audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 880 * t)
        return audio.astype(np.float32), sr
    
    def test_generate_fingerprint(self, fingerprinter, sample_audio):
        """Test fingerprint generation."""
        audio_data, sr = sample_audio
        result = fingerprinter.generate_fingerprint(audio_data, sr)
        
        assert isinstance(result, FingerprintResult)
        assert result.fingerprint_hash is not None
        assert len(result.fingerprint_hash) == 64  # SHA-256 hash length
        assert result.duration == pytest.approx(2.0, rel=0.01)
        assert result.sample_rate == sr
        assert 0.0 <= result.confidence <= 1.0
    
    def test_fingerprint_consistency(self, fingerprinter, sample_audio):
        """Test that the same audio produces the same fingerprint."""
        audio_data, sr = sample_audio
        
        fp1 = fingerprinter.generate_fingerprint(audio_data, sr)
        fp2 = fingerprinter.generate_fingerprint(audio_data, sr)
        
        assert fp1.fingerprint_hash == fp2.fingerprint_hash
    
    def test_different_audio_different_fingerprint(self, fingerprinter):
        """Test that different audio produces different fingerprints."""
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        audio1 = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio2 = 0.5 * np.sin(2 * np.pi * 880 * t)
        
        fp1 = fingerprinter.generate_fingerprint(audio1, sr)
        fp2 = fingerprinter.generate_fingerprint(audio2, sr)
        
        assert fp1.fingerprint_hash != fp2.fingerprint_hash
    
    def test_compare_fingerprints_same_audio(self, fingerprinter, sample_audio):
        """Test comparing fingerprints of the same audio."""
        audio_data, sr = sample_audio
        
        fp1 = fingerprinter.generate_fingerprint(audio_data, sr)
        fp2 = fingerprinter.generate_fingerprint(audio_data, sr)
        
        similarity = fingerprinter.compare_fingerprints(fp1, fp2)
        assert similarity == 1.0
    
    def test_compare_fingerprints_different_audio(self, fingerprinter):
        """Test comparing fingerprints of different audio."""
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        audio1 = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio2 = 0.5 * np.sin(2 * np.pi * 880 * t)
        
        fp1 = fingerprinter.generate_fingerprint(audio1, sr)
        fp2 = fingerprinter.generate_fingerprint(audio2, sr)
        
        similarity = fingerprinter.compare_fingerprints(fp1, fp2)
        assert 0.0 <= similarity < 1.0
    
    def test_spectral_features_extracted(self, fingerprinter, sample_audio):
        """Test that spectral features are properly extracted."""
        audio_data, sr = sample_audio
        result = fingerprinter.generate_fingerprint(audio_data, sr)
        
        features = result.spectral_features
        
        assert "spectral_centroid" in features
        assert "spectral_bandwidth" in features
        assert "spectral_rolloff" in features
        assert "zero_crossing_rate" in features
        assert "rms_energy" in features
        assert "peak_frequency" in features
        assert "magnitude_stats" in features
    
    def test_short_audio(self, fingerprinter):
        """Test fingerprinting very short audio."""
        sr = 22050
        audio = np.random.randn(1000).astype(np.float32)
        
        result = fingerprinter.generate_fingerprint(audio, sr)
        
        assert result.fingerprint_hash is not None
        assert result.duration < 0.1
    
    def test_silence_audio(self, fingerprinter):
        """Test fingerprinting silent audio."""
        sr = 22050
        audio = np.zeros(sr).astype(np.float32)
        
        result = fingerprinter.generate_fingerprint(audio, sr)
        
        assert result.fingerprint_hash is not None
        assert result.confidence < 0.7  # Low confidence for silent audio
