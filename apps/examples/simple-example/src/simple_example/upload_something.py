"""
Simple Example: Upload Something
-----------------------------------------
WIP
Test with
```
curl -F "user=test" -F "file1=@some_file.big" -F "file2=@some_file2.big" -H "Content-Type:multipart/form-data" "localhost:8020/api/simple-example/1x0/upload-something?qa=yes"

```
"""
from typing import Optional, List, Any
from dataclasses import dataclass, field
import os
from pathlib import Path

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import dataobject
from hopeit.toolkit.web import save_multipart_file

from model import Something, User, SomethingParams


__steps__ = ['create_items']

__api__ = event_api(
    title="Simple Example: Upload Something with files",
    payload=(SomethingParams, "provide `id` and `user` to create Something"),
    # fields=[("user", str), ("attachment", MultipartUploadFile)],
    responses={
        200: (str, 'path where object is saved')
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
    user: str
    uploaded_files: List[UploadedFile] = field(default_factory=list)


async def __init_event__(context: EventContext):
    save_path = Path(context.env['upload_something']['save_path'])
    os.makedirs(save_path, exist_ok=True)


async def __preprocess__(payload: None, context: EventContext, request: PreprocessHook) -> FileUploadInfo:
    result = FileUploadInfo("no-user")
    save_path = Path(context.env['upload_something']['save_path'])
    chunk_size = int(context.env['upload_something']['chunk_size'])
    async for file_hook in request.files():
        file_name = f"attachment-{file_hook.name}-{file_hook.file_name}"
        await save_multipart_file(file_hook, save_path / file_name, chunk_size=chunk_size)
        uploaded_file = UploadedFile(file_hook.name, file_name, save_path, size=file_hook.size)
        result.uploaded_files.append(uploaded_file)
    result.user = (await request.parsed_args())['user']
    return result


async def create_items(payload: FileUploadInfo, context: EventContext, *, qa: str) -> List[Something]:
    result = []
    for item in payload.uploaded_files:
        logger.info(context, "Creating something from uploaded item...", extra=extra(
            file_id=item.file_id, user=payload.user, qa=qa, size=item.size
        ))
        result.append(Something(
            id=item.file_id,
            user=User(id=payload.user, name=item.file_name)
        ))
    return result
