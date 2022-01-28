"""
Simple Example: Download Something Streamed
-------------------------------------------
Download streamd randomly created content as file.
The PostprocessHook return the requested resource as stream using `prepare_stream_response`.
"""
from dataclasses import dataclass

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import BinaryDownload

__steps__ = ['get_streamed_data']


@dataclass
class RandomFile(BinaryDownload):
    file_name: str


__api__ = event_api(
    query_args=[("file_name", str, "expected return file name")],
    responses={
        200: (RandomFile, "Return random content with filename=`file_name`")
    }
)


async def get_streamed_data(payload: None, context: EventContext, *, file_name: str) -> RandomFile:
    """
    Prepare output file name to be streamd
    """
    return RandomFile(file_name=file_name)


async def __postprocess__(file: RandomFile, context: EventContext, response: PostprocessHook) -> RandomFile:
    """
    Stream 50 MB of binary random content:
    """
    file_size = 1024 * 1024 * 50
    stream = await response.prepare_stream_response(
        context,
        content_disposition=f'attachment; filename="{file.file_name}"',
        content_type=file.content_type,
        content_length=file_size
    )

    for i in range(50):
        await stream.write(f"{i}".encode() * (1024 * 1024))
    return file
