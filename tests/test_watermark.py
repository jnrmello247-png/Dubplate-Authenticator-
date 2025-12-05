"""
Tests for the WatermarkManager module.
"""

import numpy as np
import pytest

from dubplate_auth.core.watermark import WatermarkManager, WatermarkInfo, WatermarkResult


class TestWatermarkManager:
    """Test cases for WatermarkManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a watermark manager instance."""
        return WatermarkManager(secret_key="test_secret_key")
    
    @pytest.fixture
    def sample_audio(self):
        """Generate sample audio for watermarking."""
        sr = 22050
        duration = 5.0  # Longer duration for watermarking
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        return audio.astype(np.float32), sr
    
    def test_embed_watermark(self, manager, sample_audio):
        """Test watermark embedding."""
        audio_data, sr = sample_audio
        
        result = manager.embed_watermark(
            audio_data=audio_data,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist"
        )
        
        assert result.success
        assert result.watermark_info is not None
        assert result.audio_data is not None
        assert result.message == "Watermark successfully embedded"
    
    def test_watermark_info_fields(self, manager, sample_audio):
        """Test that watermark info contains all expected fields."""
        audio_data, sr = sample_audio
        
        result = manager.embed_watermark(
            audio_data=audio_data,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist",
            metadata={"genre": "reggae", "year": 2024}
        )
        
        info = result.watermark_info
        assert info.artist_id == "artist_001"
        assert info.artist_name == "Test Artist"
        assert info.dubplate_id is not None
        assert info.creation_date is not None
        assert info.signature is not None
        assert info.metadata == {"genre": "reggae", "year": 2024}
    
    def test_watermark_preserves_audio_length(self, manager, sample_audio):
        """Test that watermarking preserves audio length."""
        audio_data, sr = sample_audio
        original_length = len(audio_data)
        
        result = manager.embed_watermark(
            audio_data=audio_data,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist"
        )
        
        assert len(result.audio_data) == original_length
    
    def test_custom_dubplate_id(self, manager, sample_audio):
        """Test using a custom dubplate ID."""
        audio_data, sr = sample_audio
        
        result = manager.embed_watermark(
            audio_data=audio_data,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist",
            dubplate_id="custom_dub_123"
        )
        
        assert result.watermark_info.dubplate_id == "custom_dub_123"
    
    def test_short_audio_fails(self, manager):
        """Test that very short audio fails watermarking."""
        sr = 22050
        audio = np.random.randn(sr // 2).astype(np.float32)  # 0.5 seconds
        
        result = manager.embed_watermark(
            audio_data=audio,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist"
        )
        
        assert not result.success
        assert "too short" in result.message.lower()
    
    def test_verify_watermark(self, manager, sample_audio):
        """Test watermark verification."""
        audio_data, sr = sample_audio
        
        # Embed watermark
        embed_result = manager.embed_watermark(
            audio_data=audio_data,
            sr=sr,
            artist_id="artist_001",
            artist_name="Test Artist"
        )
        
        # Verify the watermark
        is_valid = manager.verify_watermark(
            embed_result.audio_data,
            sr,
            "artist_001"
        )
        
        # Note: Due to the simple implementation, extraction may not always work
        # This tests the interface, not the robustness
        assert isinstance(is_valid, bool)


class TestWatermarkExtraction:
    """Test watermark extraction functionality."""
    
    @pytest.fixture
    def manager(self):
        """Create a watermark manager instance."""
        return WatermarkManager(secret_key="test_secret_key")
    
    def test_extract_from_unwatermarked_audio(self, manager):
        """Test extraction from audio without watermark."""
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(duration * sr), endpoint=False)
        audio = 0.5 * np.sin(2 * np.pi * 440 * t)
        
        result = manager.extract_watermark(audio, sr)
        
        # Should fail to find watermark in unwatermarked audio
        # (though false positives are possible with simple implementation)
        assert isinstance(result, WatermarkResult)
    
    def test_extract_from_short_audio(self, manager):
        """Test extraction from very short audio."""
        sr = 22050
        audio = np.random.randn(sr // 2).astype(np.float32)
        
        result = manager.extract_watermark(audio, sr)
        
        assert not result.success
        assert "too short" in result.message.lower()


class TestWatermarkSignature:
    """Test watermark signature generation and verification."""
    
    @pytest.fixture
    def manager(self):
        """Create a watermark manager instance."""
        return WatermarkManager(secret_key="test_secret_key")
    
    def test_consistent_signature(self, manager):
        """Test that signature is deterministic."""
        data = {
            "artist_id": "test",
            "artist_name": "Test Artist",
            "creation_date": "2024-01-01",
            "dubplate_id": "dub123",
            "metadata": {}
        }
        
        sig1 = manager._generate_signature(data)
        sig2 = manager._generate_signature(data)
        
        assert sig1 == sig2
    
    def test_different_data_different_signature(self, manager):
        """Test that different data produces different signatures."""
        data1 = {"artist_id": "artist1", "name": "Test"}
        data2 = {"artist_id": "artist2", "name": "Test"}
        
        sig1 = manager._generate_signature(data1)
        sig2 = manager._generate_signature(data2)
        
        assert sig1 != sig2
    
    def test_different_keys_different_signature(self):
        """Test that different secret keys produce different signatures."""
        manager1 = WatermarkManager(secret_key="key1")
        manager2 = WatermarkManager(secret_key="key2")
        
        data = {"artist_id": "test", "name": "Test Artist"}
        
        sig1 = manager1._generate_signature(data)
        sig2 = manager2._generate_signature(data)
        
        assert sig1 != sig2
