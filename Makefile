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

pngs:
	mkdir -p build/frames
	convert -scale 1024x1024 -gravity center -extent 1024x1024 -background transparent images/gridsync.svg build/gridsync.png
	for i in images/frames/frame*.svg; do \
		convert -scale 256x256 -gravity center -extent 256x256 -background transparent $$i build/frames/$$(basename $$i).png; \
	done

icns: pngs
	#for i in 16 32 128 256 512 1024; do \
		convert -scale $$i\x$$i -gravity center -extent $$i\x$$i -background transparent images/gridsync.svg  build/icon$$i\x$$i.png; \
	done
	#png2icns images/gridsync.icns build/icon*x*.png
	mkdir -p build/gridsync.iconset
	sips -s format png --resampleWidth 1024 build/gridsync.png --out build/gridsync.iconset/icon_512x512@2x.png
	sips -s format png --resampleWidth 512 build/gridsync.png --out build/gridsync.iconset/icon_512x512.png
	cp build/gridsync.iconset/icon_512x512.png build/gridsync.iconset/icon_256x256@2x.png
	sips -s format png --resampleWidth 256 build/gridsync.png --out build/gridsync.iconset/icon_256x256.png
	cp build/gridsync.iconset/icon_256x256.png build/gridsync.iconset/icon_128x128@2x.png
	sips -s format png --resampleWidth 128 build/gridsync.png --out build/gridsync.iconset/icon_128x128.png
	sips -s format png --resampleWidth 64 build/gridsync.png --out build/gridsync.iconset/icon_32x32@2x.png
	sips -s format png --resampleWidth 32 build/gridsync.png --out build/gridsync.iconset/icon_32x32.png
	cp build/gridsync.iconset/icon_32x32.png build/gridsync.iconset/icon_16x16@2x.png
	sips -s format png --resampleWidth 16 build/gridsync.png --out build/gridsync.iconset/icon_16x16.png
	iconutil -c icns build/gridsync.iconset

gif: pngs
	convert -resize 256x256 -dispose 2 -delay 8 -loop 0 build/frames/frame*.png build/sync.gif

resources: gif
	convert -scale 256x256 -gravity center -extent 256x256 -background transparent images/gridsync.svg build/gridsync.png
	pyrcc4 -py2 resources.qrc -o gridsync/resources.py

install: clean
	python setup.py install --user

app: clean icns
	pyinstaller --clean --onefile --windowed gridsync.spec
	cp Info.plist dist/Gridsync.app/Contents

dmg: app
	mkdir -p dist/dmg
	mv dist/Gridsync.app dist/dmg
	create-dmg --volname "Gridsync" \
		--app-drop-link 320 2 \
		dist/Gridsync.dmg \
		dist/dmg

uninstall:
	pip uninstall -y gridsync
