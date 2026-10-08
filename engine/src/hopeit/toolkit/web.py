"""
Utilities for handling Web requests
"""

from pathlib import Path
from typing import Union

from hopeit.app.context import PreprocessFileHook


async def save_multipart_attachment(
    file_hook: PreprocessFileHook, path: Union[str, Path], *, chunk_size: int = 8192
):
    """
    Save file using chunks from multipart upload to specified path
    """
    with open(path, "wb") as f:
        async for chunk in file_hook.read_chunks(chunk_size=chunk_size):
            f.write(chunk)
