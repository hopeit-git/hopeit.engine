"""
Special handled exceptions to return specific response status.
All other exceptions will return 500 (Internal Server Error)
"""
__all__ = ['BadRequest',
           'Unauthorized']

from hopeit.server import errors


class BadRequest(BaseException):
    """
    Exception that will return BadRequest (400) response in endpoint
    """
    ErrorInfo = errors.ErrorInfo  # pylint: disable=invalid-name


class Unauthorized(BaseException):
    """
    Exception that will return Unauthorized (401) response in endpoint
    """
    ErrorInfo = errors.ErrorInfo  # pylint: disable=invalid-name
