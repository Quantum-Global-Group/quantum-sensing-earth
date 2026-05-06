.PHONY: setup run test lint clean

setup:
	python -m pip install -r requirements.txt

run:
	python -m src.main

test:
	pytest -q

lint:
	python -m compileall src

clean:
	rm -rf outputs/* .pytest_cache
