"""
Json tools to serialized and deserialze data objects
"""

import json
from typing import Type, Generic, Optional, Union

from dataclasses_jsonschema import ValidationError

from hopeit.dataobjects import EventPayloadType


class Json(Generic[EventPayloadType]):
    """
    Json convenience ser/deser functions for @dataobject decorated object (@see DataObject)
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
        if datatype in [str, int, float, bool]:
            return datatype(json.loads(json_str).get(key))  # type: ignore
        if datatype in [dict, list, set]:
            return datatype(json.loads(json_str))  # type: ignore
        assert getattr(datatype, 'from_json'), \
            f"{datatype} should be annotated with @dataobject"
        try:
            return datatype.from_json(json_str, validate=datatype.__data_object__['validate'])  # type: ignore
        except ValidationError as e:
            raise ValueError(f"Cannot read JSON: type={datatype} validation_error={str(e)}") from e

    @staticmethod
    def to_json(payload: EventPayloadType, key: Optional[str] = 'value') -> str:
        """
        Converts event payload to json string

        :param payload: EventPayload, instance of supported object type
        :param key: key name used in generated json when serializing atomic values
        :return: str containing json representation of data. In case of simple datatypes,
            a json str of key:value form will be generated using key parameter if it's not None.
        """
        if isinstance(payload, (str, int, float, bool)):  # immutable supported types
            if key is None:
                return json.dumps(payload)
            return json.dumps({key: payload})
        if isinstance(payload, (list, set)):
            return "[" + ', '.join(Json.to_json(item, key=None) for item in payload) + "]"
        if isinstance(payload, dict):
            return "{" + ', '.join(f'"{str(k)}": {Json.to_json(item, key=None)}' for k, item in payload.items()) + "}"
        assert getattr(payload, 'to_json'), \
            f"{type(payload)} should be annotated with @dataobject"
        try:
            return payload.to_json(validate=payload.__data_object__['validate'])  # type: ignore
        except (ValidationError, AttributeError) as e:
            raise ValueError(f"Cannot convert to JSON: type={type(payload)} validation_error={str(e)}") from e

    @staticmethod
    def parse_form_field(field_data: Union[str, dict], datatype: Type[EventPayloadType],
                         key: str = 'value') -> EventPayloadType:
        """Helper to parse dataobjects from form-fields where encoding type is not correctly set to json"""
        if isinstance(field_data, str):
            return Json.from_json(field_data, datatype, key)
        return datatype.from_dict(field_data)  # type: ignore
