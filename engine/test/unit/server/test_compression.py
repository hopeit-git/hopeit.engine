from hopeit.app.config import Compression
from hopeit.server.compression import compress, decompress
import zlib
import gzip
import bz2
import lzma
import lz4.frame  # type: ignore

data = bytes([65] * 1000)

comp = {
    Compression.NONE: data,
    Compression.ZIP: b"x\x9cst\x1c\x05\xa3`\x14\x0cw\x00\x00\x89\x0c\xfd\xe9",
    Compression.ZIP_MIN: b"x\x01st\x1c\x05\xa3!0\x1a\x02\xc3=\x04\x00\x89\x0c\xfd\xe9",
    Compression.ZIP_MAX: b"x\xdast\x1c\x05\xa3`\x14\x0cw\x00\x00\x89\x0c\xfd\xe9",
    Compression.BZ2: b"BZh91AY&SYA&\xba\x95\x00\x00\x01\x84\x01\xa0\x00\x00\x80\x00\x08 \x00 "
    b"\xaamA\x98\xba\x83\xc5\xdc\x91N\x14$\x10I\xae\xa5@",
    Compression.BZ2_MIN: b"BZh11AY&SYA&\xba\x95\x00\x00\x01\x84\x01\xa0\x00\x00\x80\x00\x08 \x00 "
    b"\xaamA\x98\xba\x83\xc5\xdc\x91N\x14$\x10I\xae\xa5@",
    Compression.BZ2_MAX: b"BZh91AY&SYA&\xba\x95\x00\x00\x01\x84\x01\xa0\x00\x00\x80\x00\x08 \x00 "
    b"\xaamA\x98\xba\x83\xc5\xdc\x91N\x14$\x10I\xae\xa5@",
    Compression.GZIP: b"\x1f\x8b\x08\x00\xbb\x9d\xe4^\x02\xffst\x1c\x05\xa3`\x14\x0cw\x00"
    b"\x00\x01.\xa0Q\xe8\x03\x00\x00",
    Compression.GZIP_MIN: b"\x1f\x8b\x08\x00\xad\x9e\xe4^\x04\xffst\x1c\x05\xa3!0\x1a\x02\xc3"
    b"=\x04\x00\x01.\xa0Q\xe8\x03\x00\x00",
    Compression.GZIP_MAX: b"\x1f\x8b\x08\x00\xeb\x9e\xe4^\x02\xffst\x1c\x05\xa3`\x14\x0cw\x00"
    b"\x00\x01.\xa0Q\xe8\x03\x00\x00",
    Compression.LZ4: b'\x04"M\x18h@\xe8\x03\x00\x00\x00\x00\x00\x00\xf1\x0e\x00\x00\x00\x1f'
    b"A\x01\x00\xff\xff\xff\xd2PAAAAA\x00\x00\x00\x00",
    Compression.LZ4_MIN: b'\x04"M\x18h@\xe8\x03\x00\x00\x00\x00\x00\x00\xf1\x0e\x00\x00\x00\x1f'
    b"A\x01\x00\xff\xff\xff\xd2PAAAAA\x00\x00\x00\x00",
    Compression.LZ4_MAX: b'\x04"M\x18h@\xe8\x03\x00\x00\x00\x00\x00\x00\xf1\x0e\x00\x00\x00\x1f'
    b"A\x01\x00\xff\xff\xff\xd2PAAAAA\x00\x00\x00\x00",
    Compression.LZMA: b"\xfd7zXZ\x00\x00\x04\xe6\xd6\xb4F\x02\x00!\x01\x16\x00\x00\x00t/\xe5\xa3"
    b"\xe0\x03\xe7\x00\x0b]\x00 \xef\xfb\xbf\xfe\xa3\xb0\xb9\xa6V\x00\x00\x00"
    b"h>\x88>\xdc\xd6E\x93\x00\x01'\xe8\x07\x00\x00\x00\xf4U\x8f\\\xb1\xc4g\xfb"
    b"\x02\x00\x00\x00\x00\x04YZ",
}


def test_compress():
    assert compress(data, Compression.NONE) == data
    assert compress(data, Compression.ZIP) == comp[Compression.ZIP] == zlib.compress(data, 6)
    assert (
        compress(data, Compression.ZIP_MIN) == comp[Compression.ZIP_MIN] == zlib.compress(data, 1)
    )
    assert (
        compress(data, Compression.ZIP_MAX) == comp[Compression.ZIP_MAX] == zlib.compress(data, 9)
    )
    assert compress(data, Compression.BZ2) == comp[Compression.BZ2] == bz2.compress(data, 9)
    assert compress(data, Compression.BZ2_MIN) == comp[Compression.BZ2_MIN] == bz2.compress(data, 1)
    assert compress(data, Compression.BZ2_MAX) == comp[Compression.BZ2_MAX] == bz2.compress(data, 9)
    assert (
        compress(data, Compression.GZIP)[10:]
        == comp[Compression.GZIP][10:]
        == gzip.compress(data, 9)[10:]
    )
    assert (
        compress(data, Compression.GZIP_MIN)[10:]
        == comp[Compression.GZIP_MIN][10:]
        == gzip.compress(data, 1)[10:]
    )
    assert (
        compress(data, Compression.GZIP_MAX)[10:]
        == comp[Compression.GZIP_MAX][10:]
        == gzip.compress(data, 9)[10:]
    )
    assert compress(data, Compression.LZ4) == comp[Compression.LZ4] == lz4.frame.compress(data, 3)
    assert (
        compress(data, Compression.LZ4_MIN)
        == comp[Compression.LZ4_MIN]
        == lz4.frame.compress(data, 0)
    )
    assert (
        compress(data, Compression.LZ4_MAX)
        == comp[Compression.LZ4_MAX]
        == lz4.frame.compress(data, 16)
    )
    assert compress(data, Compression.LZMA) == comp[Compression.LZMA] == lzma.compress(data)


def test_decompress():
    assert decompress(data, Compression.NONE) == data
    assert decompress(comp[Compression.ZIP], Compression.ZIP) == data
    assert decompress(comp[Compression.ZIP_MIN], Compression.ZIP_MIN) == data
    assert decompress(comp[Compression.ZIP_MAX], Compression.ZIP_MAX) == data
    assert decompress(comp[Compression.BZ2], Compression.BZ2) == data
    assert decompress(comp[Compression.BZ2_MIN], Compression.BZ2_MIN) == data
    assert decompress(comp[Compression.BZ2_MAX], Compression.BZ2_MAX) == data
    assert decompress(comp[Compression.GZIP], Compression.GZIP) == data
    assert decompress(comp[Compression.GZIP_MIN], Compression.GZIP_MIN) == data
    assert decompress(comp[Compression.GZIP_MAX], Compression.GZIP_MAX) == data
    assert decompress(comp[Compression.LZ4], Compression.LZ4) == data
    assert decompress(comp[Compression.LZ4_MIN], Compression.LZ4_MIN) == data
    assert decompress(comp[Compression.LZ4_MAX], Compression.LZ4_MAX) == data
    assert decompress(comp[Compression.LZMA], Compression.LZMA) == data
