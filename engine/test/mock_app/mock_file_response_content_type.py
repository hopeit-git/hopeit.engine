from pathlib import Path
from dataclasses import dataclass
from hopeit.app.api import event_api
from hopeit.dataobjects import BinaryDownload
from hopeit.app.context import EventContext, PostprocessHook

__steps__ = ['create_file']


@dataclass
class ImagePng(BinaryDownload):
    content_type = 'image/png'
    file_name: str
    file_path: str


__api__ = event_api(
    summary="Test app file response",
    query_args=[('file_name', str, "File Name")],
    responses={
        200: (ImagePng, "")

    }
)


async def create_file(payload: None, context: EventContext, file_name: str) -> ImagePng:
    path = Path("/tmp") / file_name
    img_file = ImagePng(file_name=file_name, file_path=path)
    path = path.absolute()
    with open(path, 'w') as f:
        f.write(b'mock_file_response test file_response')
    return img_file


async def __postprocess__(img_file: ImagePng,
                          context: EventContext, *,
                          response: PostprocessHook) -> str:
    response.set_header("Content-Disposition", f"attachment; filename={img_file.file_name}")
    response.set_header("Content-Type", img_file.content_type)
    response.set_file_response(path=img_file.file_path)
    return img_file.file_name
