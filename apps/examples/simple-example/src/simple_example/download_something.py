"""
Simple Example: Download Something
-----------------------------------------
Download image file. The PostprocessHook return the requested file as stream.
"""
from dataclasses import dataclass
import os
import shutil

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
    query_args=[("file_name", str, "return file name, try with something.png")],
    responses={
        200: (ImagePng, "Return requested image file"),
        400: (str, "Image file not found")
    }
)

logger, extra = app_extra_logger()


async def find_image(payload: None, context: EventContext, *, file_name: str) -> str:
    """
    Find image file
    """
    return file_name
    # src_file_path = f"./apps/examples/simple-example/resources/{file_name}"
    # tgt_file_path = os.path.join(str(context.env['fs']['data_path']), file_name)
    # try:
    #     shutil.copy(src_file_path, tgt_file_path)
    # except IOError as msg:
    #     print(f"Unable to copy file. {msg}")

    # return ImagePng(file_name=file_name, file_path=tgt_file_path)


async def __postprocess__(img_file: str,
                          context: EventContext,
                          response: PostprocessHook) -> str:

    # if os.path.isfile(img_file.file_path):
    #     response.set_header('Content-Disposition',
    #                         f"attachment; filename={img_file.file_name}")
    #     response.set_content_type(img_file.content_type)
    #     response.set_file_response(img_file.file_path)
    #     return f"File {img_file.file_name}"

    stream = await response.create_stream_response("example_file.txt", content_type="application/text", content_length=0)
    with open("./apps/examples/simple-example/resources/example_file.txt") as f:
        data = f.readline();
        while data:
            await stream.write(data.encode())
            data = f.readline()

    return stream
