all: install

clean:
	rm -rf venv

install:
	python -m venv venv
	. venv/bin/activate; pip install -r requirements.txt \
		&& find plugins -type f -name requirements.txt -exec pip install --no-cache-dir -r {} \;

.PHONY: clean install all
