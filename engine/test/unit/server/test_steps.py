from typing import Union, Optional

import pytest  # type: ignore
import importlib

from hopeit.app.config import (
    AppConfig,
    AppDescriptor,
    EventDescriptor,
    EventType,
    ReadStreamDescriptor,
    StreamQueueStrategy,
    WriteStreamDescriptor,
)
from hopeit.app.context import EventContext
from hopeit.app.events import Spawn, SHUFFLE
from hopeit.server.events import get_event_settings
from hopeit.server.imports import find_event_handler
from hopeit.server.steps import (
    extract_module_steps,
    extract_postprocess_handler,
    extract_input_type,
    execute_steps,
    invoke_single_step,
    effective_steps,
    split_event_stages,
    CollectorStepsDescriptor,
)
from mock_app import MockData, MockResult, mock_collector  # type: ignore
from mock_app import mock_app_config  # type: ignore
from copy import deepcopy


def test_extract_event_steps():
    impl = importlib.import_module("mock_app.mock_event")
    f1 = getattr(impl, "entry_point")
    f2 = getattr(impl, "handle_ok_case")
    f3 = getattr(impl, "handle_special_case")
    steps = extract_module_steps(impl)
    assert steps == [
        ("entry_point", (f1, None, Union[MockData, str], False)),
        ("handle_ok_case", (f2, MockData, str, False)),
        ("handle_special_case", (f3, str, str, False)),
    ]


def test_effective_steps():
    impl = importlib.import_module("mock_app.mock_event")
    f1 = getattr(impl, "entry_point")
    f2 = getattr(impl, "handle_ok_case")
    f3 = getattr(impl, "handle_special_case")
    module_steps = [
        ("entry_point", (f1, None, Union[MockData, str], False)),
        ("handle_ok_case", (f2, MockData, str, False)),
        ("handle_special_case", (f3, str, str, False)),
    ]
    steps = effective_steps("mock_event", module_steps)
    assert steps == [
        (0, "entry_point", (f1, None, Union[MockData, str], False)),
        (1, "handle_ok_case", (f2, MockData, str, False)),
        (2, "handle_special_case", (f3, str, str, False)),
    ]


def test_extract_event_steps_with_shuffle():
    impl = importlib.import_module("mock_app.mock_shuffle_event")
    f1 = getattr(impl, "produce_messages")
    f2 = getattr(impl, "consume_stream")
    f3 = getattr(impl, "generate_default")
    steps = extract_module_steps(impl)
    assert steps == [
        ("produce_messages", (f1, str, Spawn[MockData], True)),
        (SHUFFLE, None),
        ("consume_stream", (f2, MockData, Optional[MockResult], False)),
        ("generate_default", (f3, None, MockResult, False)),
    ]


def test_effective_steps_shuffle_event():
    impl = importlib.import_module("mock_app.mock_shuffle_event")
    f1 = getattr(impl, "produce_messages")
    f2 = getattr(impl, "consume_stream")
    f3 = getattr(impl, "generate_default")
    module_steps = [
        ("produce_messages", (f1, str, Spawn[MockData], True)),
        (SHUFFLE, None),
        ("consume_stream", (f2, MockData, Optional[MockResult], False)),
        ("generate_default", (f3, None, MockResult, False)),
    ]
    steps = effective_steps("mock_shuffle_event", module_steps)
    assert steps == [(0, "produce_messages", (f1, str, Spawn[MockData], True))]
    steps = effective_steps("mock_shuffle_event$consume_stream", module_steps)
    assert steps == [
        (0, "consume_stream", (f2, MockData, Optional[MockResult], False)),
        (1, "generate_default", (f3, None, MockResult, False)),
    ]


def test_extract_postprocess_handler():
    impl = importlib.import_module("mock_app.mock_event")
    f1 = getattr(impl, "__postprocess__")
    pp_handler = extract_postprocess_handler(impl)
    assert pp_handler == (f1, str, str, False)


def test_extract_input_type_none():
    impl = importlib.import_module("mock_app.mock_event")
    datatype = extract_input_type(impl)
    assert datatype is None


def test_extract_input_type_preprocess():
    impl = importlib.import_module("mock_app.mock_post_preprocess")
    datatype = extract_input_type(impl)
    assert datatype is MockData


def test_extract_input_type_none_preprocess():
    impl = importlib.import_module("mock_app.mock_post_preprocess_no_datatype")
    datatype = extract_input_type(impl)
    assert datatype is None


def test_extract_input_type_dataclass():
    impl = importlib.import_module("mock_app.mock_post_event")
    datatype = extract_input_type(impl)
    assert datatype is MockData


