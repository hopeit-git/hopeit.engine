from datetime import datetime
from hopeit.dataobjects import dataobject


@dataobject(event_id="object_id", event_ts="object_ts")
class MyObject:
    object_id: str
    object_ts: datetime
    value: int
