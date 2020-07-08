"""
Provides generic `compress` and `decompress` methods for payloads
"""
from functools import partial
import zlib
import gzip
import bz2
import lzma
from typing import Callable, Tuple

import lz4.frame  # type: ignore

from hopeit.app.config import Compression

__all__ = ['compress', 'decompress']


def _compress_none(level: int, data: bytes) -> bytes:
    return data


def _decompress_none(data: bytes) -> bytes:
    return data


def _compress_lz4(level: int, data: bytes) -> bytes:
    return lz4.frame.compress(data, compression_level=level)


def _decompress_lz4(data: bytes) -> bytes:
    return lz4.frame.decompress(data)


def _compress_zlib(level: int, data: bytes) -> bytes:
    return zlib.compress(data, level=level)


def _decompress_zlib(data: bytes) -> bytes:
    return zlib.decompress(data)


def _compress_gzip(level: int, data: bytes) -> bytes:
    return gzip.compress(data, compresslevel=level)


def _decompress_gzip(data: bytes):
    return gzip.decompress(data)


def _compress_bz2(level: int, data: bytes) -> bytes:
    return bz2.compress(data, compresslevel=level)


def _decompress_bz2(data: bytes):
    return bz2.decompress(data)


def _compress_lzma(level: int, data: bytes) -> bytes:
    return lzma.compress(data)


def _decompress_lzma(data: bytes):
    return lzma.decompress(data)


_ALGOS = {
    'none': (_compress_none, 0, _decompress_none),
    'lz4': (_compress_lz4, 3, _decompress_lz4),
    'zip': (_compress_zlib, 6, _decompress_zlib),
    'gzip': (_compress_gzip, 9, _decompress_gzip),
    'bz2': (_compress_bz2, 9, _decompress_bz2),
    'lzma': (_compress_lzma, 0, _decompress_lzma)
}


def _compressors(compression: Compression) -> Tuple[Callable[[bytes], bytes], Callable[[bytes], bytes]]:
    info = compression.value.split(':')
    algo = info[0]
    comp, default_level, decomp = _ALGOS[algo]
    level = default_level if len(info) <= 1 else int(info[1])
    return partial(comp, level), decomp  # type: ignore


_COMPRESS = {
    c: _compressors(c)[0]
    for c in Compression
}

_DECOMPRESS = {
    c: _compressors(c)[1]
    for c in Compression
}


def compress(data: bytes, compression: Compression) -> bytes:
    return _COMPRESS[compression](data)


def decompress(data: bytes, compression: Compression) -> bytes:
    return _DECOMPRESS[compression](data)
