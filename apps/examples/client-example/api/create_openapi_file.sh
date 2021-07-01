#!/bin/bash
export PYTHONPATH=./apps/examples/client-example/src && \
export HOPEIT_SIMPLE_EXAMPLE_HOSTS="in-process" && \
hopeit_openapi create \
--title="Client Example" \
--description="Client Example" \
--api-version="$(python -m hopeit.server.version APPS_API_VERSION)" \
--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,apps/examples/client-example/config/app-config.json \
--output-file=apps/examples/client-example/api/openapi.json
