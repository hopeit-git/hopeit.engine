"""
Payload tools to serialize and deserialze event payloads and responses, including dataobjects
"""

import json
from typing import Type, Generic, Optional, Union

from dataclasses_jsonschema import ValidationError

from hopeit.dataobjects import EventPayloadType

_ATOMIC_TYPES = (str, int, float, bool)
_COLLECTION_TYPES = (dict, list, set)
_MAPPING_TYPES = (dict, )
_LIST_TYPES = (list, set)
_UNORDERED_LIST_TYPES = (set, )


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
            return datatype(json.loads(json_str).get(key))  # type: ignore
        if datatype in _COLLECTION_TYPES:
            return datatype(json.loads(json_str))  # type: ignore
        assert getattr(datatype, 'from_json'), \
            f"{datatype} should be annotated with @dataobject"
        try:
            return datatype.from_json(json_str, validate=datatype.__data_object__['validate'])  # type: ignore
        except ValidationError as e:
            raise ValueError(f"Cannot read JSON: type={datatype} validation_error={str(e)}") from e

    @staticmethod
    def from_obj(data: Union[dict, list],
                 datatype: Type[EventPayloadType],
                 key: str = 'value',
                 item_datatype: Optional[Type[EventPayloadType]] = None) -> EventPayloadType:
        """
        Converts dictionary to desired datatype

        :param data: dictionary containing fields expected on datatype
        :param datatype: supported types defined in EventPayload
        :param key: key to extract atomic types from
        :param item_datatype: optional datatype to parse items in collections
        :return: instance of datatype
        """
        if datatype in _ATOMIC_TYPES:
            return datatype(data.get(key))  # type: ignore
        if datatype in _MAPPING_TYPES:
            if item_datatype and isinstance(data, _MAPPING_TYPES):
                return {  # type: ignore
                    k: Payload.from_obj(v, item_datatype, key) for k, v in data.items()
                }
            return datatype(data)  # type: ignore
        if datatype in _LIST_TYPES:
            if item_datatype and isinstance(data, _LIST_TYPES):
                return datatype([  # type: ignore
                    Payload.from_obj(v, item_datatype, key) for v in data
                ])
            return datatype(data)  # type: ignore
        assert getattr(datatype, 'from_dict'), \
            f"{datatype} should be annotated with @dataobject"
        try:
            return datatype.from_dict(data, validate=datatype.__data_object__['validate'])  # type: ignore
        except ValidationError as e:
            raise ValueError(f"Cannot read object: type={datatype} validation_error={str(e)}") from e

    @staticmethod
    def to_json(payload: EventPayloadType, key: Optional[str] = 'value') -> str:
        """
        Converts event payload to json string

        :param payload: EventPayload, instance of supported object type
        :param key: key name used in generated json when serializing atomic values
        :return: str containing json representation of data. In case of simple datatypes,
            a json str of key:value form will be generated using key parameter if it's not None.
        """
        if isinstance(payload, _ATOMIC_TYPES):  # immutable supported types
            if key is None:
                return json.dumps(payload)
            return json.dumps({key: payload})
        if isinstance(payload, _LIST_TYPES):
            return "[" + ', '.join(Payload.to_json(item, key=None) for item in payload) + "]"
        if isinstance(payload, _MAPPING_TYPES):
            return "{" + ', '.join(
                f'"{str(k)}": {Payload.to_json(item, key=None)}' for k, item in payload.items()
            ) + "}"
        assert getattr(payload, 'to_json'), \
            f"{type(payload)} should be annotated with @dataobject"
        try:
            return payload.to_json(validate=payload.__data_object__['validate'])  # type: ignore
        except (ValidationError, AttributeError) as e:
            raise ValueError(f"Cannot convert to JSON: type={type(payload)} validation_error={str(e)}") from e

    @staticmethod
    def to_obj(payload: EventPayloadType, key: Optional[str] = 'value') -> Union[dict, list]:
        """
        Converts event payload to dictionary or list

        :param payload: EventPayload, instance of supported object type
        :param key: key name used in generated json when serializing atomic values
        :return: dict or list containing mapped representation of data. In case of simple datatypes,
            a key:value form will be generated using key parameter. All objects mappable to dict will
            be converted. Flat collections will be converted to list.
        """
        if isinstance(payload, _ATOMIC_TYPES):  # immutable supported types
            if key is None:
                return payload  # type: ignore  # only for recursive use
            return {key: payload}
        if isinstance(payload, _UNORDERED_LIST_TYPES):
            return [Payload.to_obj(v, key=None) for v in sorted(payload)]
        if isinstance(payload, _LIST_TYPES):
            return [Payload.to_obj(v, key=None) for v in payload]
        if isinstance(payload, _MAPPING_TYPES):
            return {k: Payload.to_obj(v, key=None) for k, v in payload.items()}
        assert getattr(payload, 'to_dict'), \
            f"{type(payload)} should be annotated with @dataobject"
        try:
            return payload.to_dict(validate=payload.__data_object__['validate'])  # type: ignore
        except (ValidationError, AttributeError) as e:
            raise ValueError(f"Cannot convert to dict: type={type(payload)} validation_error={str(e)}") from e

    @staticmethod
    def parse_form_field(field_data: Union[str, dict], datatype: Type[EventPayloadType],
                         key: str = 'value') -> EventPayloadType:
        """Helper to parse dataobjects from form-fields where encoding type is not correctly set to json"""
        if isinstance(field_data, str):
            return Payload.from_json(field_data, datatype, key)
        return datatype.from_dict(field_data)  # type: ignore
