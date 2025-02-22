SRC = $(wildcard src/*.py)

.PHONY: env clean-env dev deps format lint test

env:
	uv venv --seed --python 3.12
	uv sync --dev

clean-env:
	rm -rf .venv
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm uv.lock

dev: env
	uv pip install -r pyproject.toml
	uv pip install -U --no-deps -e ./engine
	uv pip install -U --no-deps -e ./plugins/auth/basic-auth
	uv pip install -U --no-deps -e ./plugins/clients/apps-client
	uv pip install -U --no-deps -e ./plugins/data/dataframes
	uv pip install -U --no-deps -e ./plugins/ops/apps-visualizer
	uv pip install -U --no-deps -e ./plugins/ops/config-manager
	uv pip install -U --no-deps -e ./plugins/ops/log-streamer
	uv pip install -U --no-deps -e ./plugins/storage/fs
	uv pip install -U --no-deps -e ./plugins/storage/redis
	uv pip install -U --no-deps -e ./plugins/streams/redis

ci-deps:
	uv venv --seed --python $(PYTHONVERSION)
	uv sync --dev
	uv pip install -r pyproject.toml

format-module:
	uv run ruff format $(MODULEFOLDER)/src/ $(MODULEFOLDER)/test/
	uv run ruff check $(MODULEFOLDER)/src/ $(MODULEFOLDER)/test/ --fix

format:
	make MODULEFOLDER=engine format-module
	make MODULEFOLDER=apps/examples/simple-example format-module
	make MODULEFOLDER=apps/examples/client-example format-module
	make MODULEFOLDER=apps/examples/dataframes-example format-module
	make MODULEFOLDER=plugins/auth/basic-auth format-module
	make MODULEFOLDER=plugins/clients/apps-client format-module
	make MODULEFOLDER=plugins/data/dataframes format-module
	make MODULEFOLDER=plugins/ops/apps-visualizer format-module
	make MODULEFOLDER=plugins/ops/config-manager format-module
	make MODULEFOLDER=plugins/ops/log-streamer format-module
	make MODULEFOLDER=plugins/storage/fs format-module
	make MODULEFOLDER=plugins/storage/redis format-module
	make MODULEFOLDER=plugins/streams/redis format-module

lint-engine:
	uv run ruff format --check engine/src/ engine/test/
	uv run ruff check engine/src/ engine/test/
	MYPYPATH=engine/src/ uv run mypy --namespace-packages -p hopeit
	MYPYPATH=engine/src:engine/test/ uv run mypy --namespace-packages engine/test/unit/
	MYPYPATH=engine/src:engine/test/ uv run mypy --namespace-packages engine/test/integration/

lint-plugin:
	uv run ruff format --check $(PLUGINFOLDER)/src/ $(PLUGINFOLDER)/test/
	uv run ruff check $(PLUGINFOLDER)/src/ $(PLUGINFOLDER)/test/
	MYPYPATH=$(PLUGINFOLDER)/src/ uv run mypy --namespace-packages -p hopeit
	MYPYPATH=$(PLUGINFOLDER)/src:$(PLUGINFOLDER)/test uv run mypy --namespace-packages $(PLUGINFOLDER)/test/

lint-plugins:
	make PLUGINFOLDER=plugins/auth/basic-auth lint-plugin
	make PLUGINFOLDER=plugins/clients/apps-client lint-plugin
	make PLUGINFOLDER=plugins/data/dataframes lint-plugin
	make PLUGINFOLDER=plugins/ops/apps-visualizer lint-plugin
	make PLUGINFOLDER=plugins/ops/config-manager lint-plugin
	make PLUGINFOLDER=plugins/ops/log-streamer lint-plugin
	make PLUGINFOLDER=plugins/storage/fs lint-plugin
	make PLUGINFOLDER=plugins/storage/redis lint-plugin
	make PLUGINFOLDER=plugins/streams/redis lint-plugin

lint-app:
	uv run ruff format $(APPFOLDER)/src/ $(APPFOLDER)/test/ --check
	uv run ruff check $(APPFOLDER)/src/ $(APPFOLDER)/test/
	MYPYPATH=$(APPFOLDER)/src/ uv run mypy --namespace-packages $(APPFOLDER)/src/
	MYPYPATH=$(APPFOLDER)/src/ uv run mypy --namespace-packages $(APPFOLDER)/test/

lint-apps:
	make APPFOLDER=apps/examples/simple-example lint-app
	make APPFOLDER=apps/examples/client-example lint-app
	make APPFOLDER=apps/examples/dataframes-example lint-app

lint: lint-engine lint-plugins lint-apps

test-engine:
	PYTHONPATH=engine/src:engine/test uv run pytest -v --cov-fail-under=90 --cov-report=term --cov=engine/src/ engine/test/unit/ engine/test/integration/

test-plugin:
	PYTHONPATH=$(PLUGINFOLDER)/src uv run pytest -v --cov-fail-under=85 --cov-report=term --cov=$(PLUGINFOLDER)/src/ $(PLUGINFOLDER)/test/

test-plugins:
	make PLUGINFOLDER=plugins/auth/basic-auth test-plugin
	make PLUGINFOLDER=plugins/clients/apps-client test-plugin
	make PLUGINFOLDER=plugins/data/dataframes test-plugin
	make PLUGINFOLDER=plugins/ops/apps-visualizer test-plugin
	make PLUGINFOLDER=plugins/ops/config-manager test-plugin
	make PLUGINFOLDER=plugins/storage/fs test-plugin
	make PLUGINFOLDER=plugins/storage/redis test-plugin
	make PLUGINFOLDER=plugins/streams/redis test-plugin
	make PLUGINFOLDER=plugins/ops/log-streamer test-plugin

test-app:
	PYTHONPATH=$(APPFOLDER)/src:$(APPFOLDER)/test uv run pytest -v --cov-fail-under=90 --cov-report=term --cov=$(APPFOLDER)/src/ $(APPFOLDER)/test/

test-apps:
	make APPFOLDER=apps/examples/simple-example test-app
	make APPFOLDER=apps/examples/client-example test-app

test: test-engine test-plugins test-apps

dist-engine: clean-dist-engine
	uv --project=engine build

dist-plugin: clean-dist-plugin
	uv --project=$(PLUGINFOLDER) build

clean-dist-engine:
	rm -rf engine/dist

clean-dist-plugin:
	rm -rf $(PLUGINFOLDER)/dist

schemas:
	uv --directory=engine/config/schemas run python update_config_schemas.py

publish-engine-pypi:
	uv publish -u=__token__ -p=$(PYPI_API_TOKEN) engine/dist/*

publish-plugin-pypi:
	uv publish -u=__token__ -p=$(PYPI_API_TOKEN) $(PLUGINFOLDER)/dist/*

publish-engine-pypi-test:
	uv publish -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --publish-url=https://test.pypi.org/legacy/  engine/dist/*

publish-plugin-pypi-test:
	uv publish -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --publish-url=https://test.pypi.org/legacy/  $(PLUGINFOLDER)/dist/*

update-examples-api:
	bash apps/examples/simple-example/api/create_openapi_file.sh
	bash apps/examples/client-example/api/create_openapi_file.sh
	bash apps/examples/dataframes-example/api/create_openapi_file.sh
	bash plugins/ops/apps-visualizer/api/create_openapi_file.sh

run-simple-example:
	uv run hopeit_server run \
		--port=$(PORT) \
		--start-streams \
		--config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/plugin-config.json,plugins/ops/config-manager/config/plugin-config.json,apps/examples/simple-example/config/app-config.json \
		--api-file=apps/examples/simple-example/api/openapi.json

run-client-example:
	HOPEIT_SIMPLE_EXAMPLE_HOSTS=$(HOSTS) uv run hopeit_server run \
		--port=$(PORT) \
		--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,apps/examples/client-example/config/app-config.json \
		--api-file=apps/examples/client-example/api/openapi.json

run-apps-visualizer:
	HOPEIT_APPS_VISUALIZER_HOSTS=$(HOSTS) uv run hopeit_server run \
		--port=$(PORT) \
		--start-streams \
		--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,plugins/ops/apps-visualizer/config/plugin-config.json \
		--api-file=plugins/ops/apps-visualizer/api/openapi.json

run-log-streamer:
	uv run hopeit_server run \
		--port=$(PORT) \
		--start-streams \
		--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,plugins/ops/log-streamer/config/plugin-config.json

start-redis:
	cd docker && \
	docker compose up -d redis && \
	cd ..

stop-redis:
	cd docker && \
	docker compose stop redis && \
	cd ..
