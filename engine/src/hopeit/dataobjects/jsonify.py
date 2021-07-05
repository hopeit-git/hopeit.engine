"""
Json tools to serialized and deserialze data objects
"""

import warnings

from hopeit.dataobjects.payload import Payload


class Json(Payload):
    """
    Json convenience ser/deser functions for @dataobject decorated object (@see DataObject)
    """
    warnings.warn(
        "Usage of `Json` from `hopeit.engine.jsonify` is deprecated since 0.8.3 and will be removed "
        "in a future version. Use `Payload` from `hopeit.engine.payload` instead", DeprecationWarning
    )
