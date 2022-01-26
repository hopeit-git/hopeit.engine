from aiohttp import content_disposition_filename
from hopeit.app.context import EventContext, PostprocessHook

__steps__ = ["create_file"]


async def create_file(payload: None, context: EventContext, file_name: str) -> str:
    return file_name


async def __postprocess__(
    file_name: str, context: EventContext, *, response: PostprocessHook
) -> str:
    data = b"TestDataTestData"
    file_size = len(data) * 3
    stream = await response.prepare_stream_response(
        context,
        content_disposition=f'attachment; filename="{file_name}"',
        content_type="application/octet-stream",
        content_length=file_size,
    )

    for _ in range(3):
        await stream.write(data)
    return stream
