"""
Flask API for Dubplate Authenticator.

Provides REST endpoints for dubplate authentication, verification,
and watermarking operations.
"""

import io
import json
import os
import tempfile
from typing import Optional

import numpy as np
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from dubplate_auth.core.authenticator import DubplateAuthenticator, AuthenticationStatus
from dubplate_auth.utils.audio import load_audio_file, save_audio_file, generate_test_audio
from dubplate_auth.utils.config import get_config


def create_app(config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    CORS(app)
    
    if config is None:
        config = get_config()
    
    app.config["MAX_CONTENT_LENGTH"] = config.max_file_size
    
    # Initialize the authenticator
    authenticator = DubplateAuthenticator(
        secret_key=config.secret_key,
        ai_sensitivity=config.ai_sensitivity
    )
    
    @app.route("/", methods=["GET"])
    def index():
        """API root endpoint."""
        return jsonify({
            "name": "Dubplate Authenticator API",
            "version": "1.0.0",
            "description": "Authenticate and verify dubplates for sound clash culture",
            "endpoints": {
                "POST /authenticate": "Full authentication of a dubplate",
                "POST /verify-legacy": "Verify a legacy dubplate",
                "POST /watermark": "Watermark a new dubplate",
                "POST /fingerprint": "Get fingerprint for an audio file",
                "POST /compare": "Compare two audio files",
                "POST /detect-ai": "Detect AI-generated content",
                "POST /register-reference": "Register a legacy reference",
                "GET /health": "Health check"
            }
        })
    
    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "service": "dubplate-authenticator"})
    
    @app.route("/authenticate", methods=["POST"])
    def authenticate():
        """
        Authenticate a dubplate.
        
        Expects multipart/form-data with:
        - audio: Audio file
        - artist_id (optional): Expected artist ID for verification
        """
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        expected_artist_id = request.form.get("artist_id")
        
        try:
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_file.save(tmp.name)
                
                try:
                    audio_data, sr = load_audio_file(tmp.name, config.sample_rate)
                except Exception as e:
                    return jsonify({"error": f"Failed to load audio: {str(e)}"}), 400
                finally:
                    os.unlink(tmp.name)
            
            # Perform authentication
            result = authenticator.authenticate(audio_data, sr, expected_artist_id)
            
            response = {
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
                "watermark": None,
                "details": result.details
            }
            
            if result.watermark:
                response["watermark"] = {
                    "artist_id": result.watermark.artist_id,
                    "artist_name": result.watermark.artist_name,
                    "dubplate_id": result.watermark.dubplate_id,
                    "creation_date": result.watermark.creation_date
                }
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/verify-legacy", methods=["POST"])
    def verify_legacy():
        """
        Verify a legacy dubplate.
        
        Expects multipart/form-data with:
        - audio: Audio file
        - reference_id (optional): Specific reference to verify against
        """
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        reference_id = request.form.get("reference_id")
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_file.save(tmp.name)
                
                try:
                    audio_data, sr = load_audio_file(tmp.name, config.sample_rate)
                except Exception as e:
                    return jsonify({"error": f"Failed to load audio: {str(e)}"}), 400
                finally:
                    os.unlink(tmp.name)
            
            result = authenticator.verify_legacy(audio_data, sr, reference_id)
            
            return jsonify({
                "verified": result.verified,
                "confidence": result.confidence,
                "match_score": result.match_score,
                "reference_fingerprint": result.reference_fingerprint,
                "details": result.details
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/watermark", methods=["POST"])
    def watermark():
        """
        Watermark a new dubplate.
        
        Expects multipart/form-data with:
        - audio: Audio file
        - artist_id: Artist identifier
        - artist_name: Artist name
        - dubplate_id (optional): Specific dubplate ID
        - metadata (optional): JSON string of additional metadata
        """
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        artist_id = request.form.get("artist_id")
        artist_name = request.form.get("artist_name")
        
        if not artist_id or not artist_name:
            return jsonify({"error": "artist_id and artist_name are required"}), 400
        
        dubplate_id = request.form.get("dubplate_id")
        metadata_str = request.form.get("metadata")
        metadata = json.loads(metadata_str) if metadata_str else None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_file.save(tmp.name)
                
                try:
                    audio_data, sr = load_audio_file(tmp.name, config.sample_rate)
                except Exception as e:
                    return jsonify({"error": f"Failed to load audio: {str(e)}"}), 400
                finally:
                    os.unlink(tmp.name)
            
            result = authenticator.watermark_new(
                audio_data=audio_data,
                sr=sr,
                artist_id=artist_id,
                artist_name=artist_name,
                dubplate_id=dubplate_id,
                metadata=metadata
            )
            
            if not result.success:
                return jsonify({"error": result.message}), 400
            
            # Save watermarked audio to send back
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                save_audio_file(tmp.name, result.audio_data, sr)
                
                return send_file(
                    tmp.name,
                    mimetype="audio/wav",
                    as_attachment=True,
                    download_name=f"watermarked_{result.watermark_info.dubplate_id}.wav"
                )
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/fingerprint", methods=["POST"])
    def fingerprint():
        """
        Get the fingerprint for an audio file.
        
        Expects multipart/form-data with:
        - audio: Audio file
        """
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_file.save(tmp.name)
                
                try:
                    audio_data, sr = load_audio_file(tmp.name, config.sample_rate)
                except Exception as e:
                    return jsonify({"error": f"Failed to load audio: {str(e)}"}), 400
                finally:
                    os.unlink(tmp.name)
            
            fp = authenticator.get_fingerprint(audio_data, sr)
            
            return jsonify({
                "hash": fp.fingerprint_hash,
                "duration": fp.duration,
                "sample_rate": fp.sample_rate,
                "confidence": fp.confidence,
                "spectral_features": fp.spectral_features
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/compare", methods=["POST"])
    def compare():
        """
        Compare two audio files.
        
        Expects multipart/form-data with:
        - audio1: First audio file
        - audio2: Second audio file
        """
        if "audio1" not in request.files or "audio2" not in request.files:
            return jsonify({"error": "Both audio1 and audio2 files required"}), 400
        
        try:
            audio_data = []
            for key in ["audio1", "audio2"]:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                    request.files[key].save(tmp.name)
                    try:
                        data, sr = load_audio_file(tmp.name, config.sample_rate)
                        audio_data.append(data)
                    finally:
                        os.unlink(tmp.name)
            
            similarity = authenticator.compare_audio(
                audio_data[0], 
                audio_data[1], 
                config.sample_rate
            )
            
            return jsonify({
                "similarity": similarity,
                "is_match": similarity > 0.85,
                "match_level": _get_match_level(similarity)
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/detect-ai", methods=["POST"])
    def detect_ai():
        """
        Detect if audio is AI-generated.
        
        Expects multipart/form-data with:
        - audio: Audio file
        """
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_file.save(tmp.name)
                
                try:
                    audio_data, sr = load_audio_file(tmp.name, config.sample_rate)
                except Exception as e:
                    return jsonify({"error": f"Failed to load audio: {str(e)}"}), 400
                finally:
                    os.unlink(tmp.name)
            
            result = authenticator.ai_detector.detect(audio_data, sr)
            
            return jsonify({
                "origin": result.origin.value,
                "ai_probability": result.ai_probability,
                "confidence": result.confidence,
                "artifacts_detected": result.artifacts_detected,
                "analysis_details": result.analysis_details
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route("/register-reference", methods=["POST"])
    def register_reference():
        """
        Register a legacy reference for verification.
        
        Expects multipart/form-data with:
        - audio: Audio file
        - reference_id: Unique identifier for the reference
        - metadata (optional): JSON string of metadata
        """
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files["audio"]
        reference_id = request.form.get("reference_id")
        
        if not reference_id:
            return jsonify({"error": "reference_id is required"}), 400
        
        metadata_str = request.form.get("metadata")
        metadata = json.loads(metadata_str) if metadata_str else None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_file.save(tmp.name)
                
                try:
                    audio_data, sr = load_audio_file(tmp.name, config.sample_rate)
                except Exception as e:
                    return jsonify({"error": f"Failed to load audio: {str(e)}"}), 400
                finally:
                    os.unlink(tmp.name)
            
            success = authenticator.register_reference(
                audio_data, sr, reference_id, metadata
            )
            
            if success:
                fp = authenticator.get_fingerprint(audio_data, sr)
                return jsonify({
                    "success": True,
                    "reference_id": reference_id,
                    "fingerprint_hash": fp.fingerprint_hash,
                    "message": "Reference registered successfully"
                })
            else:
                return jsonify({"error": "Failed to register reference"}), 500
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    def _get_match_level(similarity: float) -> str:
        """Get a human-readable match level from similarity score."""
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
    
    return app


# For development
if __name__ == "__main__":
    app = create_app()
    config = get_config()
    app.run(host=config.api_host, port=config.api_port, debug=config.debug)
