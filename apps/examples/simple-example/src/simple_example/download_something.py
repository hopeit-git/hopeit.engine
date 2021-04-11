"""
Simple Example: Download Something
-----------------------------------------
Download image file. The PostprocessHook return the requested file as stream.
"""
from dataclasses import dataclass
from pathlib import Path
import os

from hopeit.dataobjects import BinaryAttachment
from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook


__steps__ = ['find_image']


@dataclass
class ImagePng(BinaryAttachment):
    content_type = 'image/png'


__api__ = event_api(
    responses={
        200: (ImagePng, "Return requested image file"),
        400: (str, "Image file not found")
    }
)

logger, extra = app_extra_logger()


async def find_image(payload: None, context: EventContext) -> str:
    """
    Finde image file
    """
    file_name = f"{Path(__file__).parent.absolute()}/../../resources/hopeit-iso.png"

    return file_name


async def __postprocess__(file_path: str,
                          context: EventContext,
                          response: PostprocessHook) -> str:

    if os.path.isfile(file_path):
        response.set_header('Content-Disposition',
                            "attachment; filename=hopeit-iso.png")
        response.set_header("Content-Type", 'image/png')
        response.set_file_response(file_path)
        return file_path

    response.set_status(400)
    return f"File {file_path} not found"
