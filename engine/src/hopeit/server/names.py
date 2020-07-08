"""
Convenience methods to normalize endpoint names, module names from configuration
"""
import re

from stringcase import spinalcase, snakecase  # type: ignore

__all__ = ['route_name',
           'module_name',
           'auto_path',
           'auto_path_prefixed']


def route_name(*args: str) -> str:
    return '/' + '/'.join(spinalcase(re.sub('\\.', 'x', name)) for name in args)


def module_name(*args: str) -> str:
    return '.'.join(
        re.sub('\\$', '.', snakecase(re.sub('\\.', '$', name)))
        for name in args)


def auto_path(*args: str) -> str:
    return '.'.join(snakecase(re.sub('\\.', 'x', name)) for name in args)


def auto_path_prefixed(prefix, *args: str) -> str:
    return '.'.join([
        prefix,
        *(snakecase(re.sub('\\.', 'x', name)) for name in args)
    ])
