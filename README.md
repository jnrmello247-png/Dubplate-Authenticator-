# Dubplate Authenticator

An application for the sound clash culture to identify, authenticate, and watermark dubplates. This app helps distinguish real dubplates from sound-alike artists and AI-produced content.

## Features

### 🎵 Dubplate Authentication
- **Audio Fingerprinting**: Generate unique fingerprints to identify dubplates
- **AI Detection**: Detect AI-generated or AI-enhanced audio content
- **Sound-alike Detection**: Identify potential imitations by sound-alike artists
- **Watermark Verification**: Verify artist authenticity through embedded watermarks

### 📜 Legacy Dubplate Verification
- **Reference Database**: Register and store reference fingerprints for legacy dubplates
- **Match Scoring**: Compare submitted audio against known authentic recordings
- **Historical Authentication**: Verify dubplates from the sound clash archives

### 🔐 Watermarking New Works
- **Invisible Watermarks**: Embed inaudible watermarks in new dubplates
- **Artist Signatures**: Associate dubplates with artist identity
- **Metadata Embedding**: Include additional information like sound system, date, etc.
- **Verification**: Verify watermarks to confirm authenticity

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/jnrmello247-png/Dubplate-Authenticator-.git
cd Dubplate-Authenticator-

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Usage

### Command Line Interface

#### Authenticate a Dubplate
```bash
dubplate-auth authenticate path/to/audio.wav --artist-id "artist_001"
```

#### Verify a Legacy Dubplate
```bash
dubplate-auth verify-legacy path/to/legacy_dub.wav
```

#### Watermark a New Dubplate
```bash
dubplate-auth watermark path/to/original.wav \
  --artist-id "artist_001" \
  --artist-name "Buju Banton" \
  --output watermarked_dub.wav
```

#### Get Audio Fingerprint
```bash
dubplate-auth fingerprint path/to/audio.wav
```

#### Compare Two Audio Files
```bash
dubplate-auth compare audio1.wav audio2.wav
```

#### Detect AI-Generated Content
```bash
dubplate-auth detect-ai path/to/audio.wav
```

#### Start the API Server
```bash
dubplate-auth server --port 5000
```

### REST API

Start the API server and use the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information and available endpoints |
| `/health` | GET | Health check |
| `/authenticate` | POST | Full dubplate authentication |
| `/verify-legacy` | POST | Verify a legacy dubplate |
| `/watermark` | POST | Watermark a new dubplate |
| `/fingerprint` | POST | Get audio fingerprint |
| `/compare` | POST | Compare two audio files |
| `/detect-ai` | POST | Detect AI-generated content |
| `/register-reference` | POST | Register a legacy reference |

#### Example API Usage

```bash
# Authenticate a dubplate
curl -X POST -F "audio=@dubplate.wav" http://localhost:5000/authenticate

# Watermark a new dubplate
curl -X POST \
  -F "audio=@original.wav" \
  -F "artist_id=artist_001" \
  -F "artist_name=Buju Banton" \
  http://localhost:5000/watermark \
  --output watermarked.wav
```

### Python API

```python
from dubplate_auth import DubplateAuthenticator
from dubplate_auth.utils.audio import load_audio_file

# Initialize the authenticator
auth = DubplateAuthenticator(
    secret_key="your_secret_key",
    ai_sensitivity=0.7
)

# Load audio
audio_data, sr = load_audio_file("dubplate.wav")

# Authenticate
result = auth.authenticate(audio_data, sr, expected_artist_id="artist_001")
print(f"Status: {result.status.value}")
print(f"Confidence: {result.confidence}")
print(f"AI Probability: {result.ai_detection.ai_probability}")

# Watermark a new dubplate
watermark_result = auth.watermark_new(
    audio_data=audio_data,
    sr=sr,
    artist_id="artist_001",
    artist_name="Artist Name",
    metadata={"sound_system": "Stone Love", "year": 2024}
)

if watermark_result.success:
    # Save the watermarked audio
    from dubplate_auth.utils.audio import save_audio_file
    save_audio_file("watermarked.wav", watermark_result.audio_data, sr)
```

## Configuration

Create a `.env` file based on `.env.example`:

```env
# Database
DATABASE_URL=sqlite:///dubplate_auth.db

# AI Detection sensitivity (0.0-1.0)
AI_SENSITIVITY=0.7

# Secret key for watermarking
SECRET_KEY=your_secure_secret_key

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000
```

## How It Works

### Audio Fingerprinting
The system analyzes spectral characteristics of audio including:
- Spectral centroid and bandwidth
- Spectral rolloff frequency
- Zero-crossing rate
- RMS energy
- Peak frequencies

These features are combined to create a unique hash identifier for each dubplate.

### AI Detection
The AI detector analyzes multiple aspects of the audio:
- **Spectral Smoothness**: AI-generated audio tends to have unnaturally smooth spectra
- **Timing Patterns**: Human performances have natural micro-timing variations
- **Harmonic Structure**: AI often produces too-perfect harmonic relationships
- **Transient Analysis**: Natural transients vary while AI transients are often uniform

### Watermarking
Watermarks are embedded using high-frequency modulation that is:
- Inaudible to listeners (above typical hearing range)
- Resistant to basic audio processing
- Cryptographically signed for verification

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dubplate_auth

# Run specific test file
pytest tests/test_authenticator.py
```

## Project Structure

```
Dubplate-Authenticator-/
├── src/
│   └── dubplate_auth/
│       ├── __init__.py
│       ├── cli.py                 # Command-line interface
│       ├── api/
│       │   ├── __init__.py
│       │   └── app.py             # Flask REST API
│       ├── core/
│       │   ├── __init__.py
│       │   ├── authenticator.py   # Main authenticator
│       │   ├── fingerprint.py     # Audio fingerprinting
│       │   ├── ai_detector.py     # AI detection
│       │   └── watermark.py       # Watermarking
│       ├── models/
│       │   ├── __init__.py
│       │   └── database.py        # Database models
│       └── utils/
│           ├── __init__.py
│           ├── audio.py           # Audio utilities
│           └── config.py          # Configuration
├── tests/
│   ├── __init__.py
│   ├── test_authenticator.py
│   ├── test_fingerprint.py
│   ├── test_ai_detector.py
│   └── test_watermark.py
├── requirements.txt
├── setup.py
├── pytest.ini
├── .env.example
└── README.md
```

## Sound Clash Culture Context

Dubplates are exclusive, custom-pressed recordings that sound systems use in sound clashes. These unique versions of songs give sound systems their competitive edge. The authenticity of dubplates is crucial to maintaining the integrity of sound clash culture.

This authenticator helps:
- **Sound Systems**: Verify the authenticity of dubplates they acquire
- **Artists**: Protect their exclusive recordings with watermarks
- **Promoters**: Ensure legitimate dubplates are used in competitions
- **Collectors**: Verify the authenticity of legacy dubplates

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.