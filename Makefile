test:
	python setup.py test

clean:
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/

resources:
	pyrcc4 -py2 resources.qrc -o gridsync/resources.py

install: clean
	python setup.py install

app: clean
	pyinstaller --clean --onefile --windowed gridsync.spec
