#!/bin/bash
hopeit_openapi create \
--title="Simple Example" \
--description="Simple Example" \
--api-version="$(python -m hopeit.server.version APPS_API_VERSION)" \
--config-files=engine/config/dev-noauth.json,plugins/auth/basic-auth/config/plugin-config.json,plugins/ops/apps-visualizer/config/plugin-config.json,apps/examples/simple-example/config/app-config.json \
--output-file=apps/examples/simple-example/api/openapi.json
