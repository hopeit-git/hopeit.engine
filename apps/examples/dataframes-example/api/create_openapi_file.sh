#!/bin/bash
export PYTHONPATH=./apps/examples/dataframes-example/src && \
hopeit_openapi create \
--title="Dataframes Example" \
--description="Dataframes Example" \
--api-version="$(python -m hopeit.server.version APPS_API_VERSION)" \
--config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/plugin-config.json,plugins/ops/config-manager/config/plugin-config.json,plugins/data/dataframes/config/plugin-config.json,apps/examples/dataframes-example/config/app-config.json \
--output-file=apps/examples/dataframes-example/api/openapi.json
