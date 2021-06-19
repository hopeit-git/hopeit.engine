"""
Log Reader service: watches log files and emit batches of Log entries to a stream
"""
import asyncio
from typing import Dict, List, Optional

from hopeit.app.context import EventContext
from hopeit.app.events import Spawn
from hopeit.app.logger import app_extra_logger
from hopeit.server.names import auto_path

from hopeit.log_streamer import LogReaderConfig, LogRawBatch, LogEntry, LogBatch, \
    LogFileHandler, start_observer

logger, extra = app_extra_logger()

__steps__ = ['process_log_data']


async def __service__(context: EventContext) -> Spawn[LogRawBatch]:  # pylint: disable=invalid-name
    config = LogReaderConfig.from_dict(context.env['log_reader'])  # type: ignore
    event_handler = LogFileHandler(config, context)
    logger.info(context, "Starting LogFileHandler...", extra=extra(
        logs_path=config.logs_path,
        checkpoint_path=config.checkpoint_path
    ))
    observer = start_observer(event_handler, config.logs_path)
    logger.info(context, "LogFileHandler started.")

    try:
        while True:
            batch = await event_handler.get_and_reset_batch()
            if len(batch) == 0:
                logger.info(context, "LogFileHandler returned empty batch. Sleeping...")
                await asyncio.sleep(config.batch_wait_interval_secs)
            else:
                for i in range(0, len(batch), config.batch_size):
                    yield LogRawBatch(data=batch[i: i + config.batch_size + 1])
                    await asyncio.sleep(config.batch_wait_interval_secs)
            event_handler.close_inactive_files()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
        logger.error(context, e)
    finally:
        observer.stop()
        observer.join()


def _parse_extras(extras: List[str]) -> Dict[str, str]:
    items = {}
    for entry in extras:
        entry = entry.strip('\n')
        if entry:
            xs = entry.split('=')
            if len(xs) == 2:
                k, v = entry.split('=')
                items[k] = v
    return items


async def _process_log_entry(entry: str, context: EventContext) -> Optional[LogEntry]:
    """
    Parses log line into a LogEntry

    Only log entries with START/DONE/FAILED message are included.
    (This behaviour can be changed if all lines should be processed)
    """
    try:
        xs = entry.split(' | ')
        if len(xs) >= 4:
            ts, app_info, msg, extras = xs[0], xs[2], xs[3], xs[4:]
            app_info_components = app_info.split(' ')
            if msg in {'START', 'DONE', 'FAILED'} and (len(app_info_components) >= 3):
                app_name, app_version, event_name, host, pid = app_info_components[:5]
                event = f"{auto_path(app_name, app_version)}.{event_name}"
                extra_items = _parse_extras(extras)
                return LogEntry(
                    ts=ts,
                    msg=msg,
                    app_name=app_name,
                    app_version=app_version,
                    event_name=event_name,
                    event=event,
                    extra=extra_items,
                    host=host,
                    pid=pid
                )
        return None
    except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
        logger.error(context, e)
        return None


async def process_log_data(payload: LogRawBatch, context: EventContext) -> Optional[LogBatch]:
    """
    Receives emitted batch of raw log lines from service handler, process and filter in order
    to emit processed batch to a stream.
    """
    config = LogReaderConfig.from_dict(context.env['log_reader'])  # type: ignore
    logger.info(context, "Processing batch of log entries...", extra=extra(batch_size=len(payload.data)))
    try:
        entries: List[LogEntry] = []
        for entry in payload.data:
            processed_entry = await _process_log_entry(entry, context)
            if processed_entry is not None:
                entries.append(processed_entry)  # type: ignore
        if len(entries) > 0:
            return LogBatch(entries=entries)
        logger.info("Filtered out all entries in batch.")
        return None
    except Exception as e:  # pylint: disable=broad-except  # pragma: no cover
        logger.error(context, e)
        return None
    finally:
        await asyncio.sleep(config.batch_wait_interval_secs)
