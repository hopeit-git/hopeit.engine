"""
Simple Example: Upload Something
-----------------------------------------
Uploads file using multipart upload support. Returns metadata Something object.
```
"""
from typing import Optional, List, Any
from dataclasses import dataclass, field
import os
from pathlib import Path

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import dataobject, BinaryAttachment
from hopeit.toolkit.web import save_multipart_attachment

from model import Something, User


__steps__ = ['create_items']

__api__ = event_api(
    summary="Simple Example: Multipart Upload files",
    description="Upload files using Multipart form request",
    query_args=[('something_id', str)],
    fields=[('id', str), ('user', str), ('attachment', BinaryAttachment)],
    responses={
        200: (List[Something], 'list of created Something objects')
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
    uploaded_files: List[UploadedFile] = field(default_factory=list)


async def __init_event__(context: EventContext):
    save_path = Path(context.env['upload_something']['save_path'])
    os.makedirs(save_path, exist_ok=True)


async def __preprocess__(payload: None, context: EventContext, request: PreprocessHook) -> FileUploadInfo:
    uploaded_files = []
    save_path = Path(context.env['upload_something']['save_path'])
    chunk_size = int(context.env['upload_something']['chunk_size'])
    async for file_hook in request.files():
        file_name = f"{file_hook.name}-{file_hook.file_name}"
        path = save_path / file_name
        logger.info(context, f"Saving {path}...")
        await save_multipart_attachment(file_hook, path, chunk_size=chunk_size)
        uploaded_file = UploadedFile(file_hook.name, file_name, save_path, size=file_hook.size)
        uploaded_files.append(uploaded_file)
    args = await request.parsed_args()
    return FileUploadInfo(id=args['id'], user=args['user'], uploaded_files=uploaded_files)


async def create_items(payload: FileUploadInfo, context: EventContext, *, something_id: str) -> List[Something]:
    result = []
    for item in payload.uploaded_files:
        logger.info(context, "Creating something from uploaded item...", extra=extra(
            file_id=item.file_id, user=payload.user, something_id=something_id, size=item.size
        ))
        result.append(Something(
            id=something_id,
            user=User(id=payload.id, name=payload.user)
        ))
    return result
