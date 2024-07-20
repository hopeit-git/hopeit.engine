import uuid
import os
from pathlib import Path
from cryptography.fernet import Fernet

from hopeit.testing.encryption import encrypt, decrypt, setup_encryption


def test_encryption():
    key = Fernet.generate_key().decode()
    key_path = Path("/tmp") / (str(uuid.uuid4()) + ".key")
    with open(key_path, "w") as f:
        f.write(key)
    setup_encryption(key_path)
    msg = "Encrypt this message!"
    enc = encrypt(msg)
    dec = decrypt(enc)
    os.remove(key_path)
    assert enc != msg
    assert dec == msg
