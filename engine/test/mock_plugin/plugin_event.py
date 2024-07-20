from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext, PostprocessHook

__steps__ = ["entry_point"]

logger, extra = app_extra_logger()

initialized = False


async def __init_event__(context: EventContext):
    global initialized
    logger.info(context, "INIT")
    initialized = True


async def entry_point(payload: None, context: EventContext) -> str:
    logger.info(context, "plugin_event.entry_point")
    assert initialized
    return "PluginEvent"


async def __postprocess__(payload: str, context: EventContext, *, response: PostprocessHook) -> str:
    response.set_header("PluginHeader", "PluginHeaderValue")
    response.set_cookie("PluginCookie", "PluginCookieValue")
    response.set_status(999)
    return "PluginEvent.postprocess"
