clean: clean-test clean-cache

clean-test:
	find . -type f -name "*.mp4" -exec rm -f {} \;

clean-cache:
	find . \( \
		-type d -name .pytest_cache -o -type d -name __pycache__ -o -name "*.pyc" -o -type d -name .mypy_cache \
	\) -prune -exec rm -rf {} \;

codetest:
	flake8 .
	mypy .

test:
	python3 -m pytest 
	make codetest
