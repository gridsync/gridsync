test:
	python setup.py test

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

icns:
	mkdir -p build
	for i in 16 32 128 256 512 1024; do \
		convert -scale $$i\x$$i -gravity center -extent $$i\x$$i -background transparent images/gridsync.svg  build/icon$$i\x$$i.png; \
	done
	echo png2icns images/gridsync.icns images/gridsync1024.png images/gridsync512.png images/gridsync256.png images/gridsync128.png images/gridsync32.png images/gridsync16.png
	png2icns images/gridsync.icns build/icon*x*.png

pngs:
	mkdir -p build
	for i in images/frames/frame*.svg; do \
		convert -scale 256x256 -gravity center -extent 256x256 -background transparent $$i build/$$(basename $$i).png; \
	done

gif: pngs
	convert -resize 256x256 -dispose 2 -delay 8 -loop 0 build/frame*.png build/sync.gif

resources: gif
	convert -scale 256x256 -gravity center -extent 256x256 -background transparent images/gridsync.svg build/gridsync.png
	pyrcc4 -py2 resources.qrc -o gridsync/resources.py

install: clean
	python setup.py install --user

app: clean
	pyinstaller --clean --onefile --windowed gridsync.spec

uninstall:
	pip uninstall -y gridsync
