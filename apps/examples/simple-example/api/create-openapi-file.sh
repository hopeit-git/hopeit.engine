#!/bin/bash
hopeit_openapi create \
--title="Simple Example" \
--description="Simple Example" \
--api-version="$(python -m hopeit.server.version)" \
--config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/plugin-config.json,apps/examples/simple-example/config/app-config.json \
--output-file=apps/examples/simple-example/api/openapi.json
