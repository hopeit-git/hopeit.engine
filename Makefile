SRC = $(wildcard src/*.py)

.PHONY: dev check test install clean schemas dist-only

deps:
	cd engine && \
	pip install -U -r requirements.txt

dev-deps: deps
	cd engine && \
	pip install -U -r requirements-dev.txt

locked-deps:
	cd engine && \
	pip install -U pip && \
	pip install -U wheel && \
	pip install --force-reinstall -r requirements.lock && \
	pip install -U -r requirements-dev.txt

lock-requirements: clean dev-deps
	cd engine && \
	pip freeze > requirements.lock

check-engine:
	/bin/bash engine/build/ci-static-engine.sh

check-plugins:
	/bin/bash plugins/build/ci-static-plugins.sh

check-apps:
	/bin/bash apps/build/ci-static-apps.sh

check: check-engine check-plugins check-apps

test-engine:
	/bin/bash engine/build/ci-test-engine.sh

test-plugins:
	/bin/bash plugins/build/ci-test-plugins.sh

test-apps:
	/bin/bash apps/build/ci-test-apps.sh

test: test-engine test-plugins test-apps

install:
	cd engine && \
	pip install --force-reinstall -r requirements.txt && \
	pip install -U -e . --no-deps && \
	pip install -U -e ".[web]" --no-deps && \
	pip install -U -e ".[cli]" --no-deps

install-app:
	cd $(APPFOLDER) && \
	pip install -U -e .

install-plugin:
	cd $(PLUGINFOLDER) && \
	pip install -U -e .

qa: test check
	echo "DONE."

dist: clean check test
	pip install wheel && \
	cd engine && \
	python setup.py sdist bdist_wheel

dist-plugin: clean-plugins check-plugins test-plugins
	pip install wheel && \
	cd $(PLUGINFOLDER) && \
	python setup.py sdist bdist_wheel

dist-only: clean
	pip install wheel && \
	cd engine && \
	python setup.py sdist bdist_wheel

clean:
	cd engine && \
	rm -rf dist

clean-plugins:
	cd $(PLUGINFOLDER) && \
	rm -rf dist

schemas:
	cd engine/config/schemas && \
	python update_config_schemas.py

pypi:
	pip install twine && \
	python -m twine upload -u=__token__ -p=$(PYPI_API_TOKEN) --repository pypi engine/dist/*

pypi-plugin:
	pip install twine && \
	python -m twine upload -u=__token__ -p=$(PYPI_API_TOKEN) --repository pypi $(PLUGINFOLDER)/dist/*

pypi-test:
	pip install twine && \
	python -m twine upload -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --repository testpypi engine/dist/*

pypi-test-plugin:
	pip install twine && \
	python -m twine upload -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --repository testpypi $(PLUGINFOLDER)/dist/*

install-simple-example:
	make install && \
	make PLUGINFOLDER=plugins/streams/redis install-plugin && \
	make PLUGINFOLDER=plugins/storage/fs install-plugin && \
	make PLUGINFOLDER=plugins/storage/redis install-plugin && \
	make PLUGINFOLDER=plugins/ops/config-manager install-plugin && \
	make PLUGINFOLDER=plugins/ops/log-streamer install-plugin && \
	make PLUGINFOLDER=plugins/ops/apps-visualizer install-plugin && \
	make PLUGINFOLDER=plugins/auth/basic-auth install-plugin && \
	make APPFOLDER=apps/examples/simple-example install-app

run-simple-example:
	export PYTHONPATH=apps/examples/simple-example/src && \
	hopeit_server run \
		--port=$(PORT) \
		--start-streams \
		--config-files=engine/config/dev-local.json,plugins/auth/basic-auth/config/plugin-config.json,plugins/ops/config-manager/config/plugin-config.json,plugins/ops/apps-visualizer/config/plugin-config.json,apps/examples/simple-example/config/app-config.json \
		--api-file=apps/examples/simple-example/api/openapi.json
