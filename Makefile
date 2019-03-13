.DEFAULT_GOAL := all
SHELL := /bin/bash
.PHONY: tahoe

test:
	python3 -m tox

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
	rm -rf htmlcov/
	rm -f .coverage
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
		build/frames/frame*.png build/gridsync.gif
	convert \
		-resize 256x256 \
		-dispose 2 \
		-delay 8 \
		-loop 0 \
		build/frames/onion-frame*.png build/onion-sync.gif
	convert \
		-resize 256x256 \
		-dispose 2 \
		-delay 7 \
		-loop 0 \
		images/frames/waiting-*.png build/waiting.gif
	convert \
		-dispose 2 \
		-delay 4 \
		-loop 0 \
		images/frames/sync-*.png build/sync.gif

resources: gif
	pyrcc5 misc/resources.qrc -o gridsync/resources.py

ui:
	for i in misc/designer/*.ui; do \
		filename=$$(basename $$i); \
		pyuic5 $$i -o gridsync/forms/$${filename%%.*}.py; \
	done

sip:
	mkdir -p build/sip
	curl --progress-bar --retry 20 --output "build/sip.tar.gz" --location \
		"https://sourceforge.net/projects/pyqt/files/sip/sip-4.19.2/sip-4.19.2.tar.gz"
	tar zxf build/sip.tar.gz -C build/sip --strip-components=1
	cd build/sip && $${PYTHON=python} configure.py --incdir=build/sip/sipinc
	$(MAKE) -C build/sip -j 4
	$(MAKE) -C build/sip install

pyqt: sip
	# apt-get install qtbase5-dev
	mkdir -p build/pyqt
	curl --progress-bar --retry 20 --output "build/pyqt.tar.gz" --location \
		"https://sourceforge.net/projects/pyqt/files/PyQt5/PyQt-5.8.2/PyQt5_gpl-5.8.2.tar.gz"
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
	$(MAKE) -C build/pyqt install

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
	mkdir -p dist
	mkdir -p build/tahoe-lafs
	git clone -b 1432.watchdog-magic-folder-with-eliot https://github.com/tahoe-lafs/tahoe-lafs.git build/tahoe-lafs
	cp misc/tahoe.spec build/tahoe-lafs/pyinstaller.spec
	python3 -m virtualenv --clear --python=python2 build/venv-tahoe
	source build/venv-tahoe/bin/activate && \
	pushd build/tahoe-lafs && \
	python setup.py update_version && \
	python -m pip install --find-links=https://tahoe-lafs.org/deps/ . && \
	case `uname` in \
		Darwin) python ../../scripts/maybe_rebuild_libsodium.py ;; \
	esac &&	\
	python -m pip install packaging && \
	python -m pip install git+git://github.com/crwood/eliot.git@frozen-build-support && \
	python -m pip install --no-use-pep517 pyinstaller==3.4 && \
	python -m pip list && \
	export PYTHONHASHSEED=1 && \
	pyinstaller pyinstaller.spec && \
	rm -rf dist/Tahoe-LAFS/cryptography-*-py2.7.egg-info && \
	rm -rf dist/Tahoe-LAFS/include/python2.7 && \
	rm -rf dist/Tahoe-LAFS/lib/python2.7 && \
	popd && \
	mv build/tahoe-lafs/dist/Tahoe-LAFS dist

install:
	python3 -m pip install --upgrade .

pyinstaller:
	if [ -f dist/Tahoe-LAFS.zip ] ; then \
		python -m zipfile -e dist/Tahoe-LAFS.zip dist ; \
	else  \
		make frozen-tahoe ; \
	fi;
	python3 -m virtualenv --clear --python=python3.6 build/venv-gridsync
	source build/venv-gridsync/bin/activate && \
	python -m pip install --upgrade pip && \
	python -m pip install -r requirements/requirements-hashes.txt && \
	python -m pip install . && \
	case `uname` in \
		Darwin) \
			python scripts/maybe_rebuild_libsodium.py && \
			python scripts/maybe_downgrade_pyqt.py \
		;; \
	esac &&	\
	python -m pip install --no-use-pep517 pyinstaller==3.4 && \
	python -m pip list && \
	export PYTHONHASHSEED=1 && \
	python -m PyInstaller -y misc/gridsync.spec

py2app:
	if [ -f dist/Tahoe-LAFS.zip ] ; then \
		python -m zipfile -e dist/Tahoe-LAFS.zip dist ; \
	else  \
		make frozen-tahoe ; \
	fi;
	python3 -m virtualenv --clear --python=python3.6 build/venv-py2app
	source build/venv-py2app/bin/activate && \
	python -m pip install --upgrade pip && \
	python -m pip install -r requirements/requirements-hashes.txt && \
	case `uname` in \
		Darwin) \
			python scripts/maybe_rebuild_libsodium.py && \
			python scripts/maybe_downgrade_pyqt.py \
		;; \
	esac &&	\
	python -m pip install . && \
	python -m pip install py2app && \
	python -m pip list && \
	python setup.py py2app && \
	python scripts/strip_py2app_bundle.py
	cp -r gridsync/resources dist/Gridsync.app/Contents/MacOS
	cp -r dist/Tahoe-LAFS dist/Gridsync.app/Contents/MacOS
	touch dist/Gridsync.app

dmg:
	python3 -m virtualenv --clear --python=python2 build/venv-dmg
	source build/venv-dmg/bin/activate && \
	python -m pip install dmgbuild && \
	python misc/call_dmgbuild.py

# https://developer.apple.com/library/archive/technotes/tn2206/_index.html
codesign-app:
	codesign --force --deep -s "Developer ID Application: Christopher Wood" dist/Gridsync.app
	codesign --verify --verbose=1 dist/Gridsync.app
	codesign --display --verbose=4 dist/Gridsync.app
	spctl -a -t exec -vv dist/Gridsync.app

codesign-dmg:
	codesign --force --deep -s "Developer ID Application: Christopher Wood" dist/Gridsync.dmg
	codesign --verify --verbose=1 dist/Gridsync.dmg
	codesign --display --verbose=4 dist/Gridsync.dmg
	spctl -a -t open --context context:primary-signature -v dist/Gridsync.dmg
	shasum -a 256 dist/Gridsync.dmg

codesign-all:
	$(MAKE) codesign-app dmg codesign-dmg

all:
	@case `uname` in \
		Darwin)	$(MAKE) pyinstaller dmg ;; \
		*) $(MAKE) pyinstaller ;; \
	esac

gpg-sign:
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-Linux.tar.gz
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-macOS.dmg
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-macOS-Legacy.dmg
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-Windows-setup.exe
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-Windows.zip

gpg-verify:
	gpg2 --verify release/Gridsync-Linux.tar.gz{.asc,}
	gpg2 --verify release/Gridsync-macOS.dmg{.asc,}
	gpg2 --verify release/Gridsync-macOS-Legacy.dmg{.asc,}
	gpg2 --verify release/Gridsync-Windows-setup.exe{.asc,}
	gpg2 --verify release/Gridsync-Windows.zip{.asc,}

pypi-release:
	python setup.py sdist bdist_wheel
	twine upload --verbose dist/gridsync-*.*

uninstall:
	python3 -m pip uninstall -y gridsync
