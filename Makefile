all: install

clean:
	rm -rf venv

venv:
	python -m venv venv

install: venv
	. venv/bin/activate; pip install -r requirements.txt \
		&& find plugins -type f -name requirements.txt -exec pip install --no-cache-dir -r {} \;

install-dev: install
	. venv/bin/activate; pip install -r test_requirements.txt \
		&& find plugins -type f -name test_requirements.txt -exec pip install --no-cache-dir -r {} \;

.PHONY: clean install install-dev all
