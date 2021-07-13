test:
	py.test -svvvv --junitprefix=warc-migrator --junitxml=junit.xml tests

coverage:
	py.test tests --cov=warc_migrator --cov-report=html
	coverage report -m
	coverage html
	coverage xml

