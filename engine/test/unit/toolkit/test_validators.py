import asyncio
from typing import Set
from dataclasses import dataclass

import pytest  # type: ignore

from hopeit.dataobjects.validation import Mode, validate, ValidationResult
from hopeit.toolkit.validators import same_as, not_same_as, in_range, pattern, non_empty_str, custom_eval


@dataclass
@validate(Mode.ON_DEMAND,
          a=same_as('b'),
          c=not_same_as('d'),
          e=in_range(1, 10),
          f=(pattern('^[0-9]*$'), non_empty_str()))
class Values:
    a: int
    b: int
    c: int
    d: int
    e: int
    f: str


def test_same_as():
    v = Values(1, 1, 3, 4, 5, '6')
    assert v.validation_errors() == {}

    v.b = 2
    assert v.validation_errors() == \
        {'a': [ValidationResult(msg='a must be the same as b',
                                extra={'type': 'SameAs', 'field': 'a', 'value': 1, 'other_field': 'b',
                                       'other_value': 2})]}


def test_not_same_as():
    v = Values(1, 1, 3, 4, 5, '6')
    assert v.validation_errors() == {}

    v.d = 3
    assert v.validation_errors() == \
        {'c': [ValidationResult(msg='c must not be the same as d',
                                extra={'type': 'NotSameAs', 'field': 'c', 'value': 3, 'other_field': 'd',
                                       'other_value': 3})]}


def test_in_range():
    v = Values(1, 1, 3, 4, 5, '6')
    assert v.validation_errors() == {}
    v.e = 1
    assert v.validation_errors() == {}
    v.e = 10
    assert v.validation_errors() == {}
    v.e = 0
    assert v.validation_errors() == \
        {'e': [ValidationResult(msg='e=0 not in range 1-10',
                                extra={'type': 'InRange', 'field': 'e', 'value': 0, 'min_value': 1,
                                       'max_value': 10})]}
    v.e = 11
    assert v.validation_errors() == \
        {'e': [ValidationResult(msg='e=11 not in range 1-10',
                                extra={'type': 'InRange', 'field': 'e', 'value': 11, 'min_value': 1,
                                       'max_value': 10})]}


def test_pattern():
    v = Values(1, 1, 3, 4, 5, '01234567890')
    assert v.validation_errors() == {}

    v.f = "a"
    assert v.validation_errors() == \
        {'f': [ValidationResult(msg="f=a does not conform to pattern='^[0-9]*$'",
                                extra={'type': 'Pattern', 'field': 'f', 'value': 'a', 'regex': '^[0-9]*$'})]}

    v.f = "a1b"
    assert v.validation_errors() == \
        {'f': [ValidationResult(msg="f=a1b does not conform to pattern='^[0-9]*$'",
                                extra={'type': 'Pattern', 'field': 'f', 'value': 'a1b', 'regex': '^[0-9]*$'})]}


def test_non_empty():
    v = Values(1, 1, 3, 4, 5, '01234567890')
    assert v.validation_errors() == {}

    v.f = ""
    assert v.validation_errors() == \
        {'f': [ValidationResult(msg='f must not be empty', extra={'type': 'NonEmptyStr', 'field': 'f', 'value': ''})]}

    v.f = " "
    assert v.validation_errors() == \
        {'f': [
            ValidationResult(msg="f=  does not conform to pattern='^[0-9]*$'",
                             extra={'type': 'Pattern', 'field': 'f', 'value': ' ', 'regex': '^[0-9]*$'}),
            ValidationResult(msg='f must not be empty', extra={'type': 'NonEmptyStr', 'field': 'f', 'value': ' '})
        ]}


class AsyncDatabase:
    data: Set[str] = set()

    @staticmethod
    async def insert(field, value):
        await asyncio.sleep(0.1)
        AsyncDatabase.data.add(value)

    @staticmethod
    async def exists(field, value) -> bool:
        await asyncio.sleep(0.1)
        return value not in AsyncDatabase.data


async def exists_in_db(obj, field, value) -> bool:
    return await AsyncDatabase.exists(field, value)


def is_valid_value(obj, field, value) -> bool:
    return len(value) == 2   # Any arbitrary check


@dataclass
@validate(Mode.ASYNC,
          a=(custom_eval(is_valid_value), custom_eval(exists_in_db)))
class CustomEvalValues:
    a: str


@pytest.mark.asyncio
async def test_custom_eval():
    AsyncDatabase.data = set()
    v = CustomEvalValues('42')
    assert await v.validation_errors() == {}
    await AsyncDatabase.insert('a', '42')

    assert await v.validation_errors() == \
        {'a': [ValidationResult(msg='validation failed when applying function=exists_in_db to a=42',
                                extra={'type': 'CustomEval', 'field': 'a', 'value': '42', 'function': 'exists_in_db'})]}

    v.a = '420'
    assert await v.validation_errors() == \
        {'a': [ValidationResult(msg='validation failed when applying function=is_valid_value to a=420',
                                extra={'type': 'CustomEval', 'field': 'a', 'value': '420',
                                       'function': 'is_valid_value'})]}

    v.a = '43'
    assert await v.validation_errors() == {}
    AsyncDatabase.data = set()
