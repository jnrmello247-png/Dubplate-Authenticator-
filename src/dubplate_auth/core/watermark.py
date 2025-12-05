"""
Watermarking Module for Dubplate Authentication.

This module provides audio watermarking capabilities for dubplates,
allowing artists to embed invisible signatures in their new works
for authentication and verification purposes.
"""

import hashlib
import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import numpy as np


@dataclass
class WatermarkInfo:
    """Information about a watermark."""
    
    artist_id: str
    artist_name: str
    creation_date: str
    dubplate_id: str
    metadata: dict
    signature: str


@dataclass
class WatermarkResult:
    """Result of a watermark operation."""
    
    success: bool
    watermark_info: Optional[WatermarkInfo]
    audio_data: Optional[np.ndarray]
    message: str


class WatermarkManager:
    """
    Audio watermarking system for dubplate authentication.
    
    Embeds invisible watermarks in audio that can be used to verify
    authenticity and track the origin of dubplates.
    """
    
    # Watermark configuration
    WATERMARK_FREQUENCY_LOW = 18000  # Hz - low bound for watermark
    WATERMARK_FREQUENCY_HIGH = 20000  # Hz - high bound for watermark
    WATERMARK_AMPLITUDE = 0.001  # Low amplitude to be inaudible
    SYNC_PATTERN = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 1]  # Sync pattern for detection
    
    def __init__(self, secret_key: str = "dubplate_auth_secret"):
        """
        Initialize the WatermarkManager.
        
        Args:
            secret_key: Secret key used for watermark generation
        """
        self.secret_key = secret_key
    
    def embed_watermark(
        self,
        audio_data: np.ndarray,
        sr: int,
        artist_id: str,
        artist_name: str,
        dubplate_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> WatermarkResult:
        """
        Embed a watermark in audio data.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            artist_id: Unique identifier for the artist
            artist_name: Name of the artist
            dubplate_id: Unique identifier for the dubplate (auto-generated if not provided)
            metadata: Additional metadata to embed
            
        Returns:
            WatermarkResult containing the watermarked audio and info
        """
        if len(audio_data) < sr:  # Minimum 1 second of audio
            return WatermarkResult(
                success=False,
                watermark_info=None,
                audio_data=None,
                message="Audio too short for watermarking (minimum 1 second required)"
            )
        
        # Generate dubplate ID if not provided
        if dubplate_id is None:
            dubplate_id = self._generate_dubplate_id(artist_id, artist_name)
        
        # Create watermark info
        creation_date = datetime.now(timezone.utc).isoformat()
        
        # Create watermark data
        watermark_data = {
            "artist_id": artist_id,
            "artist_name": artist_name,
            "creation_date": creation_date,
            "dubplate_id": dubplate_id,
            "metadata": metadata or {}
        }
        
        # Generate signature
        signature = self._generate_signature(watermark_data)
        watermark_data["signature"] = signature
        
        # Encode watermark as binary
        binary_data = self._encode_to_binary(watermark_data)
        
        # Embed watermark in audio
        watermarked_audio = self._embed_binary_watermark(audio_data, sr, binary_data)
        
        watermark_info = WatermarkInfo(
            artist_id=artist_id,
            artist_name=artist_name,
            creation_date=creation_date,
            dubplate_id=dubplate_id,
            metadata=metadata or {},
            signature=signature
        )
        
        return WatermarkResult(
            success=True,
            watermark_info=watermark_info,
            audio_data=watermarked_audio,
            message="Watermark successfully embedded"
        )
    
    def extract_watermark(self, audio_data: np.ndarray, sr: int) -> WatermarkResult:
        """
        Extract a watermark from audio data.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            
        Returns:
            WatermarkResult containing the extracted watermark info
        """
        if len(audio_data) < sr:
            return WatermarkResult(
                success=False,
                watermark_info=None,
                audio_data=None,
                message="Audio too short for watermark extraction"
            )
        
        # Extract binary data from audio
        binary_data = self._extract_binary_watermark(audio_data, sr)
        
        if binary_data is None:
            return WatermarkResult(
                success=False,
                watermark_info=None,
                audio_data=None,
                message="No watermark found in audio"
            )
        
        # Decode watermark data
        watermark_data = self._decode_from_binary(binary_data)
        
        if watermark_data is None:
            return WatermarkResult(
                success=False,
                watermark_info=None,
                audio_data=None,
                message="Failed to decode watermark data"
            )
        
        # Verify signature
        signature = watermark_data.get("signature", "")
        data_to_verify = {k: v for k, v in watermark_data.items() if k != "signature"}
        expected_signature = self._generate_signature(data_to_verify)
        
        if signature != expected_signature:
            return WatermarkResult(
                success=False,
                watermark_info=None,
                audio_data=None,
                message="Watermark signature verification failed"
            )
        
        watermark_info = WatermarkInfo(
            artist_id=watermark_data.get("artist_id", ""),
            artist_name=watermark_data.get("artist_name", ""),
            creation_date=watermark_data.get("creation_date", ""),
            dubplate_id=watermark_data.get("dubplate_id", ""),
            metadata=watermark_data.get("metadata", {}),
            signature=signature
        )
        
        return WatermarkResult(
            success=True,
            watermark_info=watermark_info,
            audio_data=None,
            message="Watermark successfully extracted and verified"
        )
    
    def verify_watermark(self, audio_data: np.ndarray, sr: int, expected_artist_id: str) -> bool:
        """
        Verify that audio contains a valid watermark from a specific artist.
        
        Args:
            audio_data: Audio samples as numpy array
            sr: Sample rate of the audio
            expected_artist_id: Expected artist ID in the watermark
            
        Returns:
            True if watermark is valid and matches expected artist
        """
        result = self.extract_watermark(audio_data, sr)
        
        if not result.success or result.watermark_info is None:
            return False
        
        return result.watermark_info.artist_id == expected_artist_id
    
    def _generate_dubplate_id(self, artist_id: str, artist_name: str) -> str:
        """Generate a unique dubplate ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = f"{artist_id}:{artist_name}:{timestamp}:{self.secret_key}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _generate_signature(self, data: dict) -> str:
        """Generate a signature for watermark data."""
        data_str = json.dumps(data, sort_keys=True)
        signature_data = f"{data_str}:{self.secret_key}"
        return hashlib.sha256(signature_data.encode()).hexdigest()
    
    def _encode_to_binary(self, data: dict) -> list:
        """Encode watermark data to binary."""
        # Convert to JSON string
        json_str = json.dumps(data, sort_keys=True)
        
        # Convert string to binary
        binary = []
        for char in json_str:
            byte_val = ord(char)
            for i in range(8):
                binary.append((byte_val >> (7 - i)) & 1)
        
        # Add sync pattern at the beginning
        return self.SYNC_PATTERN + binary + self.SYNC_PATTERN
    
    def _decode_from_binary(self, binary: list) -> Optional[dict]:
        """Decode binary data to watermark info."""
        # Find sync pattern
        sync_len = len(self.SYNC_PATTERN)
        
        start_idx = None
        for i in range(len(binary) - sync_len):
            if binary[i:i+sync_len] == self.SYNC_PATTERN:
                start_idx = i + sync_len
                break
        
        if start_idx is None:
            return None
        
        # Find end sync pattern
        end_idx = None
        for i in range(start_idx, len(binary) - sync_len):
            if binary[i:i+sync_len] == self.SYNC_PATTERN:
                end_idx = i
                break
        
        if end_idx is None:
            return None
        
        # Extract data bits
        data_bits = binary[start_idx:end_idx]
        
        # Convert to bytes
        if len(data_bits) % 8 != 0:
            return None
        
        chars = []
        for i in range(0, len(data_bits), 8):
            byte_val = 0
            for j in range(8):
                byte_val = (byte_val << 1) | data_bits[i + j]
            chars.append(chr(byte_val))
        
        json_str = "".join(chars)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def _embed_binary_watermark(self, audio_data: np.ndarray, sr: int, binary: list) -> np.ndarray:
        """Embed binary watermark data in audio using high-frequency modulation."""
        watermarked = audio_data.copy().astype(np.float64)
        
        # Calculate bit duration (samples per bit)
        bit_duration = sr // 100  # 100 bits per second
        total_samples_needed = len(binary) * bit_duration
        
        if total_samples_needed > len(watermarked):
            # Repeat the watermark to fill available space, or truncate
            available_bits = len(watermarked) // bit_duration
            binary = binary[:available_bits]
        
        # Generate time array
        t = np.arange(len(watermarked)) / sr
        
        # Create carrier frequency
        carrier_freq = (self.WATERMARK_FREQUENCY_LOW + self.WATERMARK_FREQUENCY_HIGH) / 2
        
        # Embed each bit
        for i, bit in enumerate(binary):
            start_sample = i * bit_duration
            end_sample = min((i + 1) * bit_duration, len(watermarked))
            
            if start_sample >= len(watermarked):
                break
            
            # Create watermark signal for this bit
            bit_t = t[start_sample:end_sample]
            
            if bit == 1:
                # Embed '1' using carrier frequency
                watermark_signal = self.WATERMARK_AMPLITUDE * np.sin(
                    2 * np.pi * carrier_freq * bit_t
                )
            else:
                # Embed '0' using slightly different frequency
                watermark_signal = self.WATERMARK_AMPLITUDE * np.sin(
                    2 * np.pi * (carrier_freq + 500) * bit_t
                )
            
            watermarked[start_sample:end_sample] += watermark_signal
        
        # Normalize to prevent clipping
        max_val = np.max(np.abs(watermarked))
        if max_val > 1.0:
            watermarked = watermarked / max_val
        
        return watermarked.astype(audio_data.dtype)
    
    def _extract_binary_watermark(self, audio_data: np.ndarray, sr: int) -> Optional[list]:
        """Extract binary watermark data from audio."""
        # High-pass filter to isolate watermark frequencies
        # Using simple FFT-based filtering
        
        n_fft = 4096
        hop_length = 2048
        
        # Calculate bit duration
        bit_duration = sr // 100
        carrier_freq = (self.WATERMARK_FREQUENCY_LOW + self.WATERMARK_FREQUENCY_HIGH) / 2
        alt_freq = carrier_freq + 500
        
        binary = []
        
        # Process audio in chunks corresponding to bits
        n_bits = len(audio_data) // bit_duration
        
        for i in range(n_bits):
            start_sample = i * bit_duration
            end_sample = min((i + 1) * bit_duration, len(audio_data))
            
            chunk = audio_data[start_sample:end_sample]
            
            if len(chunk) < n_fft:
                chunk = np.pad(chunk, (0, n_fft - len(chunk)))
            
            # FFT analysis
            fft_result = np.fft.rfft(chunk[:n_fft])
            magnitude = np.abs(fft_result)
            freqs = np.fft.rfftfreq(n_fft, 1/sr)
            
            # Find energy at carrier and alternate frequencies
            carrier_idx = np.argmin(np.abs(freqs - carrier_freq))
            alt_idx = np.argmin(np.abs(freqs - alt_freq))
            
            carrier_energy = magnitude[carrier_idx]
            alt_energy = magnitude[alt_idx]
            
            # Determine bit value based on which frequency has more energy
            if carrier_energy > alt_energy:
                binary.append(1)
            else:
                binary.append(0)
        
        # Look for sync pattern
        sync_len = len(self.SYNC_PATTERN)
        found_sync = False
        
        for i in range(len(binary) - sync_len):
            if binary[i:i+sync_len] == self.SYNC_PATTERN:
                found_sync = True
                break
        
        if not found_sync:
            return None
        
        return binary
