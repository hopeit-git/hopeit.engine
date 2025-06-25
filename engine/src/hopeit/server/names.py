"""
Convenience methods to normalize endpoint names, module names from configuration
"""

import re

__all__ = ["route_name", "module_name", "auto_path", "auto_path_prefixed"]


def route_name(*args: str) -> str:
    return "/" + "/".join(spinalcase(re.sub("\\.", "x", name)) for name in args)


def module_name(*args: str) -> str:
    return ".".join(re.sub("\\$", ".", snakecase(re.sub("\\.", "$", name))) for name in args)


def auto_path(*args: str) -> str:
    return ".".join(snakecase(re.sub("\\.", "x", name)) for name in args)


def auto_path_prefixed(prefix, *args: str) -> str:
    return ".".join([prefix, *(snakecase(re.sub("\\.", "x", name)) for name in args)])


def snakecase(string: str) -> str:
    """Convert string into snake_case."""

    def convert_word(matched) -> str:
        return "_" + matched.group(0).lower()

    if not string:
        return string
    string = re.sub(r"[\-\.\s]", "_", string)
    return string[0].lower() + re.sub(r"[A-Z]", convert_word, string[1:])


def spinalcase(string: str) -> str:
    """Convert string into spinal-case."""
    return snakecase(string).replace("_", "-")


def titlecase(string: str) -> str:
    """Convert string into Title Case."""
    if not string:
        return string
    return " ".join([word[0].upper() + word[1:] for word in snakecase(string).split("_")])
