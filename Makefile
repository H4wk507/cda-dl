clean-test:
	find . \( -type f -name "*.mp4" -o -type f -name "*.part" \) -exec rm -f {} \;
	# purge empty directories
	fd -te -td -X rm -rf
	fd -te -td -X rm -rf

clean-cache:
	find . \( \
		-type d -name .pytest_cache -o -type d -name __pycache__ -o -name "*.pyc" -o -type d -name .mypy_cache \
	\) -prune -exec rm -rf {} \;

clean-build:
	rm -rf build cda_dl.egg-info dist

clean: clean-test clean-cache clean-build

codetest:
	isort .
	black --line-length 79 --preview .
	flake8 .
	mypy .

test:
	python3 -m pytest 
	make codetest

upload:
	python3 setup.py sdist bdist_wheel
	twine upload dist/*