def test_extract_input_type_builtin_type():
    impl = importlib.import_module("mock_app.mock_post_auth")
    datatype = extract_input_type(impl)
    assert datatype is str


def step1(payload: MockData, context: EventContext) -> MockData:
    return MockData(payload.value + " step1")


def step2(payload: MockData, context: EventContext) -> MockData:
    return MockData(payload.value + " step2")


def step3(payload: MockData, context: EventContext) -> MockData:
    return MockData(payload.value + " step3")


def step4(payload: MockData, context: EventContext) -> Union[MockData, str]:
    if payload.value.startswith("a"):
        return MockData(payload.value + " step4")
    else:
        return payload.value + " step4"


def step5a(payload: MockData, context: EventContext) -> MockResult:
    return MockResult(payload.value + " step5a")


def step5b(payload: str, context: EventContext) -> MockResult:
    return MockResult(payload + " step5b")


def step6(payload: MockResult, context: EventContext) -> MockResult:
    return MockResult(payload.value + " step6")


async def step_spawn(payload: None, context: EventContext, *, query_arg1: str) -> Spawn[MockData]:
    for i in range(3):
        yield MockData(query_arg1 + " " + str(i))


async def step_respawn(payload: MockData, context: EventContext) -> Spawn[MockData]:
    for j in range(3):
        yield MockData(payload.value + " respawn:" + str(j))


def test_context() -> EventContext:
    app_config = AppConfig(
        app=AppDescriptor(name="test_steps", version="test_version"),
        events={"test_steps": EventDescriptor(type=EventType.POST)},
    ).setup()
    return EventContext(
        app_config=app_config,
        plugin_config=app_config,
        event_name="test_steps",
        settings=get_event_settings(app_config.effective_settings, "test_steps"),
        track_ids={},
        auth_info={},
    )


@pytest.mark.asyncio
async def test_execute_linear_steps():
    steps = [
        (0, "step1", (step1, MockData, MockData, False)),
        (1, "step2", (step2, MockData, MockData, False)),
        (2, "step3", (step3, MockData, MockData, False)),
    ]
    async for result in execute_steps(
        steps=steps, payload=MockData("input"), context=test_context()
    ):
        assert result == MockData("input step1 step2 step3")


@pytest.mark.asyncio
async def test_execute_decision_steps():
    steps = [
        (0, "step1", (step1, MockData, MockData, False)),
        (1, "step2", (step2, MockData, MockData, False)),
        (2, "step3", (step3, MockData, MockData, False)),
        (3, "step4", (step4, MockData, Union[MockData, str], False)),
        (4, "step5a", (step5a, MockData, MockResult, False)),
        (5, "step5b", (step5b, str, MockResult, False)),
        (6, "step6", (step6, MockResult, MockResult, False)),
    ]
    async for result in execute_steps(steps=steps, payload=MockData("a"), context=test_context()):
        assert result == MockResult("a step1 step2 step3 step4 step5a step6")

    async for result in execute_steps(steps=steps, payload=MockData("b"), context=test_context()):
        assert result == MockResult("b step1 step2 step3 step4 step5b step6")


@pytest.mark.asyncio
async def test_execute_spawn_initial_steps():
    steps = [
        (0, "step_spawn", (step_spawn, None, Spawn[MockData], True)),
        (1, "step1", (step1, MockData, MockData, False)),
        (2, "step2", (step2, MockData, MockData, False)),
        (3, "step3", (step3, MockData, MockData, False)),
        (4, "step4", (step4, MockData, Union[MockData, str], False)),
        (5, "step5a", (step5a, MockData, MockResult, False)),
        (6, "step5b", (step5b, str, MockResult, False)),
        (7, "step6", (step6, MockResult, MockResult, False)),
    ]
    i = 0
    async for result in execute_steps(
        steps=steps, payload=None, context=test_context(), query_arg1="a"
    ):
        assert result == MockResult(f"a {i} step1 step2 step3 step4 step5a step6")
        i += 1
    assert i == 3

    i = 0
    async for result in execute_steps(
        steps=steps, payload=None, context=test_context(), query_arg1="b"
    ):
        assert result == MockResult(f"b {i} step1 step2 step3 step4 step5b step6")
        i += 1
    assert i == 3


