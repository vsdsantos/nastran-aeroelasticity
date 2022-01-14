
main:	setup

setup:
	( \
		python -m pip install virtualenv; \
		python -m virtualenv env && \
		source env/bin/activate && \
		pip install -r requirements.txt; \
	)

build:
	. env/bin/activate; python -m build

test:
	. env/bin/activate; python -m pytest

clean:
	rm -rf env

install:
	# python -m pip install -f dist/*
