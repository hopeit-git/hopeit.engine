from pathlib import Path

from hopeit.app.context import EventContext, PostprocessHook

__steps__ = ['create_file']


async def create_file(payload: None, context: EventContext, file_name: str) -> str:
    path = Path("/tmp") / file_name
    path = path.absolute()
    with open(path, 'w') as f:
        f.write('mock_file_response test file_response')
    return str(path)


async def __postprocess__(path: str,
                          context: EventContext, *,
                          response: PostprocessHook) -> str:
    file_name = Path(path).name
    response.set_header("Content-Disposition", f"attachment; filename={file_name}")
    response.set_header("Content-Type", 'text/plain')
    response.set_file_response(path=path)
    return path
