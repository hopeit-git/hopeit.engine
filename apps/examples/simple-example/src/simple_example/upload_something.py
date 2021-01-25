from typing import Optional, List, Any
from dataclasses import dataclass, field

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PreprocessHook
from hopeit.dataobjects import dataobject

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
    uploaded_files: List[UploadedFile] = field(default_factory=list)



async def __preprocess__(payload: SomethingParams, context: Any, request: PreprocessHook) -> FileUploadInfo:
    result = FileUploadInfo()
    async for file in request.files():
        file_name = f"attachment-{payload.id}-{file.name}-{file.file_name}"
        with open(os.path.join('/tmp/upload_something', file_name), 'wb') as f:
            async for chunk in file.read_chunks():
                f.write(chunk)
        uploaded_file = UploadedFile(request.name, file_name, "tmp/upload_something", size=request.size)
        result.uploaded_files.append(uploaded_file)
    return result


async def create_items(payload: FileUploadInfo, context: EventContext, *, user: str) -> List[Something]:
    for item in payload.uploaded_files:
        logger.info(context, "Creating something from uploaded item...", extra=extra(
            file_id=item.file_id, user=user
        ))
        result = Something(
            id=item.file_id,
            user=User(id=user, name=user)
        )
    return result
