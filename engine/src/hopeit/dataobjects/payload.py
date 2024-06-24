"""
Payload tools to serialize and deserialze event payloads and responses, including dataobjects
"""

from typing import Dict, Type, Generic, Union

from pydantic import RootModel, ValidationError

from hopeit.dataobjects import EventPayloadType

_ATOMIC_TYPES = (str, int, float, bool)


class Payload(Generic[EventPayloadType]):
    """
    Convenience ser/deser functions for @dataobject decorated object (@see DataObject)
    """
    @staticmethod
    def from_json(json_str: Union[str, bytes],
                  datatype: Type[EventPayloadType],
                  key: str = 'value') -> EventPayloadType:
        """
        Converts json_str to desired datatype

        :param json_str: str containing valid json,
            or string representation for atomic values
        :param datatype: supported types defined in EventPayload
        :param key: key to extract atomic types from
        :return: instance of datatype
        """
        if datatype in _ATOMIC_TYPES:
            return RootModel[Dict[str, datatype]].model_validate_json(json_str).root[key]  # type: ignore[valid-type]
        try:
            return RootModel[datatype].model_validate_json(json_str).root  # type: ignore[valid-type]
        except ValidationError:
            raise
        except Exception as e:
            if not hasattr(datatype, '__data_object__'):
                raise TypeError(f"{datatype} must be annotated with @dataobject") from e
            raise  # Raises unexpected exceptions, if does not catch missing @dataobject

    @staticmethod
    def from_obj(data: Union[dict, list],
                 datatype: Type[EventPayloadType],
                 key: str = 'value') -> EventPayloadType:
        """
        Converts dictionary to desired datatype

        :param data: dictionary containing fields expected on datatype
        :param datatype: supported types defined in EventPayload
        :param key: key to extract atomic types from
        :param item_datatype: optional datatype to parse items in collections
        :return: instance of datatype
        """
        if datatype in _ATOMIC_TYPES:
            return RootModel[datatype].model_validate(data.get(key)).root  # type: ignore[valid-type, union-attr]
        try:
            return RootModel[datatype].model_validate(data).root  # type: ignore[valid-type]
        except ValidationError:
            raise
        except Exception as e:
            if not hasattr(datatype, '__data_object__'):
                raise TypeError(f"{datatype} must be annotated with @dataobject") from e
            raise  # Raises unexpected exceptions, if does not catch missing @dataobject

    @staticmethod
    def to_json(payload: EventPayloadType, key: str = 'value') -> str:
        """
        Converts event payload to json string

        :param payload: EventPayload, instance of supported object type
        :param key: key name used in generated json when serializing atomic values
        :return: str containing json representation of data. In case of simple datatypes,
            a json str of key:value form will be generated using key parameter if it's not None.
        """
        if isinstance(payload, _ATOMIC_TYPES):  # immutable supported types
            return RootModel({key: payload}).model_dump_json()
        try:
            return RootModel(payload).model_dump_json()
        except Exception as e:
            if not hasattr(payload, '__data_object__'):
                raise TypeError(f"{type(payload)} must be annotated with @dataobject") from e
            raise  # Raises unexpected exceptions, if does not catch missing @dataobject

    @staticmethod
    def to_obj(payload: EventPayloadType, key: str = 'value') -> Union[dict, list, set]:
        """
        Converts event payload to dictionary or list

        :param payload: EventPayload, instance of supported object type
        :param key: key name used in generated json when serializing atomic values
        :return: dict or list containing mapped representation of data. In case of simple datatypes,
            a key:value form will be generated using key parameter. All objects mappable to dict will
            be converted. Flat collections will be converted to list.
        """
        if isinstance(payload, _ATOMIC_TYPES):  # immutable supported types
            return {key: payload}
        try:
            serialized = RootModel(payload).model_dump()  # pylint: disable=assignment-from-no-return
            if not isinstance(serialized, (dict, list, set)):
                raise TypeError(f"Cannot serialize {type(payload)} as `dict`, `list` or `set`")
            return serialized
        except Exception as e:
            if not hasattr(payload, '__data_object__'):
                raise TypeError(f"{type(payload)} must be annotated with @dataobject") from e
            raise  # Raises unexpected exceptions, if does not catch missing @dataobject

    @staticmethod
    def parse_form_field(field_data: Union[str, dict], datatype: Type[EventPayloadType],
                         key: str = 'value') -> EventPayloadType:
        """Helper to parse dataobjects from form-fields where encoding type is not correctly set to json"""
        if isinstance(field_data, str):
            return Payload.from_json(field_data, datatype, key)
        return Payload.from_obj(field_data, datatype)
