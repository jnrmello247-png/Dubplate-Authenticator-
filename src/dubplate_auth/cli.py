"""
Command-line interface for Dubplate Authenticator.
"""

import argparse
import json
import sys

import numpy as np

from dubplate_auth.core.authenticator import DubplateAuthenticator
from dubplate_auth.utils.audio import load_audio_file, save_audio_file, generate_test_audio
from dubplate_auth.utils.config import get_config


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Dubplate Authenticator - Authenticate and verify dubplates"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Authenticate command
    auth_parser = subparsers.add_parser("authenticate", help="Authenticate a dubplate")
    auth_parser.add_argument("audio", help="Path to audio file")
    auth_parser.add_argument("--artist-id", help="Expected artist ID")
    auth_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    
    # Verify legacy command
    verify_parser = subparsers.add_parser("verify-legacy", help="Verify a legacy dubplate")
    verify_parser.add_argument("audio", help="Path to audio file")
    verify_parser.add_argument("--reference-id", help="Reference ID to verify against")
    verify_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    
    # Watermark command
    watermark_parser = subparsers.add_parser("watermark", help="Watermark a new dubplate")
    watermark_parser.add_argument("audio", help="Path to audio file")
    watermark_parser.add_argument("--artist-id", required=True, help="Artist ID")
    watermark_parser.add_argument("--artist-name", required=True, help="Artist name")
    watermark_parser.add_argument("--output", "-o", required=True, help="Output file path")
    watermark_parser.add_argument("--dubplate-id", help="Specific dubplate ID")
    
    # Fingerprint command
    fp_parser = subparsers.add_parser("fingerprint", help="Get audio fingerprint")
    fp_parser.add_argument("audio", help="Path to audio file")
    fp_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    
    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two audio files")
    compare_parser.add_argument("audio1", help="Path to first audio file")
    compare_parser.add_argument("audio2", help="Path to second audio file")
    compare_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    
    # Detect AI command
    ai_parser = subparsers.add_parser("detect-ai", help="Detect AI-generated content")
    ai_parser.add_argument("audio", help="Path to audio file")
    ai_parser.add_argument("--output", "-o", help="Output file for results (JSON)")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start the API server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    server_parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    server_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return 0
    
    config = get_config()
    authenticator = DubplateAuthenticator(
        secret_key=config.secret_key,
        ai_sensitivity=config.ai_sensitivity
    )
    
    try:
        if args.command == "authenticate":
            return cmd_authenticate(args, authenticator, config)
        elif args.command == "verify-legacy":
            return cmd_verify_legacy(args, authenticator, config)
        elif args.command == "watermark":
            return cmd_watermark(args, authenticator, config)
        elif args.command == "fingerprint":
            return cmd_fingerprint(args, authenticator, config)
        elif args.command == "compare":
            return cmd_compare(args, authenticator, config)
        elif args.command == "detect-ai":
            return cmd_detect_ai(args, authenticator, config)
        elif args.command == "server":
            return cmd_server(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    return 0


def cmd_authenticate(args, authenticator, config):
    """Handle authenticate command."""
    audio_data, sr = load_audio_file(args.audio, config.sample_rate)
    result = authenticator.authenticate(audio_data, sr, args.artist_id)
    
    output = {
        "status": result.status.value,
        "confidence": result.confidence,
        "timestamp": result.timestamp,
        "fingerprint": {
            "hash": result.fingerprint.fingerprint_hash,
            "duration": result.fingerprint.duration,
            "confidence": result.fingerprint.confidence
        },
        "ai_detection": {
            "origin": result.ai_detection.origin.value,
            "probability": result.ai_detection.ai_probability,
            "artifacts": result.ai_detection.artifacts_detected
        },
        "details": result.details
    }
    
    if result.watermark:
        output["watermark"] = {
            "artist_id": result.watermark.artist_id,
            "artist_name": result.watermark.artist_name,
            "dubplate_id": result.watermark.dubplate_id,
            "creation_date": result.watermark.creation_date
        }
    
    _output_results(output, args.output)
    return 0


def cmd_verify_legacy(args, authenticator, config):
    """Handle verify-legacy command."""
    audio_data, sr = load_audio_file(args.audio, config.sample_rate)
    result = authenticator.verify_legacy(audio_data, sr, args.reference_id)
    
    output = {
        "verified": result.verified,
        "confidence": result.confidence,
        "match_score": result.match_score,
        "reference_fingerprint": result.reference_fingerprint,
        "details": result.details
    }
    
    _output_results(output, args.output)
    return 0


def cmd_watermark(args, authenticator, config):
    """Handle watermark command."""
    audio_data, sr = load_audio_file(args.audio, config.sample_rate)
    
    result = authenticator.watermark_new(
        audio_data=audio_data,
        sr=sr,
        artist_id=args.artist_id,
        artist_name=args.artist_name,
        dubplate_id=args.dubplate_id
    )
    
    if not result.success:
        print(f"Error: {result.message}", file=sys.stderr)
        return 1
    
    save_audio_file(args.output, result.audio_data, sr)
    
    print(f"Watermarked audio saved to: {args.output}")
    print(f"Artist ID: {result.watermark_info.artist_id}")
    print(f"Artist Name: {result.watermark_info.artist_name}")
    print(f"Dubplate ID: {result.watermark_info.dubplate_id}")
    print(f"Creation Date: {result.watermark_info.creation_date}")
    print(f"Signature: {result.watermark_info.signature}")
    
    return 0


def cmd_fingerprint(args, authenticator, config):
    """Handle fingerprint command."""
    audio_data, sr = load_audio_file(args.audio, config.sample_rate)
    fp = authenticator.get_fingerprint(audio_data, sr)
    
    output = {
        "hash": fp.fingerprint_hash,
        "duration": fp.duration,
        "sample_rate": fp.sample_rate,
        "confidence": fp.confidence,
        "spectral_features": fp.spectral_features
    }
    
    _output_results(output, args.output)
    return 0


def cmd_compare(args, authenticator, config):
    """Handle compare command."""
    audio1, sr1 = load_audio_file(args.audio1, config.sample_rate)
    audio2, sr2 = load_audio_file(args.audio2, config.sample_rate)
    
    similarity = authenticator.compare_audio(audio1, audio2, config.sample_rate)
    
    output = {
        "similarity": similarity,
        "is_match": similarity > 0.85,
        "match_level": _get_match_level(similarity)
    }
    
    _output_results(output, args.output)
    return 0


def cmd_detect_ai(args, authenticator, config):
    """Handle detect-ai command."""
    audio_data, sr = load_audio_file(args.audio, config.sample_rate)
    result = authenticator.ai_detector.detect(audio_data, sr)
    
    output = {
        "origin": result.origin.value,
        "ai_probability": result.ai_probability,
        "confidence": result.confidence,
        "artifacts_detected": result.artifacts_detected,
        "analysis_details": result.analysis_details
    }
    
    _output_results(output, args.output)
    return 0


def cmd_server(args):
    """Handle server command."""
    from dubplate_auth.api.app import create_app
    
    app = create_app()
    print(f"Starting Dubplate Authenticator API server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
    return 0


def _output_results(data, output_file=None):
    """Output results to console or file."""
    json_str = json.dumps(data, indent=2)
    
    if output_file:
        with open(output_file, "w") as f:
            f.write(json_str)
        print(f"Results saved to: {output_file}")
    else:
        print(json_str)


def _get_match_level(similarity: float) -> str:
    """Get a human-readable match level."""
    if similarity > 0.95:
        return "exact_match"
    elif similarity > 0.85:
        return "high_match"
    elif similarity > 0.70:
        return "moderate_match"
    elif similarity > 0.50:
        return "low_match"
    else:
        return "no_match"


if __name__ == "__main__":
    sys.exit(main())
