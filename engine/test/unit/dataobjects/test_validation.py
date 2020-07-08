import asyncio
from typing import Any, Optional, Dict

import pytest  # type: ignore
from dataclasses import dataclass

from hopeit.dataobjects.validation import Validator, Mode, validate, ValidationResult, AsyncValidator


# pylint: disable=arguments-differ


class Validator1(Validator):
    def expr(self, test_value: Any, obj: Any, field: str, value: Any) -> bool:  # type: ignore
        return value == test_value


class Validator2(Validator1):
    def msg(self, test_value: Any, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"{value} must be the same as {test_value}"


class Validator3(Validator2):
    def extra(self, test_value: Any, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'test_value': test_value}


class Validator4(AsyncValidator):
    async def expr(self, test_value: Any, obj: Any, field: str, value: Any) -> bool:  # type: ignore
        await asyncio.sleep(0.1)
        return value == test_value


class Validator5(Validator4):
    def msg(self, test_value: Any, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"{value} must be the same as {test_value}"

    def extra(self, test_value: Any, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'test_value': test_value}


validator1 = Validator1.build()
validator2 = Validator2.build()
validator3 = Validator3.build()
validator4 = Validator4.build()
validator5 = Validator5.build()


@dataclass
@validate(
    value1=validator1(1),
    value2=validator2(2),
    value3=validator3(3)
)
class Values1:
    value1: int
    value2: int
    value3: int


@dataclass
@validate(
    Mode.STRICT,
    value1=validator1(1),
    value2=validator2(2),
    value3=validator3(3)
)
class Values2:
    value1: int
    value2: int
    value3: int
    value4: int

    def __post_init__(self):
        self.value4 = 42


@dataclass
@validate(
    Mode.ON_CREATE,
    value1=validator1(1),
    value2=validator2(2),
    value3=validator3(3)
)
class Values3:
    value1: int
    value2: int
    value3: int
    value4: int

    def __post_init__(self):
        self.value4 = 42


@dataclass
@validate(
    Mode.ON_DEMAND,
    value1=validator1(1),
    value2=validator2(2),
    value3=validator3(3)
)
class Values4:
    value1: int
    value2: int
    value3: int


errors = {'value1': [ValidationResult(msg='Validator1: validation failed',
                                      extra={'type': 'Validator1', 'field': 'value1', 'value': 3})],
          'value2': [ValidationResult(msg='4 must be the same as 2',
                                      extra={'type': 'Validator2', 'field': 'value2', 'value': 4})],
          'value3': [ValidationResult(msg='5 must be the same as 3',
                                      extra={'type': 'Validator3', 'field': 'value3', 'value': 5,
                                             'test_value': 3})]}


def test_validate_default():
    ok = Values1(1, 2, 3)
    assert ok == Values1(1, 2, 3)
    assert ok.validation_errors() == {}

    with pytest.raises(ValueError):
        Values1(3, 4, 5)


def test_validate_strict():
    ok = Values2(1, 2, 3, 4)
    assert ok == Values2(1, 2, 3, 42)
    assert ok.validation_errors() == {}

    with pytest.raises(ValueError):
        Values2(3, 4, 5, 6)


def test_validate_on_create():
    ok = Values3(1, 2, 3, 4)
    assert ok == Values3(1, 2, 3, 42)
    assert ok.validation_errors() == {}

    not_ok = Values3(3, 4, 5, 6)
    assert not_ok.validation_errors() == errors
    assert not_ok == Values3(3, 4, 5, 42)

    not_ok.value1 = 1
    not_ok.value2 = 2
    not_ok.value3 = 3
    assert not_ok.validation_errors() == errors


def test_validate_on_demand():
    ok = Values4(1, 2, 3)
    assert ok == Values4(1, 2, 3)
    assert ok.validation_errors() == {}

    not_ok = Values4(3, 4, 5)
    assert not_ok.validation_errors() == errors

    not_ok.value1 = 1
    not_ok.value2 = 2
    not_ok.value3 = 3
    assert not_ok.validation_errors() == {}

    not_ok.value1 = 3
    assert not_ok.validation_errors()['value1'] == errors['value1']


@dataclass
@validate(
    'Async',  # same as Mode.ASYNC
    value1=validator4(42),
    value2=validator5(42)
)
class Values5:
    value1: int
    value2: int


@pytest.mark.asyncio
async def test_validate_async():
    ok = Values5(42, 42)
    assert ok == Values5(42, 42)
    assert await ok.validation_errors() == {}

    not_ok = Values5(24, 24)
    assert await not_ok.validation_errors() == \
        {'value1': [ValidationResult(msg='Validator4: validation failed',
                                     extra={'type': 'Validator4', 'field': 'value1', 'value': 24})],
         'value2': [ValidationResult(msg='24 must be the same as 42',
                                     extra={'type': 'Validator5', 'field': 'value2', 'value': 24,
                                            'test_value': 42})]}
