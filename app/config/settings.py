from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "data" / "temp"
AUDIO_DIR = TEMP_DIR / "audio"
STATIC_DIR = BASE_DIR / "static"

# Ensure directories exist
for dir_path in [TEMP_DIR, AUDIO_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Configuration
API_CONFIG = {
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": "gpt-3.5-turbo",
        "temperature": 0.3,
        "max_tokens": 2000,
        "timeout": 30,
    },
    "speech_to_text": {
        "model": "base",
        "language": "ja-JP",
    }
}

# Application Settings
APP_SETTINGS = {
    "max_file_size_mb": 50,
    "supported_audio_formats": [".mp3", ".wav", ".m4a"],
    "max_vocabulary_items": 100,
    "default_language": "ja",
    "ai_provider": "openai",  # Tambahan untuk identifikasi provider AI
}

def get_openai_api_key() -> str:
    """Get OpenAI API key with validation"""
    api_key = API_CONFIG["openai"]["api_key"]
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables. Please set OPENAI_API_KEY in your .env file or environment variables.")
    return api_key

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI specific configuration"""
    return API_CONFIG["openai"]

def get_app_config() -> Dict[str, Any]:
    """Get full application configuration"""
    return {
        "api": API_CONFIG,
        "app": APP_SETTINGS,
        "paths": {
            "base": str(BASE_DIR),
            "temp": str(TEMP_DIR),
            "audio": str(AUDIO_DIR),
            "static": str(STATIC_DIR),
        }
    }

# Backward compatibility function (untuk kode yang mungkin masih menggunakan nama lama)
def get_gemini_api_key() -> str:
    """Deprecated: Use get_openai_api_key() instead"""
    import warnings
    warnings.warn(
        "get_gemini_api_key() is deprecated. Use get_openai_api_key() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return get_openai_api_key()

# Utility functions
def validate_api_setup() -> bool:
    """Validate that all required API configurations are properly set"""
    try:
        openai_key = get_openai_api_key()
        return bool(openai_key and len(openai_key.strip()) > 0)
    except ValueError:
        return False

def get_model_config(model_type: str = "default") -> Dict[str, Any]:
    """Get model configuration based on type"""
    configs = {
        "default": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.3,
            "max_tokens": 2000,
        },
        "creative": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 2000,
        },
        "precise": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.1,
            "max_tokens": 1500,
        },
        "gpt4": {
            "model": "gpt-4",
            "temperature": 0.3,
            "max_tokens": 2000,
        }
    }
    return configs.get(model_type, configs["default"])

# Environment validation
def check_environment() -> Dict[str, bool]:
    """Check if all required environment variables are set"""
    checks = {
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "directories_exist": all(path.exists() for path in [TEMP_DIR, AUDIO_DIR]),
        "write_permissions": TEMP_DIR.is_dir() and os.access(TEMP_DIR, os.W_OK),
    }
    return checks

# Configuration summary for debugging
def get_config_summary() -> Dict[str, Any]:
    """Get a summary of current configuration (without sensitive data)"""
    env_check = check_environment()
    return {
        "ai_provider": APP_SETTINGS["ai_provider"],
        "model": API_CONFIG["openai"]["model"],
        "max_vocabulary_items": APP_SETTINGS["max_vocabulary_items"],
        "supported_formats": APP_SETTINGS["supported_audio_formats"],
        "environment_status": env_check,
        "api_key_configured": env_check["openai_api_key"],
        "directories_ready": env_check["directories_exist"] and env_check["write_permissions"],
    }
