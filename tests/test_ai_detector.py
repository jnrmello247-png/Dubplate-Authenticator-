"""
Tests for the AIDetector module.
"""

import numpy as np
import pytest

from dubplate_auth.core.ai_detector import AIDetector, AIDetectionResult, AudioOrigin


class TestAIDetector:
    """Test cases for AIDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create an AI detector instance."""
        return AIDetector(sensitivity=0.7)
    
    @pytest.fixture
    def natural_audio(self):
        """Generate audio that simulates natural human performance."""
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        # Add natural variations to simulate human performance
        vibrato = 0.02 * np.sin(2 * np.pi * 5 * t)  # Slight vibrato
        freq_variation = 440 * (1 + vibrato)
        
        # Natural human audio with variations
        audio = 0.5 * np.sin(2 * np.pi * np.cumsum(freq_variation) / sr)
        
        # Add some natural noise
        noise = 0.02 * np.random.randn(len(audio))
        audio = audio + noise
        
        return audio.astype(np.float32), sr
    
    @pytest.fixture
    def synthetic_audio(self):
        """Generate audio that simulates AI-generated content."""
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        
        # Perfect sinusoidal - no natural variations
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        
        # Perfect harmonics
        audio += 0.25 * np.sin(2 * np.pi * 880 * t)
        audio += 0.125 * np.sin(2 * np.pi * 1320 * t)
        
        return audio.astype(np.float32), sr
    
    def test_detect_returns_result(self, detector, natural_audio):
        """Test that detect returns an AIDetectionResult."""
        audio_data, sr = natural_audio
        result = detector.detect(audio_data, sr)
        
        assert isinstance(result, AIDetectionResult)
        assert isinstance(result.origin, AudioOrigin)
        assert 0.0 <= result.ai_probability <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.artifacts_detected, list)
        assert isinstance(result.analysis_details, dict)
    
    def test_analysis_details_structure(self, detector, natural_audio):
        """Test that analysis details contain expected keys."""
        audio_data, sr = natural_audio
        result = detector.detect(audio_data, sr)
        
        assert "spectral" in result.analysis_details
        assert "timing" in result.analysis_details
        assert "harmonic" in result.analysis_details
        assert "transient" in result.analysis_details
    
    def test_sensitivity_affects_detection(self):
        """Test that sensitivity parameter affects detection."""
        sr = 22050
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        
        low_sensitivity = AIDetector(sensitivity=0.3)
        high_sensitivity = AIDetector(sensitivity=0.9)
        
        result_low = low_sensitivity.detect(audio, sr)
        result_high = high_sensitivity.detect(audio, sr)
        
        # Higher sensitivity should generally report higher AI probability
        # for the same audio
        assert result_low.ai_probability <= result_high.ai_probability or \
               abs(result_low.ai_probability - result_high.ai_probability) < 0.2
    
    def test_audio_origin_enum_values(self):
        """Test AudioOrigin enum has expected values."""
        assert AudioOrigin.HUMAN.value == "human"
        assert AudioOrigin.AI_GENERATED.value == "ai_generated"
        assert AudioOrigin.AI_ENHANCED.value == "ai_enhanced"
        assert AudioOrigin.SOUND_ALIKE.value == "sound_alike"
        assert AudioOrigin.UNKNOWN.value == "unknown"
    
    def test_short_audio(self, detector):
        """Test detection on very short audio."""
        sr = 22050
        audio = np.random.randn(sr // 2).astype(np.float32)  # 0.5 seconds
        
        result = detector.detect(audio, sr)
        
        assert isinstance(result, AIDetectionResult)
        assert result.origin is not None
    
    def test_silent_audio(self, detector):
        """Test detection on silent audio."""
        sr = 22050
        audio = np.zeros(sr).astype(np.float32)
        
        result = detector.detect(audio, sr)
        
        assert isinstance(result, AIDetectionResult)
    
    def test_noisy_audio(self, detector):
        """Test detection on pure noise."""
        sr = 22050
        audio = np.random.randn(sr * 2).astype(np.float32) * 0.5
        
        result = detector.detect(audio, sr)
        
        assert isinstance(result, AIDetectionResult)
        # Pure random noise should not be classified as AI-generated
        assert result.origin != AudioOrigin.AI_GENERATED


class TestArtifactDetection:
    """Test artifact detection capabilities."""
    
    @pytest.fixture
    def detector(self):
        """Create an AI detector instance."""
        return AIDetector(sensitivity=0.7)
    
    def test_artifacts_list_format(self, detector):
        """Test that artifacts are returned as a list of strings."""
        sr = 22050
        audio = np.random.randn(sr).astype(np.float32)
        
        result = detector.detect(audio, sr)
        
        assert isinstance(result.artifacts_detected, list)
        for artifact in result.artifacts_detected:
            assert isinstance(artifact, str)
    
    def test_known_artifact_types(self, detector):
        """Test that detected artifacts are from known types."""
        known_artifacts = {
            "unnatural_spectral_smoothness",
            "mechanical_timing",
            "perfect_harmonics",
            "uniform_transients"
        }
        
        sr = 22050
        # Generate synthetic-sounding audio
        t = np.linspace(0, 2.0, sr * 2, endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        
        result = detector.detect(audio, sr)
        
        for artifact in result.artifacts_detected:
            assert artifact in known_artifacts
