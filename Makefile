SRC = $(wildcard src/*.py)

.PHONY: dev check test install clean schemas dist-only

deps:
	cd engine && \
	pip install -U -r requirements.txt

dev-deps: deps
	cd engine && \
	pip install -U -r requirements-dev.txt

locked-deps: deps
	cd engine && \
	pip install --force-reinstall -r requirements.lock

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
	pip install -e . --no-deps && \
	pip install -e ".[web]" --no-deps && \
	pip install -e ".[cli]" --no-deps

install-app:
	cd $(APPFOLDER) && \
	pip install -e .

install-plugin:
	cd $(PLUGINFOLDER) && \
	pip install -e .

qa: test check
	echo "DONE."

dist: clean check test
	pip install wheel && \
	cd engine && \
	python setup.py sdist bdist_wheel

dist-only: clean
	pip install wheel && \
	cd engine && \
	python setup.py sdist bdist_wheel

clean:
	cd engine && \
	rm -rf dist

schemas:
	cd engine/config/schemas && \
	python update_config_schemas.py

pypi: dist
	python -m twine upload -u=__token__ -p=$(PYPI_API_TOKEN) --repository pypi engine/dist/*

pypi_test:
	python -m twine upload -u=__token__ -p=$(TEST_PYPI_API_TOKEN) --repository testpypi engine/dist/*