"""
Simple Example: Upload Something
--------------------------------------------------------------------
Uploads and save a file using multipart form data
"""
from typing import Optional

from hopeit.app.api import event_api
from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from hopeit.toolkit.storage.fs import FileStorage

from model import Something, User, SomethingParams


__steps__ = ['create_something', 'save']

__api__ = event_api(
    title="Simple Example: Upload Something with files",
    payload=(SomethingParams, "provide `id` and `user` to create Something"),
    # fields=[("user", str), ("attachment", MultipartUploadFile)],
    responses={
        200: (str, 'path where object is saved')
    }
)


logger, extra = app_extra_logger()
fs: Optional[FileStorage] = None


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


async def __init_event__(context):
    global fs
    if fs is None:
        fs = FileStorage(path=str(context.env['fs']['data_path']))


async def __preprocess__(payload: SomethingParams, context: Any, request: PreprocessHook) -> FileUploadInfo:
    # save file to fs
    async for file in request.files():
        file_name = f"attachment-{payload.id}-{file.name}-{file.file_name}"
        with open(os.path.join('/tmp/upload_something', file_name), 'wb') as f:
            async for chunk in file.read_chunks():
                f.write(chunk)
    uploaded_file = UploadedFile(request.name, file_name, "tmp/upload_something", size=request.size)
    payload.uploaded_files.append(uploaded_file)
    return payload


async def create_something(payload: UploadedFile, context: EventContext, *, user: str) -> Something:
    logger.info(context, "Creating something...", extra=extra(
        payload_id=payload.id, user=user
    ))
    result = Something(
        id=payload.file_id,
        user=User(id=user, name=user)
    )
    return result


async def save(payload: Something, context: EventContext) -> str:
    """
    Attempts to validate `payload` and save it to disk in json format

    :param payload: Something object
    :param context: EventContext
    """
    assert fs
    logger.info(context, "saving", extra=extra(something_id=payload.id, path=fs.path))
    return await fs.store(payload.id, payload)
