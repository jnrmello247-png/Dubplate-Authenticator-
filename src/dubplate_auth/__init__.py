"""
Dubplate Authenticator - Authentication and verification for dubplates.

This package provides tools for:
- Identifying and authenticating real dubplates from sound-alike artists and AI-produced content
- Authenticating and verifying legacy dubplates
- Watermarking new works for artists at source
"""

__version__ = "1.0.0"
__author__ = "Dubplate Authenticator Team"

from dubplate_auth.core.authenticator import DubplateAuthenticator
from dubplate_auth.core.fingerprint import AudioFingerprint
from dubplate_auth.core.ai_detector import AIDetector
from dubplate_auth.core.watermark import WatermarkManager

__all__ = [
    "DubplateAuthenticator",
    "AudioFingerprint",
    "AIDetector",
    "WatermarkManager",
]
