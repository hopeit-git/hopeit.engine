"""
auth module, provides functionallity to create, validate and decode access and refresh tokens

call init() to load or create RSA keys before using token manipulation methods
"""
from typing import Optional

import pathlib
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey, RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import load_pem_public_key

import jwt
from jwt.exceptions import InvalidSignatureError, ExpiredSignatureError, DecodeError  # type: ignore

from hopeit.app.context import EventContext
from hopeit.server.config import AuthConfig, AuthType
from hopeit.server.logger import engine_logger

__all__ = ['init',
           'new_token',
           'decode_token',
           'validate_token',
           'validate_auth_method',
           'AuthType']

logger = engine_logger()
public_key: Optional[RSAPublicKey] = None
private_key: Optional[RSAPrivateKey] = None


def init(auth_config: AuthConfig):
    """
    loads or creates RSA private/public keys that will be used to create, validate and decode tokens

    :param auth_config: AuthConfig, authorization/authentication server configuration
    """
    global public_key, private_key
    logger.info(__name__, "Initializing auth module...")
    if auth_config.enabled:
        private_key_path = pathlib.Path(auth_config.secrets_location) / 'key.pem'
        public_key_path = pathlib.Path(auth_config.secrets_location) / 'key_pub.pem'
        passphrase = auth_config.auth_passphrase.encode()
        try:
            private_key = load_pem_private_key(
                open(private_key_path, 'rb').read(),
                passphrase, default_backend())
            public_key = load_pem_public_key(
                open(public_key_path, 'rb').read(),
                default_backend())
            logger.info(__name__, f"Found keys in {auth_config.secrets_location}")
        except FileNotFoundError as e:
            if auth_config.create_keys:
                logger.info(__name__, "Keys not found. Creating new key pair...")
                os.makedirs(auth_config.secrets_location, exist_ok=True)
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
                with open(private_key_path, "wb") as f:
                    f.write(private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.BestAvailableEncryption(passphrase),
                    ))
                with open(public_key_path, "wb") as f:
                    f.write(public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ))
                logger.debug(__name__, "Saved generated key pair.")
            else:
                raise e
    else:
        public_key = None
        private_key = None
        logger.warning(__name__, 'Auth module not configured in server config. Auth disabled.')


def new_token(payload: dict) -> str:
    assert private_key
    token = jwt.encode(payload, private_key, algorithm='RS256')
    return token.decode()


def decode_token(token: str) -> dict:
    assert public_key
    return jwt.decode(token, public_key, algorithms=['RS256'])


def validate_token(token: str, context: EventContext) -> Optional[dict]:
    try:
        return decode_token(token)
    except (InvalidSignatureError,
            ExpiredSignatureError,
            DecodeError) as e:
        logger.warning(context, e)
        return None


def validate_auth_none(data: str, context: EventContext):
    context.auth_info['auth_type'] = AuthType.UNSECURED
    context.auth_info['allowed'] = True


def validate_auth_basic(data: str, context: EventContext):
    if data:
        context.auth_info['auth_type'] = AuthType.BASIC
        context.auth_info['allowed'] = True
        context.auth_info['payload'] = data


def validate_auth_bearer(data: str, context: EventContext):
    auth_info = validate_token(data, context)
    if auth_info is not None:
        context.auth_info['auth_type'] = AuthType.BEARER
        context.auth_info['allowed'] = True
        context.auth_info['payload'] = auth_info


def validate_auth_refresh(data: str, context: EventContext):
    auth_info = validate_token(data, context)
    if auth_info is not None:
        context.auth_info['auth_type'] = AuthType.REFRESH
        context.auth_info['allowed'] = True
        context.auth_info['payload'] = auth_info


AUTH_VALIDATION_METHODS = {
    AuthType.UNSECURED: validate_auth_none,
    AuthType.BASIC: validate_auth_basic,
    AuthType.BEARER: validate_auth_bearer,
    AuthType.REFRESH: validate_auth_refresh
}


def validate_auth_method(auth_type: AuthType, data: str, context: EventContext):
    return AUTH_VALIDATION_METHODS[auth_type](data, context)
