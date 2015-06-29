test:
	python setup.py test

clean:
	rm -rf build/
	rm -rf dist/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

icns:
	png2icns images/gridsync.icns images/gridsync1024.png images/gridsync512.png images/gridsync256.png images/gridsync128.png images/gridsync32.png images/gridsync16.png

resources:
	pyrcc4 -py2 resources.qrc -o gridsync/resources.py

install: clean
	python setup.py install --user

app: clean
	pyinstaller --clean --onefile --windowed gridsync.spec

uninstall:
	pip uninstall -y gridsync