@pytest.mark.asyncio
async def test_execute_multiple_spawn_steps():
    steps = [
        (0, "step_spawn", (step_spawn, None, Spawn[MockData], True)),
        (1, "step1", (step1, MockData, MockData, False)),
        (2, "step2", (step2, MockData, MockData, False)),
        (3, "step3", (step3, MockData, MockData, False)),
        (4, "step_respawn", (step_respawn, MockData, Spawn[MockData], True)),
        (5, "step4", (step4, MockData, Union[MockData, str], False)),
        (6, "step5a", (step5a, MockData, MockResult, False)),
        (7, "step5b", (step5b, str, MockResult, False)),
        (8, "step6", (step6, MockResult, MockResult, False)),
    ]
    i, j, count = 0, 0, 0
    async for result in execute_steps(
        steps=steps, payload=None, context=test_context(), query_arg1="a"
    ):
        assert result == MockResult(f"a {i} step1 step2 step3 respawn:{j} step4 step5a step6")
        i, j = i + 1 if j == 2 else i, j + 1 if j < 2 else 0
        count += 1
        assert count <= 9
    assert count == 9

    i, j, count = 0, 0, 0
    async for result in execute_steps(
        steps=steps, payload=None, context=test_context(), query_arg1="b"
    ):
        assert result == MockResult(f"b {i} step1 step2 step3 respawn:{j} step4 step5b step6")
        i, j = i + 1 if j == 2 else i, j + 1 if j < 2 else 0
        count += 1
        assert count <= 9
    assert count == 9


@pytest.mark.asyncio
async def test_invoke_single_step():
    result = await invoke_single_step(step1, payload=MockData("input"), context=test_context())
    assert result == MockData("input step1")


def test_split_event_stages(mock_app_config):
    impl = find_event_handler(
        app_config=mock_app_config,
        event_name="mock_shuffle_event",
        event_info=mock_app_config.events["mock_shuffle_event"],
    )
    event_info = mock_app_config.events["mock_shuffle_event"]
    stages = split_event_stages(
        mock_app_config.app,
        event_name="mock_shuffle_event",
        event_info=event_info,
        impl=impl,
    )
    assert stages == {
        "mock_shuffle_event": EventDescriptor(
            type=EventType.GET,
            read_stream=event_info.read_stream,
            write_stream=WriteStreamDescriptor(
                name="mock_app.test.mock_shuffle_event.produce_messages",
                queues=["AUTO"],
                queue_strategy=StreamQueueStrategy.PROPAGATE,
            ),
            auth=[],
        ),
        "mock_shuffle_event$consume_stream": EventDescriptor(
            type=EventType.STREAM,
            read_stream=ReadStreamDescriptor(
                name="mock_app.test.mock_shuffle_event.produce_messages",
                consumer_group="mock_app.test.mock_shuffle_event.consume_stream",
                queues=["AUTO"],
            ),
            write_stream=event_info.write_stream,
            auth=[],
        ),
    }


def test_split_event_stages_queues(mock_app_config):
    impl = find_event_handler(
        app_config=mock_app_config,
        event_name="mock_shuffle_event",
        event_info=mock_app_config.events["mock_shuffle_event"],
    )
    event_info = deepcopy(mock_app_config.events["mock_shuffle_event"])
    event_info.read_stream = ReadStreamDescriptor(
        name="test_read_stream", consumer_group="test_group", queues=["q1", "q2"]
    )
    event_info.write_stream = WriteStreamDescriptor(
        name="test_write_stream",
        queues=["q1", "q2"],
        queue_strategy=StreamQueueStrategy.PROPAGATE,
    )
    stages = split_event_stages(
        mock_app_config.app,
        event_name="mock_shuffle_event",
        event_info=event_info,
        impl=impl,
    )
    assert stages == {
        "mock_shuffle_event": EventDescriptor(
            type=EventType.GET,
            read_stream=event_info.read_stream,
            write_stream=WriteStreamDescriptor(
                name="mock_app.test.mock_shuffle_event.produce_messages",
                queues=["AUTO"],
                queue_strategy=StreamQueueStrategy.PROPAGATE,
            ),
            auth=[],
        ),
        "mock_shuffle_event$consume_stream": EventDescriptor(
            type=EventType.STREAM,
            read_stream=ReadStreamDescriptor(
                name="mock_app.test.mock_shuffle_event.produce_messages",
                consumer_group="mock_app.test.mock_shuffle_event.consume_stream",
                queues=["q1", "q2"],
            ),
            write_stream=event_info.write_stream,
            auth=[],
        ),
    }


def test_collector_steps_descriptor(mock_app_config):
    impl = find_event_handler(
        app_config=mock_app_config,
        event_name="mock_collector",
        event_info=mock_app_config.events["mock_collector"],
    )
    steps = extract_module_steps(impl)
    collector: CollectorStepsDescriptor = steps[0][0]
    assert isinstance(collector, CollectorStepsDescriptor)
    assert collector.steps == [
        ("step1", mock_collector.step1),
        ("step2", mock_collector.step2),
        ("step3", mock_collector.step3),
    ]
    assert collector.__name__ == "collector@step1"
    assert collector.input_type is MockData
    assert collector.step_names == ["step1", "step2", "step3"]
