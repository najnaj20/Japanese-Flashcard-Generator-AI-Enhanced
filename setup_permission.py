import os
import stat
from pathlib import Path

def setup_permissions():
    """Setup required permissions for directories"""
    dirs_to_setup = [
        "app/data/temp",
        "app/data/temp/audio",
        "app/data/temp/whisper_cache"
    ]
    
    for dir_path in dirs_to_setup:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        # Set read/write permissions
        os.chmod(path, 0o777)

def setup_directories():
    """Setup direktori dengan permission yang benar"""
    
    # Buat direktori yang diperlukan
    directories = [
        Path("app/data/temp"),
        Path("app/data/temp/audio"),
        Path("app/data/temp/whisper_cache"),
        Path.home() / ".cache" / "whisper",
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            # Set permission untuk read, write, execute untuk owner
            os.chmod(str(directory), stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            print(f"✅ Created and set permissions for: {directory}")
        except Exception as e:
            print(f"❌ Failed to setup {directory}: {e}")
    
    # Set environment variables
    os.environ['WHISPER_CACHE_DIR'] = str(Path("app/data/temp/whisper_cache").absolute())
    os.environ['XDG_CACHE_HOME'] = str(Path("app/data/temp/whisper_cache").absolute())
    
    print("✅ Environment variables set")

if __name__ == "__main__":
    setup_directories()