"""
Main Dubplate Authenticator Module.

This module provides the main interface for dubplate authentication,
combining fingerprinting, AI detection, and watermarking capabilities.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import numpy as np

from dubplate_auth.core.ai_detector import AIDetector, AIDetectionResult, AudioOrigin
from dubplate_auth.core.fingerprint import AudioFingerprint, FingerprintResult
from dubplate_auth.core.watermark import WatermarkManager, WatermarkInfo, WatermarkResult


class AuthenticationStatus(Enum):
    """Status of dubplate authentication."""
    
    AUTHENTIC = "authentic"
    LIKELY_AUTHENTIC = "likely_authentic"
    SUSPICIOUS = "suspicious"
    AI_GENERATED = "ai_generated"
    SOUND_ALIKE = "sound_alike"
    UNVERIFIED = "unverified"
    LEGACY_VERIFIED = "legacy_verified"
    LEGACY_UNVERIFIED = "legacy_unverified"


@dataclass
class AuthenticationResult:
    """Complete result of dubplate authentication."""
    
    status: AuthenticationStatus
    confidence: float
    fingerprint: FingerprintResult
    ai_detection: AIDetectionResult
    watermark: Optional[WatermarkInfo]
    timestamp: str
    details: dict


@dataclass
class VerificationResult:
    """Result of legacy dubplate verification."""
    
    verified: bool
    confidence: float
    match_score: float
    reference_fingerprint: Optional[str]
    details: dict


class DubplateAuthenticator:
    """
    Main authenticator class for dubplate verification.
    
    Provides comprehensive dubplate authentication combining:
    - Audio fingerprinting for identification
    - AI detection to identify synthetic content
    - Watermark verification for artist authentication
    - Legacy dubplate verification against reference database
    """
    
    def __init__(
        self,
        secret_key: str = "dubplate_auth_secret",
        ai_sensitivity: float = 0.7
    ):
        """
        Initialize the DubplateAuthenticator.
        
        Args:
            secret_key: Secret key for watermark operations
            ai_sensitivity: Sensitivity for AI detection (0.0-1.0)
        """
        self.fingerprinter = AudioFingerprint()
        self.ai_detector = AIDetector(sensitivity=ai_sensitivity)
        self.watermark_manager = WatermarkManager(secret_key=secret_key)
        
        # Reference database for legacy verification (in-memory for now)
        self._reference_fingerprints: dict = {}
    
    def authenticate(
        self,
        audio_data: np.ndarray,
        sr: int = 22050,
        expected_artist_id: Optional[str] = None
    ) -> AuthenticationResult:
        """
        Perform full authentication on audio.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            expected_artist_id: If provided, verify watermark matches this artist
            
        Returns:
            AuthenticationResult with comprehensive analysis
        """
        # Generate fingerprint
        fingerprint = self.fingerprinter.generate_fingerprint(audio_data, sr)
        
        # Perform AI detection
        ai_detection = self.ai_detector.detect(audio_data, sr)
        
        # Try to extract watermark
        watermark_result = self.watermark_manager.extract_watermark(audio_data, sr)
        watermark_info = watermark_result.watermark_info if watermark_result.success else None
        
        # Determine authentication status
        status, confidence = self._determine_status(
            ai_detection,
            watermark_info,
            expected_artist_id
        )
        
        details = {
            "ai_probability": ai_detection.ai_probability,
            "ai_artifacts": ai_detection.artifacts_detected,
            "fingerprint_confidence": fingerprint.confidence,
            "watermark_found": watermark_result.success,
            "artist_verified": (
                watermark_info is not None and
                expected_artist_id is not None and
                watermark_info.artist_id == expected_artist_id
            )
        }
        
        return AuthenticationResult(
            status=status,
            confidence=confidence,
            fingerprint=fingerprint,
            ai_detection=ai_detection,
            watermark=watermark_info,
            timestamp=datetime.now(timezone.utc).isoformat(),
            details=details
        )
    
    def verify_legacy(
        self,
        audio_data: np.ndarray,
        sr: int = 22050,
        reference_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify a legacy dubplate against reference database.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            reference_id: Specific reference to verify against
            
        Returns:
            VerificationResult indicating verification status
        """
        # Generate fingerprint for the audio
        fingerprint = self.fingerprinter.generate_fingerprint(audio_data, sr)
        
        # Perform AI detection (legacy dubplates shouldn't be AI-generated)
        ai_detection = self.ai_detector.detect(audio_data, sr)
        
        best_match_score = 0.0
        best_match_id = None
        
        if reference_id:
            # Verify against specific reference
            if reference_id in self._reference_fingerprints:
                ref_fp = self._reference_fingerprints[reference_id]
                match_score = self.fingerprinter.compare_fingerprints(fingerprint, ref_fp)
                best_match_score = match_score
                best_match_id = reference_id
        else:
            # Search all references for best match
            for ref_id, ref_fp in self._reference_fingerprints.items():
                match_score = self.fingerprinter.compare_fingerprints(fingerprint, ref_fp)
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_match_id = ref_id
        
        # Determine if verified
        verified = best_match_score > 0.85 and ai_detection.ai_probability < 0.5
        
        # Calculate confidence
        confidence = self._calculate_verification_confidence(
            best_match_score,
            ai_detection.ai_probability,
            fingerprint.confidence
        )
        
        details = {
            "fingerprint_hash": fingerprint.fingerprint_hash,
            "ai_probability": ai_detection.ai_probability,
            "reference_searched": len(self._reference_fingerprints),
            "threshold_match": 0.85
        }
        
        return VerificationResult(
            verified=verified,
            confidence=confidence,
            match_score=best_match_score,
            reference_fingerprint=best_match_id,
            details=details
        )
    
    def register_reference(
        self,
        audio_data: np.ndarray,
        sr: int,
        reference_id: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Register a reference fingerprint for legacy dubplate verification.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            reference_id: Unique identifier for this reference
            metadata: Optional metadata to store with the reference
            
        Returns:
            True if registration successful
        """
        fingerprint = self.fingerprinter.generate_fingerprint(audio_data, sr)
        
        self._reference_fingerprints[reference_id] = fingerprint
        
        return True
    
    def watermark_new(
        self,
        audio_data: np.ndarray,
        sr: int,
        artist_id: str,
        artist_name: str,
        dubplate_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> WatermarkResult:
        """
        Watermark a new dubplate for the artist.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            artist_id: Unique identifier for the artist
            artist_name: Name of the artist
            dubplate_id: Optional specific dubplate ID
            metadata: Optional metadata to embed
            
        Returns:
            WatermarkResult containing watermarked audio
        """
        return self.watermark_manager.embed_watermark(
            audio_data=audio_data,
            sr=sr,
            artist_id=artist_id,
            artist_name=artist_name,
            dubplate_id=dubplate_id,
            metadata=metadata
        )
    
    def get_fingerprint(self, audio_data: np.ndarray, sr: int = 22050) -> FingerprintResult:
        """
        Get the fingerprint for an audio file.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            
        Returns:
            FingerprintResult containing the fingerprint
        """
        return self.fingerprinter.generate_fingerprint(audio_data, sr)
    
    def compare_audio(
        self,
        audio1: np.ndarray,
        audio2: np.ndarray,
        sr: int = 22050
    ) -> float:
        """
        Compare two audio files and return similarity score.
        
        Args:
            audio1: First audio samples
            audio2: Second audio samples
            sr: Sample rate of the audio
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        fp1 = self.fingerprinter.generate_fingerprint(audio1, sr)
        fp2 = self.fingerprinter.generate_fingerprint(audio2, sr)
        
        return self.fingerprinter.compare_fingerprints(fp1, fp2)
    
    def _determine_status(
        self,
        ai_detection: AIDetectionResult,
        watermark: Optional[WatermarkInfo],
        expected_artist_id: Optional[str]
    ) -> tuple:
        """
        Determine authentication status based on all factors.
        
        Returns:
            Tuple of (AuthenticationStatus, confidence)
        """
        # If AI-generated with high probability
        if ai_detection.origin == AudioOrigin.AI_GENERATED:
            return AuthenticationStatus.AI_GENERATED, ai_detection.confidence
        
        # If detected as sound-alike
        if ai_detection.origin == AudioOrigin.SOUND_ALIKE:
            return AuthenticationStatus.SOUND_ALIKE, ai_detection.confidence
        
        # If AI-enhanced
        if ai_detection.origin == AudioOrigin.AI_ENHANCED:
            return AuthenticationStatus.SUSPICIOUS, ai_detection.confidence
        
        # Check watermark if expected artist provided
        if expected_artist_id:
            if watermark and watermark.artist_id == expected_artist_id:
                return AuthenticationStatus.AUTHENTIC, 0.95
            elif watermark:
                # Watermark exists but doesn't match expected artist
                return AuthenticationStatus.SUSPICIOUS, 0.6
            else:
                # No watermark found but artist was expected
                return AuthenticationStatus.UNVERIFIED, 0.5
        
        # No expected artist, check based on AI detection
        if ai_detection.origin == AudioOrigin.HUMAN:
            if watermark:
                return AuthenticationStatus.AUTHENTIC, ai_detection.confidence
            else:
                return AuthenticationStatus.LIKELY_AUTHENTIC, ai_detection.confidence
        
        # Unknown origin
        return AuthenticationStatus.UNVERIFIED, 0.5
    
    def _calculate_verification_confidence(
        self,
        match_score: float,
        ai_probability: float,
        fingerprint_confidence: float
    ) -> float:
        """Calculate overall confidence for legacy verification."""
        # Weight factors
        match_weight = 0.5
        ai_weight = 0.3
        fp_weight = 0.2
        
        # Calculate weighted confidence
        confidence = (
            match_score * match_weight +
            (1 - ai_probability) * ai_weight +
            fingerprint_confidence * fp_weight
        )
        
        return min(max(confidence, 0.0), 1.0)
