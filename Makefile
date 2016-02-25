SHELL := /bin/bash
.PHONY: tahoe

test:
	#python setup.py test
	tox

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf .cache/
	rm -rf .tox/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

pngs:
	mkdir -p build/frames
	for i in images/gridsync*.svg; do \
		convert -scale 1024x1024 \
			-gravity center \
			-extent 1024x1024 \
			-background transparent \
			$$i build/$$(basename -s .svg $$i).png; \
	done
	for i in images/frames/frame*.svg; do \
		convert -scale 1024x1024 \
			-gravity center \
			-extent 1024x1024 \
			-background transparent \
			$$i build/frames/$$(basename -s .svg $$i).png; \
	done
	for i in images/frames/onion-frame*.svg; do \
		convert -scale 1024x1024 \
			-gravity center \
			-extent 1024x1024 \
			-background transparent \
			$$i build/frames/$$(basename -s .svg $$i).png; \
	done

ico: pngs
	mkdir -p build/ico
	for i in 16 32 48 256; do \
		convert \
			-scale $$i\x$$i \
			-gravity center \
			-extent $$i\x$$i \
			-background transparent \
			images/gridsync.svg  \
			build/ico/gridsync-$$i\-$$i.png; \
	done
	# from 'icoutils' debian package
	icotool --create \
		build/ico/gridsync-16-16.png \
		build/ico/gridsync-32-32.png \
		build/ico/gridsync-48-48.png \
		build/ico/gridsync-256-256.png \
		-o images/gridsync.ico

icns: pngs
	#png2icns images/gridsync.icns build/icon*x*.png
	mkdir -p build/gridsync.iconset
	# OS X only
	sips \
		-s format png \
		--resampleWidth 1024 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_512x512@2x.png
	sips \
		-s format png \
		--resampleWidth 512 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_512x512.png
	cp build/gridsync.iconset/icon_512x512.png \
		build/gridsync.iconset/icon_256x256@2x.png
	sips \
		-s format png \
		--resampleWidth 256 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_256x256.png
	cp build/gridsync.iconset/icon_256x256.png \
		build/gridsync.iconset/icon_128x128@2x.png
	sips \
		-s format png \
		--resampleWidth 128 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_128x128.png
	sips \
		-s format png \
		--resampleWidth 64 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_32x32@2x.png
	sips \
		-s format png \
		--resampleWidth 32 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_32x32.png
	cp build/gridsync.iconset/icon_32x32.png \
		build/gridsync.iconset/icon_16x16@2x.png
	sips \
		-s format png \
		--resampleWidth 16 \
		build/gridsync.png \
		--out build/gridsync.iconset/icon_16x16.png
	iconutil -c icns build/gridsync.iconset

gif: pngs
	convert \
		-resize 256x256 \
		-dispose 2 \
		-delay 8 \
		-loop 0 \
		build/frames/frame*.png build/sync.gif
	convert \
		-resize 256x256 \
		-dispose 2 \
		-delay 8 \
		-loop 0 \
		build/frames/onion-frame*.png build/onion-sync.gif

resources: gif
	pyrcc5 resources.qrc -o gridsync/resources.py

ui:
	for i in designer/*.ui; do \
		filename=$$(basename $$i); \
		pyuic5 $$i -o gridsync/forms/$${filename%%.*}.py; \
	done

sip:
	mkdir -p build/sip
	#curl "https://www.riverbankcomputing.com/hg/sip/archive/tip.tar.gz" -o "build/sip.tar.gz"
	curl \
		--location \
		"http://sourceforge.net/projects/pyqt/files/sip/sip-4.17/sip-4.17.tar.gz" \
		--output "build/sip.tar.gz"
	tar zxvf build/sip.tar.gz -C build/sip --strip-components=1
	cd build/sip && \
		python2 build.py prepare; \
		python3 configure.py
	$(MAKE) -C build/sip install

pyqt: clean sip
	# Assumes Qt5/qmake is already installed system-wide
	mkdir -p build/pyqt
	curl \
		--location \
		"http://sourceforge.net/projects/pyqt/files/latest/download?source=files" \
		--output "build/pyqt.tar.gz"
	tar zxvf build/pyqt.tar.gz -C build/pyqt --strip-components=1
	cd build/pyqt && \
		python3 configure.py \
			--confirm-license \
			--sip ../sip/sipgen/sip \
			--sip-incdir ../sip/siplib \
			--enable QtCore \
			--enable QtGui \
			--enable QtWidgets
	$(MAKE) -C build/pyqt install

deps:
	case `uname` in \
		Linux) \
			apt-get update && \
			apt-get install tahoe-lafs python3 python3-pyqt5 python3-pip \
		;; \
		Darwin) echo darwin \
			brew -v update && \
			brew -v install python3 pyqt5 \
		;; \
	esac

build-deps: deps
	case `uname` in \
		Linux) \
			apt-get update && \
			apt-get install imagemagick \
		;; \
		Darwin) echo darwin \
			brew -v update && \
			brew -v install imagemagick \
		;; \
	esac

tahoe:
	git clone https://github.com/tahoe-lafs/tahoe-lafs.git build/tahoe-lafs
	virtualenv --clear --python=python2 build/venv
	source build/venv/bin/activate && \
		case `uname` in Linux) pip2 install pyopenssl ;; esac && \
		$(MAKE) -C build/tahoe-lafs make-version && \
		pip2 install build/tahoe-lafs

frozen-tahoe: tahoe
	# OS X only
	source build/venv/bin/activate && \
		pip2 install pyinstaller && \
		sed -i '' 's/"setuptools >= 0.6c6",/#"setuptools >= 0.6c6",/' \
			build/venv/lib/python2.7/site-packages/allmydata/_auto_deps.py && \
		export PYTHONHASHSEED=1 && \
			pyinstaller --noconfirm tahoe.spec
			python2 -m zipfile -c dist/Tahoe-LAFS.zip dist/Tahoe-LAFS

install:
	pip3 install --upgrade .

app: install
	# OS X only
	if [ -f dist/Tahoe-LAFS.zip ] ; then \
		python -m zipfile -e dist/Tahoe-LAFS.zip dist ; \
	else  \
		make frozen-tahoe ; \
	fi;
	pip3 install --upgrade pyinstaller
	export PYTHONHASHSEED=1 && \
		pyinstaller \
			--windowed \
			--icon=images/gridsync.icns \
			--name=gridsync \
			gridsync/cli.py
	mv dist/gridsync.app dist/Gridsync.app
	cp Info.plist dist/Gridsync.app/Contents
	mv dist/Tahoe-LAFS dist/Gridsync.app/Contents/MacOS

dmg: app
	mkdir -p dist/dmg
	mv dist/Gridsync.app dist/dmg
	# From https://github.com/andreyvit/create-dmg
	create-dmg --volname "Gridsync" \
		--app-drop-link 320 2 \
		dist/Gridsync.dmg \
		dist/dmg
	mv dist/dmg/Gridsync.app dist
	rm -rf dist/dmg

all: dmg

uninstall:
	pip3 uninstall -y gridsync
