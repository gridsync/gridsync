SHELL := /bin/bash
.PHONY: tahoe

test:
	python setup.py test

pytest:
	@case `uname` in \
		Linux) xvfb-run -a python -m pytest || exit 1;;\
		Darwin) python -m pytest || exit 1;;\
	esac

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
	pyrcc5 misc/resources.qrc -o gridsync/resources.py

ui:
	for i in misc/designer/*.ui; do \
		filename=$$(basename $$i); \
		pyuic5 $$i -o gridsync/forms/$${filename%%.*}.py; \
	done

sip:
	mkdir -p build/sip
	curl --progress-bar --output "build/sip.tar.gz" --location \
		"https://sourceforge.net/projects/pyqt/files/sip/sip-4.18/sip-4.18.tar.gz"
	tar zxf build/sip.tar.gz -C build/sip --strip-components=1
	cd build/sip && \
		$${PYTHON=python} configure.py --incdir=build/sip/sipinc
	$(MAKE) -C build/sip -j 4
	$(MAKE) -C build/sip install || sudo $(MAKE) -C build/sip install

pyqt: sip
	mkdir -p build/pyqt
	curl --progress-bar --output "build/pyqt.tar.gz" --location \
		"https://sourceforge.net/projects/pyqt/files/PyQt5/PyQt-5.6/PyQt5_gpl-5.6.tar.gz"
	tar zxf build/pyqt.tar.gz -C build/pyqt --strip-components=1
	cd build/pyqt && \
		QT_SELECT=qt5 $${PYTHON=python} configure.py \
			--confirm-license \
			--sip ../sip/sipgen/sip \
			--sip-incdir ../sip/siplib \
			--enable QtCore \
			--enable QtGui \
			--enable QtWidgets
	$(MAKE) -C build/pyqt -j 4
	$(MAKE) -C build/pyqt install || sudo $(MAKE) -C build/pyqt install

check_pyqt:
	$${PYTHON=python} -c 'import PyQt5' && echo 'PyQt5 installed' || make pyqt

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

frozen-tahoe:
	mkdir -p build/tahoe-lafs
	curl --output build/tahoe-lafs.tar.bz2 --location \
		https://tahoe-lafs.org/downloads/tahoe-lafs-1.11.0.tar.bz2
	tar jxf build/tahoe-lafs.tar.bz2 -C build/tahoe-lafs --strip-components=1
	virtualenv --clear --python=python2 build/venv
	source build/venv/bin/activate && \
	pip install --find-links=https://tahoe-lafs.org/deps/ build/tahoe-lafs && \
	pip install pyinstaller && \
	cp misc/tahoe.spec build/tahoe-lafs && \
	pushd build/tahoe-lafs && \
	export PYTHONHASHSEED=1 && \
	pyinstaller tahoe.spec && \
	python -m zipfile -c dist/Tahoe-LAFS.zip dist/Tahoe-LAFS && \
	mv dist ../..

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
	cp misc/Info.plist dist/Gridsync.app/Contents
	mv dist/Tahoe-LAFS dist/Gridsync.app/Contents/MacOS
	chmod +x dist/Gridsync.app/Contents/MacOS/Tahoe-LAFS/tahoe

dmg: app
	pip2 install --upgrade dmgbuild || pip2 install --user --upgrade dmgbuild
	dmgbuild -s misc/dmgbuild_settings.py Gridsync dist/Gridsync.dmg
	#mkdir -p dist/dmg
	#mv dist/Gridsync.app dist/dmg
	# From https://github.com/andreyvit/create-dmg
	#create-dmg --volname "Gridsync" \
	#	--app-drop-link 320 2 \
	#	dist/Gridsync.dmg \
	#	dist/dmg
	#mv dist/dmg/Gridsync.app dist
	#rm -rf dist/dmg

all: dmg

uninstall:
	pip3 uninstall -y gridsync
