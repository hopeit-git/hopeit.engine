"""
Server error handling convenience module
"""
import traceback
import json
import urllib.parse
from dataclasses import dataclass
from typing import List

from hopeit.dataobjects import dataobject

__all__ = ['ErrorInfo',
           'format_exc',
           'json_exc']


@dataobject
@dataclass
class ErrorInfo:
    """
    Error information to be returned in failed responses
    """
    msg: str
    tb: List[str]

    @staticmethod
    def from_exception(e: BaseException):
        return ErrorInfo(
            msg=str(e),
            tb=traceback.format_exception_only(type(e), e)
        )


def format_exc(e: Exception) -> List[str]:
    traceback.print_exception(None, e, e.__traceback__)
    return traceback.format_exception(None, e, e.__traceback__)


def json_exc(e: Exception) -> str:
    return urllib.parse.quote(
        json.dumps(format_exc(e))
    )
