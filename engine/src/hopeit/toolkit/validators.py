"""
Provided validators for fields in dataclasses
"""
import re
from asyncio import iscoroutine
from typing import Optional, Any, Dict, Callable, Awaitable, Union

from hopeit.dataobjects.validation import Validator, AsyncValidator

__all__ = ['same_as', 'not_same_as', 'in_range', 'pattern', 'non_empty_str', 'custom_eval']

# pylint: disable=arguments-differ


class NonEmptyStr(Validator):
    """
    Checks value of current field is not an empty string, after removing trailing space
    """
    def expr(self, *args, obj: Any, field: str, value: Any) -> bool:
        return value.strip(' ') != ''

    def msg(self, *args, obj: Any, field: str, value: Any) -> Optional[str]:
        return f"{field} must not be empty"

    def extra(self, *args, obj: Any, field: str, value: Any) -> Dict[str, Any]:
        return {}


non_empty_str = NonEmptyStr.build()


class SameAs(Validator):
    """
    Checks value of current field is equal to the value of `other_field`
    """
    def expr(self, other_field: str, obj: Any, field: str, value: Any) -> bool:  # type: ignore
        return value == getattr(obj, other_field)

    def msg(self, other_field: str, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"{field} must be the same as {other_field}"

    def extra(self, other_field: str, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'other_field': other_field, 'other_value': getattr(obj, other_field)}


same_as = SameAs.build()


class NotSameAs(Validator):
    """
    Checks value of current field is not equal to the value of `other_field`
    """
    def expr(self, other_field: str, obj: Any, field: str, value: Any) -> bool:  # type: ignore
        return value != getattr(obj, other_field)

    def msg(self, other_field: str, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"{field} must not be the same as {other_field}"

    def extra(self, other_field: str, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'other_field': other_field, 'other_value': getattr(obj, other_field)}


not_same_as = NotSameAs.build()


# noqa: W0221:
class InRange(Validator):
    """
    Checks that an int field is in the interval [min_value..max_value] (inclusive)
    value parameter is converted to int
    """

    def expr(self, min_value: int, max_value: int, obj: Any, field: str, value: Any) -> bool:  # type: ignore
        return min_value <= int(value) <= max_value

    def msg(self, min_value: int, max_value: int, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"{field}={value} not in range {min_value}-{max_value}"

    def extra(self, min_value: int, max_value: int, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'min_value': min_value, 'max_value': max_value}


in_range = InRange.build()


# noqa: W0221:
class Pattern(Validator):
    """
    Checks that a str field conforms to a regular expression `regex`
    """
    def expr(self, regex: str, obj: Any, field: str, value: Any) -> bool:  # type: ignore
        return re.compile(regex).match(value) is not None

    def msg(self, regex: str, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"{field}={value} does not conform to pattern='{regex}'"

    def extra(self, regex: str, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'regex': regex}


pattern = Pattern.build()


class CustomEval(AsyncValidator):
    """
    Executes a provided function sending obj, field and value. func may be async.
    """
    async def expr(self,  # type: ignore
                   func: Callable[[Any, str, Any], Union[bool, Awaitable[Any]]],  # type: ignore
                   obj: Any, field: str, value: Any) -> bool:  # type: ignore
        res = func(obj, field, value)
        if iscoroutine(res):
            return await res  # type: ignore
        assert isinstance(res, bool)
        return res

    def msg(self, func, obj: Any, field: str, value: Any) -> Optional[str]:  # type: ignore
        return f"validation failed when applying function={func.__name__} to {field}={value}"

    def extra(self, func, obj: Any, field: str, value: Any) -> Dict[str, Any]:  # type: ignore
        return {'function': func.__name__}


custom_eval = CustomEval.build()
