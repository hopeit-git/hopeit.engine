"""
Simple Example: Download Something Streamed
-------------------------------------------
Download streamd created content as file.
The PostprocessHook return the requested resource as stream using `prepare_stream_response`.
"""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import BinaryDownload, dataclass

__steps__ = ["get_streamed_data"]


@dataclass
class SomeFile(BinaryDownload):
    file_name: str


__api__ = event_api(
    query_args=[("file_name", str, "expected return file name")],
    responses={200: (SomeFile, "Return content with filename=`file_name`")},
)


async def get_streamed_data(payload: None, context: EventContext, *, file_name: str) -> SomeFile:
    """
    Prepare output file name to be streamd
    """
    return SomeFile(file_name=file_name)


async def __postprocess__(
    file: SomeFile, context: EventContext, response: PostprocessHook
) -> SomeFile:
    """
    Stream 50 MB of binary content:
    """
    line = ("x" * 1024 * 1024).encode()
    response_length = 50 * len(line)
    stream_response = await response.prepare_stream_response(
        context,
        content_disposition=f'attachment; filename="{file.file_name}"',
        content_type=file.content_type,
        content_length=response_length,
    )

    for _ in range(50):
        await stream_response.write(line)
    return file
