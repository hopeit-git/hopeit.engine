"""
Simple Example: Download Something Streamed
-------------------------------------------
Download randomly created content as file.
The PostprocessHook return the requested resource as stream using `create_stream_response`.
"""
from dataclasses import dataclass
import os

from hopeit.dataobjects import BinaryDownload
from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook


__steps__ = ['find_image']


@dataclass
class RandomFile(BinaryDownload):
    file_name: str


__api__ = event_api(
    query_args=[("file_name", str, "expected return file name")],
    responses={
        200: (RandomFile, "Return random content with filename=`file_name`")
    }
)

async def find_image(payload: None, context: EventContext, *, file_name: str) -> RandomFile:
    """
    Prepare output file name to be streamd
    """
    return RandomFile(file_name=file_name)


async def __postprocess__(random_file: RandomFile, context: EventContext, response: PostprocessHook) -> str:
    """
    Stream 50 MB of binary random content:
    """
    file_size = 1024 * 1024 * 50
    stream = await response.create_stream_response(filename=random_file.file_name,
                                                   content_type=random_file.content_type,
                                                   content_length=file_size)

    for _ in range(50):
        await stream.write(os.urandom(1024 * 1024))
    return stream
