"""
Simple encryption tools for testing development
"""

from pathlib import Path

from cryptography.fernet import Fernet

__all__ = ["decrypt", "encrypt", "setup_encryption"]

key_file: Path = Path.home() / ".hopeit" / "test.key"


def setup_encryption(path_to_key_file: str | Path):
    global key_file
    if isinstance(path_to_key_file, str):
        path_to_key_file = Path(path_to_key_file)
    key_file = path_to_key_file


def encrypt(text):
    with open(key_file, encoding="utf-8") as f:
        return Fernet(f.read()).encrypt(text.encode()).decode()


def decrypt(text):
    with open(key_file, encoding="utf-8") as f:
        return Fernet(f.read()).decrypt(text.encode()).decode()
