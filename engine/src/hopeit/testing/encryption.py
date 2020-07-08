"""
Simple encryption tools for testing development
"""
from pathlib import Path
from typing import Union

from cryptography.fernet import Fernet

__all__ = [
    'setup_encryption',
    'encrypt',
    'decrypt'
]

key_file: Path = Path.home() / '.hopeit' / 'test.key'


def setup_encryption(path_to_key_file: Union[str, Path]):
    global key_file
    if isinstance(path_to_key_file, str):
        path_to_key_file = Path(path_to_key_file)
    key_file = path_to_key_file


def encrypt(text):
    with open(key_file) as f:
        return Fernet(f.read()).encrypt(text.encode()).decode()


def decrypt(text):
    with open(key_file) as f:
        return Fernet(f.read()).decrypt(text.encode()).decode()
