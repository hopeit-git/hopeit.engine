SRC = $(wildcard src/*.py)

.PHONY: check test install clean

install:
	pip install -e .

dist: clean
	python setup.py sdist bdist_wheel

pypi: dist
	twine upload --repository pypi dist/*

clean:
	rm -rf dist
