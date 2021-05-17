export PYTHONPATH=../src && hopeit_openapi create \
--config-files=../config/dev-noauth.json,../config/app-config.json \
--output-file=../api/openapi.json \
--api-version=$(python -m hopeit.server.version APPS_API_VERSION) \
--title="Simple Benchmark" \
--description="Simple Benchmark App"
