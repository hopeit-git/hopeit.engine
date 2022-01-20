"""
Simple Example: Download Something Streamed
-------------------------------------------
Download image file strimed from filesystem.
The PostprocessHook return the requested resource as stream using `create_stream_response`.
"""
from dataclasses import dataclass
import os

from hopeit.dataobjects import BinaryDownload
from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook


__steps__ = ['find_image']


@dataclass
class ImagePng(BinaryDownload):
    content_type = 'image/png'
    file_name: str
    file_path: str


__api__ = event_api(
    query_args=[("file_name", str, "return file name, try with hopeit-iso.png")],
    responses={
        200: (ImagePng, "Return requested image file"),
        400: (str, "Image file not found")
    }
)

logger, extra = app_extra_logger()


async def find_image(payload: None, context: EventContext, *, file_name: str) -> ImagePng:
    """
    Find image file to be streamd
    """
    src_file_path = f"./apps/examples/simple-example/resources/{file_name}"
    return ImagePng(file_name=file_name, file_path=src_file_path)


async def __postprocess__(img_file: ImagePng, context: EventContext, response: PostprocessHook) -> str:
    if os.path.isfile(img_file.file_path):
        content_length = os.path.getsize(img_file.file_path)
        stream = await response.create_stream_response(filename=img_file.file_name,
                                                       content_type=img_file.content_type,
                                                       content_length=content_length)
        with open(img_file.file_path, 'rb') as f:
            chunk = f.read(2 ** 16)
            while chunk:
                await stream.write(chunk)
                chunk = f.read(2 ** 16)
        return stream

    response.set_status(400)
    return f"File {img_file.file_name} not found"
