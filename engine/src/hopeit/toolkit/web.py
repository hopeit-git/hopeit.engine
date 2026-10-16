"""
Utilities for handling Web requests
"""

from asyncio import to_thread
from pathlib import Path

from hopeit.app.context import PreprocessFileHook


async def save_multipart_attachment(
    file_hook: PreprocessFileHook, path: str | Path, *, chunk_size: int = 8192
):
    """
    Save file using chunks from multipart upload to specified path
    """
    file = await to_thread(open, path, "wb")
    try:
        async for chunk in file_hook.read_chunks(chunk_size=chunk_size):
            await to_thread(file.write, chunk)
    finally:
        await to_thread(file.close)
