"""
auth module, provides functionallity to create, validate and decode access and refresh tokens

call init() to load or create RSA keys before using token manipulation methods
"""
from typing import Dict, Optional, Set

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
from hopeit.server.logger import engine_extra_logger

__all__ = ['init',
           'new_token',
           'decode_token',
           'validate_token',
           'validate_auth_method',
           'AuthType']

logger, extra = engine_extra_logger()

auth_config: Optional[AuthConfig] = None
private_keys: Dict[str, RSAPrivateKey] = {}
public_keys: Dict[str, RSAPublicKey] = {}
rejected_apps: Set[str] = set()


def init(app_key: str, app_auth_config: AuthConfig):
    """
    loads or creates RSA private/public keys that will be used to create, validate and decode tokens

    :param auth_config: AuthConfig, authorization/authentication server configuration
    """
    global public_keys, private_keys, auth_config
    logger.info(__name__, "Initializing auth module...", extra=extra(app_key=app_key))
    auth_config = app_auth_config
    secrets_path = pathlib.Path(auth_config.secrets_location)
    if auth_config.enabled:
        private_key_path = secrets_path / '.private' / f'{app_key}.pem'
        public_key_path = secrets_path / 'public' / f'{app_key}_pub.pem'
        passphrase = auth_config.auth_passphrase.encode()
        try:
            with open(private_key_path, 'rb') as f:
                private_keys[app_key] = load_pem_private_key(
                    f.read(), passphrase, default_backend()
                )
            with open(public_key_path, 'rb') as f:
                public_keys[app_key] = load_pem_public_key(
                    f.read(), default_backend()
                )
            logger.info(__name__, f"Found keys in {auth_config.secrets_location}", extra=extra(app_key=app_key))
        except FileNotFoundError as e:
            if auth_config.create_keys:
                logger.info(__name__, "Keys not found. Creating new key pair...", extra=extra(app_key=app_key))
                os.makedirs(secrets_path / '.private', exist_ok=True)
                os.makedirs(secrets_path / 'public', exist_ok=True)
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
                public_keys[app_key] = public_key
                private_keys[app_key] = private_key
                logger.debug(__name__, "Saved generated key pair.", extra=extra(app_key=app_key))
            else:
                raise e
    else:
        public_keys = {}
        private_keys = {}
        logger.warning(__name__, 'Auth module not configured in server config. Auth disabled.',
                       extra=extra(app_key=app_key))


class PublicKeyNotFoundError(Exception):
    pass


class PrivateKeyNotFoundError(Exception):
    pass


def app_public_key(app_key: str) -> RSAPublicKey:
    """
    Returns current registerd public key for a given application.
    Attempts to load from disk in case is not cached.
    If previous attemps to load key failed, it will not attempt to load again,
    so an app restart might be necessary in case configuration is fixed.
    """
    def _load_app_public_key():
        if app_key in rejected_apps:
            raise PublicKeyNotFoundError(app_key)
        try:
            logger.info(__name__, "Loading public app keys", extra=extra(app_key=app_key))
            public_key_path = pathlib.Path(auth_config.secrets_location) / 'public' / f'{app_key}_pub.pem'
            with open(public_key_path, 'rb') as f:
                public_keys[app_key] = load_pem_public_key(
                    f.read(), default_backend()
                )
            return public_keys[app_key]
        except FileNotFoundError as e:
            logger.error(__name__, "Cannot find public key for app", extra=extra(app_key=app_key))
            rejected_apps.add(app_key)
            raise PublicKeyNotFoundError(app_key) from e

    key = public_keys.get(app_key)
    if key is None:
        return _load_app_public_key()
    return key


def app_private_key(app_key: str) -> RSAPrivateKey:
    key = private_keys.get(app_key)
    if key is None:
        raise PrivateKeyNotFoundError(app_key)
    return key


def new_token(app_key: str, payload: dict) -> str:
    private_key = app_private_key(app_key)
    token = jwt.encode(
        {**payload, "app": app_key}, private_key, algorithm='RS256'
    )
    return token.decode()


def decode_token(token: str) -> dict:
    info = jwt.decode(token, verify=False)
    app_key = info['app']
    public_key = app_public_key(app_key)
    return jwt.decode(token, public_key, algorithms=['RS256'])


def validate_token(token: str, context: EventContext) -> Optional[dict]:
    try:
        return decode_token(token)
    except (InvalidSignatureError,
            ExpiredSignatureError,
            DecodeError,
            PublicKeyNotFoundError) as e:
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
