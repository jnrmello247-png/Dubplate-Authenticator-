"""
Audio Fingerprinting Module for Dubplate Authentication.

This module provides audio fingerprinting capabilities to uniquely identify
dubplates and compare them against known authentic recordings.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass
class FingerprintResult:
    """Result of an audio fingerprint operation."""
    
    fingerprint_hash: str
    duration: float
    sample_rate: int
    spectral_features: dict
    confidence: float


class AudioFingerprint:
    """
    Audio fingerprinting system for dubplate identification.
    
    Uses spectral analysis and acoustic features to create unique
    fingerprints for audio files that can be used for identification
    and verification.
    """
    
    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        """
        Initialize the AudioFingerprint system.
        
        Args:
            sample_rate: Target sample rate for audio processing
            hop_length: Hop length for spectral analysis
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length
    
    def generate_fingerprint(self, audio_data: np.ndarray, sr: Optional[int] = None) -> FingerprintResult:
        """
        Generate a unique fingerprint for an audio file.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio (uses default if not provided)
            
        Returns:
            FingerprintResult containing the unique fingerprint and metadata
        """
        if sr is None:
            sr = self.sample_rate
            
        # Calculate duration
        duration = len(audio_data) / sr
        
        # Extract spectral features
        spectral_features = self._extract_spectral_features(audio_data, sr)
        
        # Generate hash from features
        fingerprint_hash = self._generate_hash(spectral_features)
        
        return FingerprintResult(
            fingerprint_hash=fingerprint_hash,
            duration=duration,
            sample_rate=sr,
            spectral_features=spectral_features,
            confidence=self._calculate_confidence(spectral_features)
        )
    
    def compare_fingerprints(self, fp1: FingerprintResult, fp2: FingerprintResult) -> float:
        """
        Compare two fingerprints and return similarity score.
        
        Args:
            fp1: First fingerprint
            fp2: Second fingerprint
            
        Returns:
            Similarity score between 0.0 (no match) and 1.0 (exact match)
        """
        if fp1.fingerprint_hash == fp2.fingerprint_hash:
            return 1.0
            
        # Compare spectral features
        similarity = self._compare_spectral_features(
            fp1.spectral_features, 
            fp2.spectral_features
        )
        
        return similarity
    
    def _extract_spectral_features(self, audio_data: np.ndarray, sr: int) -> dict:
        """
        Extract spectral features from audio data.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate
            
        Returns:
            Dictionary of spectral features
        """
        # Calculate basic spectral features using numpy
        # These provide a foundation for fingerprinting
        
        # Compute FFT
        n_fft = min(2048, len(audio_data))
        if len(audio_data) < n_fft:
            audio_data = np.pad(audio_data, (0, n_fft - len(audio_data)))
            
        fft_result = np.fft.rfft(audio_data[:n_fft])
        magnitude = np.abs(fft_result)
        
        # Spectral centroid (center of mass of spectrum)
        freqs = np.fft.rfftfreq(n_fft, 1/sr)
        spectral_centroid = np.sum(magnitude * freqs) / (np.sum(magnitude) + 1e-10)
        
        # Spectral bandwidth
        spectral_bandwidth = np.sqrt(
            np.sum(magnitude * (freqs - spectral_centroid)**2) / (np.sum(magnitude) + 1e-10)
        )
        
        # Spectral rolloff (frequency below which 85% of energy is contained)
        cumsum = np.cumsum(magnitude)
        rolloff_threshold = 0.85 * cumsum[-1]
        rolloff_idx = np.searchsorted(cumsum, rolloff_threshold)
        spectral_rolloff = freqs[min(rolloff_idx, len(freqs) - 1)]
        
        # Zero crossing rate
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / (2 * len(audio_data))
        
        # RMS energy
        rms_energy = np.sqrt(np.mean(audio_data**2))
        
        # Peak frequency
        peak_freq_idx = np.argmax(magnitude)
        peak_frequency = freqs[peak_freq_idx]
        
        return {
            "spectral_centroid": float(spectral_centroid),
            "spectral_bandwidth": float(spectral_bandwidth),
            "spectral_rolloff": float(spectral_rolloff),
            "zero_crossing_rate": float(zero_crossings),
            "rms_energy": float(rms_energy),
            "peak_frequency": float(peak_frequency),
            "magnitude_stats": {
                "mean": float(np.mean(magnitude)),
                "std": float(np.std(magnitude)),
                "max": float(np.max(magnitude))
            }
        }
    
    def _generate_hash(self, features: dict) -> str:
        """
        Generate a unique hash from spectral features.
        
        Args:
            features: Dictionary of spectral features
            
        Returns:
            SHA-256 hash string
        """
        # Create a deterministic string representation of features
        feature_str = "|".join([
            f"{k}:{v}" for k, v in sorted(features.items()) 
            if not isinstance(v, dict)
        ])
        
        # Add nested features
        if "magnitude_stats" in features:
            feature_str += "|" + "|".join([
                f"mag_{k}:{v}" 
                for k, v in sorted(features["magnitude_stats"].items())
            ])
        
        # Generate SHA-256 hash
        return hashlib.sha256(feature_str.encode()).hexdigest()
    
    def _calculate_confidence(self, features: dict) -> float:
        """
        Calculate confidence score for the fingerprint.
        
        Higher confidence indicates more distinctive features.
        
        Args:
            features: Dictionary of spectral features
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence on feature distinctiveness
        confidence = 0.5  # Base confidence
        
        # Higher energy indicates clearer signal
        if features["rms_energy"] > 0.01:
            confidence += 0.1
        if features["rms_energy"] > 0.05:
            confidence += 0.1
            
        # Clear spectral features add confidence
        if features["spectral_centroid"] > 500:
            confidence += 0.1
        if features["spectral_bandwidth"] > 1000:
            confidence += 0.1
            
        # Magnitude statistics
        if features["magnitude_stats"]["std"] > 0:
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    def _compare_spectral_features(self, features1: dict, features2: dict) -> float:
        """
        Compare two sets of spectral features.
        
        Args:
            features1: First set of features
            features2: Second set of features
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Keys to compare (excluding nested dicts)
        compare_keys = [
            "spectral_centroid", "spectral_bandwidth", "spectral_rolloff",
            "zero_crossing_rate", "rms_energy", "peak_frequency"
        ]
        
        similarities = []
        for key in compare_keys:
            if key in features1 and key in features2:
                v1, v2 = features1[key], features2[key]
                if v1 == 0 and v2 == 0:
                    similarities.append(1.0)
                else:
                    # Normalized difference
                    max_val = max(abs(v1), abs(v2), 1e-10)
                    diff = abs(v1 - v2) / max_val
                    similarities.append(max(0, 1 - diff))
        
        return np.mean(similarities) if similarities else 0.0
