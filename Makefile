SRC = $(wildcard src/*.py)

.PHONY: env clean-env dev deps format lint test clean schemas dist-only

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
	uv pip install -U --no-deps -e ./plugins/storage/fs

ci-deps:
	uv venv --seed --python $(PYTHONVERSION)
	uv sync --dev
	uv pip install -r pyproject.toml

# deps:
# 	cd engine && \
# 	pip install -U pip && \
# 	pip install -U wheel && \
# 	pip install -U -r requirements.txt

# dev-deps: deps
# 	cd engine && \
# 	pip install -U -r requirements-dev.txt

# locked-deps:
# 	cd engine && \
# 	pip install -U pip && \
# 	pip install -U wheel && \
# 	pip install -U -r requirements-dev.txt

# ci-setup: locked-deps
# 	make install && \
# 	make install-plugins && \
# 	make install-examples

format-module:
	uv run ruff format $(MODULEFOLDER)/src/ $(MODULEFOLDER)/test/
	uv run ruff check $(MODULEFOLDER)/src/ $(MODULEFOLDER)/test/ --fix

format:
	make MODULEFOLDER=engine format-module
# 	make MODULEFOLDER=apps/examples/simple-example format-module
# 	make MODULEFOLDER=apps/examples/client-example format-module
# 	make MODULEFOLDER=apps/examples/dataframes-example format-module
# 	make MODULEFOLDER=plugins/auth/basic-auth format-module
# 	make MODULEFOLDER=plugins/clients/apps-client format-module
# 	make MODULEFOLDER=plugins/data/dataframes format-module
# 	make MODULEFOLDER=plugins/ops/apps-visualizer format-module
# 	make MODULEFOLDER=plugins/ops/config-manager format-module
# 	make MODULEFOLDER=plugins/ops/log-streamer format-module
	make MODULEFOLDER=plugins/storage/fs format-module
# 	make MODULEFOLDER=plugins/storage/redis format-module
# 	make MODULEFOLDER=plugins/streams/redis format-module

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
# 	make PLUGINFOLDER=plugins/auth/basic-auth lint-plugin
# 	make PLUGINFOLDER=plugins/clients/apps-client lint-plugin
# 	make PLUGINFOLDER=plugins/data/dataframes lint-plugin
# 	make PLUGINFOLDER=plugins/ops/apps-visualizer lint-plugin
# 	make PLUGINFOLDER=plugins/ops/config-manager lint-plugin
# 	make PLUGINFOLDER=plugins/ops/log-streamer lint-plugin
	make PLUGINFOLDER=plugins/storage/fs lint-plugin
# 	make PLUGINFOLDER=plugins/storage/redis lint-plugin
# 	make PLUGINFOLDER=plugins/streams/redis lint-plugin

lint-app:
	echo 0
# 	cd $(APPFOLDER) && \
# 	ruff format src/ test/ --check && \
# 	ruff check src/ test/ && \
# 	MYPYPATH=src/ mypy --namespace-packages src/ && \
# 	MYPYPATH=src/ mypy --namespace-packages test/

lint-apps:
	make APPFOLDER=apps/examples/simple-example lint-app
	make APPFOLDER=apps/examples/client-example lint-app
	make APPFOLDER=apps/examples/dataframes-example lint-app

# check: check-engine check-plugins check-apps

test-engine:
	PYTHONPATH=engine/test uv run pytest -v --cov-fail-under=90 --cov-report=term --cov=engine/src/ engine/test/unit/ engine/test/integration/

test-plugin:
	uv run pytest -v --cov-fail-under=90 --cov-report=term --cov=$(PLUGINFOLDER)/src/ $(PLUGINFOLDER)/test/

test-plugins:
# 	make PLUGINFOLDER=plugins/auth/basic-auth test-plugin
# 	make PLUGINFOLDER=plugins/clients/apps-client test-plugin
# 	make PLUGINFOLDER=plugins/data/dataframes test-plugin
# 	make PLUGINFOLDER=plugins/ops/apps-visualizer test-plugin
# 	make PLUGINFOLDER=plugins/ops/config-manager test-plugin
	make PLUGINFOLDER=plugins/storage/fs test-plugin
# 	make PLUGINFOLDER=plugins/storage/redis test-plugin
# 	make PLUGINFOLDER=plugins/streams/redis test-plugin
# 	make PLUGINFOLDER=plugins/ops/log-streamer test-plugin

test-app:
	echo 0
# 	PYTHONPATH=$(APPFOLDER)/test pytest -v --cov-fail-under=90 --cov-report=term --cov=$(APPFOLDER)/src/ $(APPFOLDER)/test/

test-apps:
	make APPFOLDER=apps/examples/simple-example test-app && \
	make APPFOLDER=apps/examples/client-example test-app

# test: test-engine test-plugins test-apps

# install:
# 	cd engine && \
# 	pip install --force-reinstall -r requirements.txt && \
# 	pip install -U -e . --no-deps && \
# 	pip install -U -e ".[web]" --no-deps && \
# 	pip install -U -e ".[cli]" --no-deps

# install-app:
# 	cd $(APPFOLDER) && \
# 	pip install -U -e .

# install-plugin:
# 	cd $(PLUGINFOLDER) && \
# 	pip install -U -e .

# install-plugin-extras:
# 	cd $(PLUGINFOLDER) && \
# 	pip install -U -e .[$(PLUGINEXTRAS)]

# qa: test check
# 	echo "DONE."

dist: clean-env dev
	cd engine && uv build

# dist-plugin: clean-plugins
# 	$(eval ENGINE_VERSION := $(shell python engine/src/hopeit/server/version.py))
# 	export  && pip install wheel build && \
# 	cd $(PLUGINFOLDER) && \
# 	ENGINE_VERSION=$(ENGINE_VERSION) python -m build

# clean:
# 	cd engine && \
# 	rm -rf dist

# clean-plugins:
# 	cd $(PLUGINFOLDER) && \
# 	rm -rf dist

# schemas:
# 	cd engine/config/schemas && \
# 	python update_config_schemas.py

# pypi:
# 	pip install twine && \
# 	python -m twine upload -u=__token__ -p=$(PYPI_API_TOKEN) --repository pypi engine/dist/*

# pypi-plugin:
# 	pip install twine && \
# 	python -m twine upload -u=__token__ -p=$(PYPI_API_TOKEN) --repository pypi $(PLUGINFOLDER)/dist/*

pypi-test:
# 	pip install twine && \
# 	python -m twine upload -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --repository testpypi engine/dist/*
	uv publish -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --publish-url=https://test.pypi.org/legacy/  engine/dist/*

# pypi-test-plugin:
# 	pip install twine && \
# 	python -m twine upload -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --repository testpypi $(PLUGINFOLDER)/dist/*

# update-examples-api:
# 	bash apps/examples/simple-example/api/create_openapi_file.sh && \
# 	bash apps/examples/client-example/api/create_openapi_file.sh && \
# 	bash apps/examples/dataframes-example/api/create_openapi_file.sh && \
# 	bash plugins/ops/apps-visualizer/api/create_openapi_file.sh

# install-plugins: install
# 	make PLUGINFOLDER=plugins/auth/basic-auth install-plugin && \
# 	make PLUGINFOLDER=plugins/streams/redis install-plugin && \
# 	make PLUGINFOLDER=plugins/storage/fs install-plugin && \
# 	make PLUGINFOLDER=plugins/storage/redis install-plugin && \
# 	make PLUGINFOLDER=plugins/ops/config-manager install-plugin && \
# 	make PLUGINFOLDER=plugins/ops/log-streamer install-plugin && \
# 	make PLUGINFOLDER=plugins/ops/apps-visualizer install-plugin && \
# 	make PLUGINFOLDER=plugins/clients/apps-client install-plugin && \
# 	make PLUGINFOLDER=plugins/data/dataframes PLUGINEXTRAS=pyarrow install-plugin-extras

# install-examples: install install-plugins
# 	make APPFOLDER=apps/examples/simple-example install-app && \
# 	make APPFOLDER=apps/examples/client-example install-app && \
# 	make APPFOLDER=apps/examples/dataframes-example install-app

# run-simple-example:
# 	export PYTHONPATH=apps/examples/simple-example/src && \
# 	hopeit_server run \
# 		--port=$(PORT) \
# 		--start-streams \
# 		--config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/plugin-config.json,plugins/ops/config-manager/config/plugin-config.json,apps/examples/simple-example/config/app-config.json \
# 		--api-file=apps/examples/simple-example/api/openapi.json

# run-client-example:
# 	export PYTHONPATH=apps/examples/simple-example/src && \
# 	export HOPEIT_SIMPLE_EXAMPLE_HOSTS=$(HOSTS) && \
# 	hopeit_server run \
# 		--port=$(PORT) \
# 		--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,apps/examples/client-example/config/app-config.json \
# 		--api-file=apps/examples/client-example/api/openapi.json

# run-apps-visualizer:
# 	export HOPEIT_APPS_VISUALIZER_HOSTS=$(HOSTS) && \
# 	hopeit_server run \
# 		--port=$(PORT) \
# 		--start-streams \
# 		--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,plugins/ops/apps-visualizer/config/plugin-config.json \
# 		--api-file=plugins/ops/apps-visualizer/api/openapi.json

# run-log-streamer:
# 	hopeit_server run \
# 		--port=$(PORT) \
# 		--start-streams \
# 		--config-files=engine/config/dev-local.json,plugins/ops/config-manager/config/plugin-config.json,plugins/ops/log-streamer/config/plugin-config.json

# start-redis:
# 	cd docker && \
# 	docker-compose up -d redis && \
# 	cd ..

# stop-redis:
# 	cd docker && \
# 	docker-compose stop redis && \
# 	cd ..
