"""
Support to add validation to dataclasses
"""
from asyncio import iscoroutine
from collections import defaultdict
from functools import partial
from enum import Enum
from typing import Optional, Any, Iterable, NamedTuple, Union, Dict


class Validator:
    """
    Abstract class to be extended to implement custom validators for dataclasses fields
    A validator can be created subclassing Validator, implementing expr() method at least,
    and calling .build() to get an instance that can be used in the @validate decorator
    when applied to dataclasses.
    """

    @property
    def name(self) -> str:
        """
        Returns the name of the validator, using the class name implementing it
        """
        return type(self).__name__

    def expr(self, *args, obj: Any, field: str, value: Any) -> bool:
        """
        A function implementing a boolean expression that will be applied to fields
        :param args: custom validator arguments, not named
        :param obj: dataobject where this validation is applied to
        :param field: field being validated
        :param value: value of the field
        :return: True is validation succeded, False if it does not
        """
        raise NotImplementedError("Need to extend Validator class and implement `expr()`")

    def msg(self, *args, obj: Any, field: str, value: Any) -> Optional[str]:
        """
        Returns a message being used when reporting validation_errors().
        Receives same arguments as expr() method.
        If not implemented default message will be "<Valdiator>: validation failed"
        :return: str with a message
        """
        return f"{self.name}: validation failed"

    def extra(self, *args, obj: Any, field: str, value: Any) -> Dict[str, Any]:
        """
        By default validation_errors() will report back a dictionary containing
        basic fields: validator name, field and value.
        By implementing this method, additional custom values or calculated values can be added
        to the dictionary.
        If not implemented, only basic fields are reported back.
        Receives same arguments as expr() method.
        :return: a dictionary with extra information to report
        """
        return {}

    def invoke(self, *args, obj: Any, field: str, value: Any):
        """
        Invokes the validation for this field. This method is called internally by
        @validate decorator.
        """
        if not self.expr(*args, obj=obj, field=field, value=value):
            raise ValueError(
                self.msg(*args, obj=obj, field=field, value=value),
                {'type': self.name, 'field': field, 'value': value,
                 **self.extra(*args, obj=obj, field=field, value=value)}
            )

    def _apply(self, *args):
        return partial(self.invoke, *args)

    @classmethod
    def build(cls):
        """
        Builds an instance of an implemented validator.
        This instance can be used in a argument to @validate decorator
        """
        return cls()._apply  # pylint: disable=protected-access


class AsyncValidator:
    """
    Abstract class to be extended to implement custom async validators for dataclasses fields
    @see Validator
    """
    @property
    def name(self) -> str:
        """
        Returns the name of the validator, using the class name implementing it
        """
        return type(self).__name__

    async def expr(self, *args, obj: Any, field: str, value: Any) -> bool:
        """
        An async function implementing a boolean expression that will be applied to fields.
        same as @see Validator.expr, but async
        """
        raise NotImplementedError("Need to extend Validator class and implement `expr()`")

    def msg(self, *args, obj: Any, field: str, value: Any) -> Optional[str]:
        """
        Returns a message being used when reporting validation_errors().
        same as @see Validator.msg
        """
        return f"{self.name}: validation failed"

    def extra(self, *args, obj: Any, field: str, value: Any) -> Dict[str, Any]:
        """
        Extra values to be resported back on validation errors.
        same as @see Validator.extra
        """
        return {}

    async def invoke(self, *args, obj: Any, field: str, value: Any):
        if not await self.expr(*args, obj=obj, field=field, value=value):
            raise ValueError(
                self.msg(*args, obj=obj, field=field, value=value),
                {'type': self.name, 'field': field, 'value': value,
                 **self.extra(*args, obj=obj, field=field, value=value)}
            )

    def _apply(self, *args):
        return partial(self.invoke, *args)

    @classmethod
    def build(cls):
        """
        Builds an instance of an implemented validator.
        This instance can be used in a argument to @validate decorator
        """
        return cls()._apply  # pylint: disable=protected-access


class ValidationResult(NamedTuple):
    msg: str
    extra: dict


class Mode(Enum):
    """
    Validation modes:
    :field: STRICT, validation is performed on object creation and raises a ValueException containing information
        about all failed validations. Object cannot be created.
    :field: ON_CREATE, validation is performed only once on object creation, but validation errors can be
        obtained calling validation_errors(). Notice that even mutating the object wont affect validation_errors()
        results on further calls.
    :field: ON_DEMAND: validation is only perform when calling validation_errors() on the object. This allows
        mutating and validation an object as many times as needed.
    """
    STRICT = 'Strict'
    ON_CREATE = 'OnCreate'
    ON_DEMAND = 'OnDemand'
    ASYNC = 'Async'


def validate(validation_mode: Union[str, Mode] = Mode.STRICT, cls=None, **kwargs):
    """
    Decorator specifying validators to be used in a dataclass fields

    Example::

        @dataclass
        @validate(
            Mode.STRICT,
            field_a=same_as('field_b')
        )
        class ValidatedObject:
            field_a: int
            field_b: int

    When object is created (Mode.STRICT) an ValueException will be raised
    if field_a is not the same as field_b.
    First unnamed argument is Mode and if not specified it defaults to Mode.STRICT
    Remaining keyword-arguments are the field=validator(...) to apply to each field
    """

    def wrap(cls):
        current_post_init = None

        if hasattr(cls, '__post_init__'):
            current_post_init = getattr(cls, '__post_init__')

        async def _avalidation_errors(obj):
            errors = defaultdict(list)
            for field, funcs in cls._VALIDATE.items():  # pylint: disable=protected-access
                value = getattr(obj, field)
                if not isinstance(funcs, Iterable):  # pylint: disable=isinstance-second-argument-not-valid-type
                    funcs = [funcs]
                for func in funcs:
                    try:
                        res = func(obj=obj, field=field, value=value)
                        if iscoroutine(res):
                            await res
                    except ValueError as e:
                        errors[field].append(ValidationResult(*e.args))
            return errors

        def _validation_errors(obj):
            if validation_mode != Mode.ON_DEMAND and hasattr(obj, '_validation_errors'):
                return getattr(obj, '_validation_errors')
            errors = defaultdict(list)
            for field, funcs in cls._VALIDATE.items():  # pylint: disable=protected-access
                value = getattr(obj, field)
                if not isinstance(funcs, Iterable):  # pylint: disable=isinstance-second-argument-not-valid-type
                    funcs = [funcs]
                for func in funcs:
                    try:
                        func(obj=obj, field=field, value=value)
                    except ValueError as e:
                        errors[field].append(ValidationResult(*e.args))
            return errors

        def _post_init_mixin(obj):
            if current_post_init is not None:
                current_post_init(obj)
            errors = _validation_errors(obj)
            if validation_mode != Mode.ON_DEMAND:
                setattr(obj, '_validation_errors', errors)
            if validation_mode == Mode.STRICT and len(errors) > 0:
                raise ValueError(
                    ', '.join(error.msg for items in errors.values() for error in items),
                    dict(errors.items()))

        setattr(cls, '_VALIDATE', kwargs)
        if validation_mode == Mode.ASYNC:
            setattr(cls, 'validation_errors', _avalidation_errors)
        else:
            setattr(cls, 'validation_errors', _validation_errors)
        if validation_mode in (Mode.STRICT, Mode.ON_CREATE):
            setattr(cls, '__post_init__', _post_init_mixin)
        return cls

    if isinstance(cls, (Mode, str)):
        validation_mode, cls = cls, None
    if isinstance(validation_mode, str):
        validation_mode = Mode(validation_mode)
    if cls is None:
        return wrap
    return wrap(cls)
