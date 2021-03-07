#!/bin/bash
cd ../../../../
hopeit_openapi create --title="Simple Example" --description="Simple Example" --api-version="0.2.0" --config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --output-file=apps/examples/simple-example/api/openapi.json