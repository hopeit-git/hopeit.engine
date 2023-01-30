from hopeit.app.config import AppConfig
from hopeit.server.config import ServerConfig
import json

with open('app-config-schema-draftv6.json', 'w') as fb:
    fb.write(AppConfig.schema_json(indent=2))

with open('server-config-schema-draftv6.json', 'w') as fb:
    fb.write(ServerConfig.schema_json(indent=2))
