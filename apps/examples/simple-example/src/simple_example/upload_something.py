"""
Simple Example: Upload Something
-----------------------------------------
Uploads file using multipart upload support. Returns metadata Something object.
```
"""
from typing import List, Union

import os
from pathlib import Path

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import dataclass, dataobject, field, BinaryAttachment
from hopeit.dataobjects.payload import Payload
from hopeit.toolkit.web import save_multipart_attachment

from model import Something


__steps__ = ['create_items']

__api__ = event_api(
    summary="Simple Example: Multipart Upload files",
    description="Upload files using Multipart form request",
    query_args=[('something_id', str)],
    fields=[('id', str), ('user', str), ('attachment', BinaryAttachment), ('object', Something)],
    responses={
        200: (List[Something], 'list of created Something objects'),
        400: (str, "Missing or invalid fields")
    }
)


logger, extra = app_extra_logger()


@dataobject
@dataclass
class UploadedFile:
    file_id: str
    file_name: str
    saved_path: str
    size: int


@dataobject
@dataclass
class FileUploadInfo:
    id: str
    user: str
    object: Something
    uploaded_files: List[UploadedFile] = field(default_factory=list)


async def __init_event__(context: EventContext):
    save_path = Path(str(context.env['upload_something']['save_path']))
    os.makedirs(save_path, exist_ok=True)


# pylint: disable=invalid-name
async def __preprocess__(payload: None, context: EventContext, request: PreprocessHook,
                         *, something_id: str) -> Union[str, FileUploadInfo]:
    uploaded_files = []
    save_path = Path(str(context.env['upload_something']['save_path']))
    chunk_size = int(context.env['upload_something']['chunk_size'])
    async for file_hook in request.files():
        file_name = f"{file_hook.name}-{file_hook.file_name}"
        path = save_path / file_name
        logger.info(context, f"Saving {path}...")
        await save_multipart_attachment(file_hook, path, chunk_size=chunk_size)
        uploaded_file = UploadedFile(file_hook.name, file_name, save_path.as_posix(), size=file_hook.size)
        uploaded_files.append(uploaded_file)
    args = await request.parsed_args()
    if not all(x in args for x in ('id', 'user', 'attachment', 'object')):
        request.status = 400
        return "Missing required fields"
    something_obj = Payload.parse_form_field(args['object'], Something)
    return FileUploadInfo(id=args['id'], user=args['user'], object=something_obj, uploaded_files=uploaded_files)


async def create_items(payload: FileUploadInfo, context: EventContext, *, something_id: str) -> List[Something]:
    """
    Create Something objects to be returned for each uploaded file
    """
    result = []
    for item in payload.uploaded_files:
        logger.info(context, "Creating something from uploaded item...", extra=extra(
            file_id=item.file_id, user=payload.user, something_id=something_id, size=item.size
        ))
        result.append(Something(
            id=item.file_id,
            user=payload.object.user
        ))
    return result
