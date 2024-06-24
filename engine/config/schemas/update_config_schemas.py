import json

from pydantic import TypeAdapter

from hopeit.app.config import AppConfig
from hopeit.server.config import ServerConfig

with open('app-config-schema-draftv6.json', 'w') as fb:
    fb.write(json.dumps(TypeAdapter(AppConfig).json_schema(), indent=2))

with open('server-config-schema-draftv6.json', 'w') as fb:
    fb.write(json.dumps(TypeAdapter(ServerConfig).json_schema(), indent=2))
