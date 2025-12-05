"""
Audio utilities for Dubplate Authenticator.

Provides helper functions for audio processing and file handling.
"""

import os
from typing import Optional, Tuple

import numpy as np


def load_audio_file(filepath: str, sr: Optional[int] = 22050) -> Tuple[np.ndarray, int]:
    """
    Load an audio file and return samples and sample rate.
    
    Args:
        filepath: Path to the audio file
        sr: Target sample rate (None to keep original)
        
    Returns:
        Tuple of (audio_samples, sample_rate)
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")
    
    ext = os.path.splitext(filepath)[1].lower()
    supported_formats = [".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"]
    
    if ext not in supported_formats:
        raise ValueError(f"Unsupported audio format: {ext}. Supported: {supported_formats}")
    
    # Try to use librosa first (best quality)
    try:
        import librosa
        audio_data, file_sr = librosa.load(filepath, sr=sr, mono=True)
        return audio_data.astype(np.float32), sr if sr else file_sr
    except ImportError:
        pass
    except Exception:
        pass
    
    # Fallback to soundfile
    try:
        import soundfile as sf
        audio_data, file_sr = sf.read(filepath)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Resample if needed
        if sr is not None and file_sr != sr:
            audio_data = resample_audio(audio_data, file_sr, sr)
            file_sr = sr
        
        return audio_data.astype(np.float32), file_sr
    except ImportError:
        # Fallback for basic WAV support without soundfile
        if ext == ".wav":
            return _load_wav_basic(filepath, sr)
        raise ImportError("soundfile or librosa library required for non-WAV formats")


def _load_wav_basic(filepath: str, target_sr: Optional[int]) -> Tuple[np.ndarray, int]:
    """Basic WAV file loader using scipy."""
    from scipy.io import wavfile
    
    sr, audio_data = wavfile.read(filepath)
    
    # Convert to float
    if audio_data.dtype == np.int16:
        audio_data = audio_data.astype(np.float32) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_data = audio_data.astype(np.float32) / 2147483648.0
    elif audio_data.dtype == np.uint8:
        audio_data = (audio_data.astype(np.float32) - 128) / 128.0
    
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    
    # Resample if needed
    if target_sr is not None and sr != target_sr:
        audio_data = resample_audio(audio_data, sr, target_sr)
        sr = target_sr
    
    return audio_data.astype(np.float32), sr


def save_audio_file(
    filepath: str,
    audio_data: np.ndarray,
    sr: int,
    format_type: str = "wav"
) -> bool:
    """
    Save audio data to a file.
    
    Args:
        filepath: Output file path
        audio_data: Audio samples as numpy array
        sr: Sample rate
        format_type: Output format type
        
    Returns:
        True if successful
    """
    try:
        import soundfile as sf
        sf.write(filepath, audio_data, sr)
        return True
    except ImportError:
        if format_type == "wav":
            return _save_wav_basic(filepath, audio_data, sr)
        raise ImportError("soundfile library required for non-WAV formats")


def _save_wav_basic(filepath: str, audio_data: np.ndarray, sr: int) -> bool:
    """Basic WAV file saver using scipy."""
    from scipy.io import wavfile
    
    # Convert to int16 for WAV
    audio_int16 = (audio_data * 32767).astype(np.int16)
    wavfile.write(filepath, sr, audio_int16)
    return True


def resample_audio(audio_data: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio to a different sample rate.
    
    Args:
        audio_data: Audio samples
        orig_sr: Original sample rate
        target_sr: Target sample rate
        
    Returns:
        Resampled audio data
    """
    if orig_sr == target_sr:
        return audio_data
    
    try:
        import librosa
        return librosa.resample(audio_data, orig_sr=orig_sr, target_sr=target_sr)
    except ImportError:
        # Fallback to basic interpolation if librosa not available
        duration = len(audio_data) / orig_sr
        new_length = int(duration * target_sr)
        x_old = np.linspace(0, duration, len(audio_data))
        x_new = np.linspace(0, duration, new_length)
        return np.interp(x_new, x_old, audio_data)


def normalize_audio(audio_data: np.ndarray, target_level: float = 0.9) -> np.ndarray:
    """
    Normalize audio to a target peak level.
    
    Args:
        audio_data: Audio samples
        target_level: Target peak level (0.0-1.0)
        
    Returns:
        Normalized audio data
    """
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        return audio_data * (target_level / max_val)
    return audio_data


def trim_silence(
    audio_data: np.ndarray,
    threshold: float = 0.01,
    min_samples: int = 100
) -> np.ndarray:
    """
    Trim silence from the beginning and end of audio.
    
    Args:
        audio_data: Audio samples
        threshold: Silence threshold
        min_samples: Minimum samples to keep
        
    Returns:
        Trimmed audio data
    """
    # Find non-silent regions
    above_threshold = np.abs(audio_data) > threshold
    
    if not np.any(above_threshold):
        return audio_data[:min_samples]
    
    # Find first and last non-silent samples
    nonzero_indices = np.where(above_threshold)[0]
    start = max(0, nonzero_indices[0] - 100)
    end = min(len(audio_data), nonzero_indices[-1] + 100)
    
    return audio_data[start:end]


def generate_test_audio(
    duration: float = 1.0,
    sr: int = 22050,
    frequency: float = 440.0,
    amplitude: float = 0.5
) -> np.ndarray:
    """
    Generate a test audio signal (sine wave).
    
    Args:
        duration: Duration in seconds
        sr: Sample rate
        frequency: Frequency of the sine wave
        amplitude: Amplitude (0.0-1.0)
        
    Returns:
        Audio samples as numpy array
    """
    t = np.linspace(0, duration, int(duration * sr), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.float32)


def mix_audio(
    audio1: np.ndarray,
    audio2: np.ndarray,
    ratio: float = 0.5
) -> np.ndarray:
    """
    Mix two audio signals together.
    
    Args:
        audio1: First audio signal
        audio2: Second audio signal
        ratio: Mix ratio (0.0 = only audio1, 1.0 = only audio2)
        
    Returns:
        Mixed audio
    """
    # Make same length
    max_len = max(len(audio1), len(audio2))
    if len(audio1) < max_len:
        audio1 = np.pad(audio1, (0, max_len - len(audio1)))
    if len(audio2) < max_len:
        audio2 = np.pad(audio2, (0, max_len - len(audio2)))
    
    # Mix
    mixed = audio1 * (1 - ratio) + audio2 * ratio
    
    # Normalize if needed
    max_val = np.max(np.abs(mixed))
    if max_val > 1.0:
        mixed = mixed / max_val
    
    return mixed
