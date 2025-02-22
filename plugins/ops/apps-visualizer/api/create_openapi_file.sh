#!/bin/bash
PYTHONPATH=./plugins/ops/apps-visualizer/src/ HOPEIT_APPS_VISUALIZER_HOSTS="in-process" hopeit_openapi create \
--title="Simple Example" \
--description="Simple Example" \
--api-version="$(python -m hopeit.server.version APPS_API_VERSION)" \
--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,plugins/ops/apps-visualizer/config/plugin-config.json \
--output-file=plugins/ops/apps-visualizer/api/openapi.json
