export PYTHONPATH=apps/benchmark/simple-benchmark/src/ && hopeit_openapi create \
--config-files=engine/config/dev-noauth.json,apps/benchmark/simple-benchmark/config/app-config.json \
--output-file=apps/benchmark/simple-benchmark/api/openapi.json \
--api-version=$(python -m hopeit.server.version APPS_API_VERSION) \
--title="Simple Benchmark" \
--description="Simple Benchmark App"
