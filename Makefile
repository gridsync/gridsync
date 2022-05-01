.DEFAULT_GOAL := all
SHELL := /bin/bash
SCRIPTS := $(CURDIR)/scripts
.PHONY: clean test all

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf .cache/
	rm -rf .tox/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -f .coverage
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -rf {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

test:
	@case `uname` in \
		Darwin)	arch -x86_64 python3 -m tox ;; \
		*) python3 -m tox ;; \
	esac

test-integration:
	@case `uname` in \
		Darwin)	arch -x86_64 python3 -m tox -e integration ;; \
		*) xvfb-run -a python3 -m tox -e integration ;; \
	esac

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

install:
	python3 -m pip install --upgrade .


pyinstaller-separate:
	python3 -m tox -e pyinstaller-tahoe
	python3 -m tox -e pyinstaller-magic-folder
	python3 -m tox -e pyinstaller-gridsync

pyinstaller-merged:
	python3 -m tox -e pyinstaller

pyinstaller:
	$(MAKE) pyinstaller-merged

zip:
	python3 scripts/update_permissions.py dist
	python3 scripts/update_timestamps.py dist
	python3 scripts/make_zip.py

test-determinism:
	python3 scripts/test_determinism.py

dmg:
	python3 -m virtualenv --clear build/venv-dmg
	source build/venv-dmg/bin/activate && \
	python3 -m pip install -r requirements/dmgbuild.txt && \
	python3 scripts/call_dmgbuild.py

check-outdated:
	python3 scripts/check_outdated.py


vagrant-build-linux:
	vagrant up centos-7
	vagrant provision --provision-with devtools,test,build centos-7

vagrant-build-macos:
	vagrant up --provision-with devtools,test,build macos-10.14

vagrant-build-windows:
	vagrant up --provision-with devtools,test,build windows-10


container-image:
	@if [ -z "${QT_VERSION}" ] ; then export QT_VERSION=5 ; fi ; \
	podman build --timestamp 1651072070 \
		--tag gridsync-builder-qt$${QT_VERSION} \
		--file Containerfile.qt$${QT_VERSION}

push-container-image:
	@if [ -z "${QT_VERSION}" ] ; then export QT_VERSION=5 ; fi ; \
	podman login docker.io && \
	podman push --digestfile misc/gridsync-builder-qt$${QT_VERSION}.digest \
		gridsync-builder-qt$${QT_VERSION} \
		docker.io/gridsync/gridsync-builder-qt$${QT_VERSION}

in-container:
	@if [ "${QT_API}" == "pyqt6" ] || [ "${QT_API}" == "pyside6" ] ; then \
		export _QT_VERSION=6 ; \
	elif [ "${QT_API}" == "pyside2" ] ; then \
		export _QT_VERSION=5 ; \
	else \
		export QT_API=pyqt5 ; \
		export _QT_VERSION=5 ; \
	fi && \
	docker run --rm --mount type=bind,src=$$(pwd),target=/gridsync \
		-w /gridsync --env QT_API="$${QT_API}" \
		docker.io/gridsync/gridsync-builder-qt$${_QT_VERSION}@$$(cat misc/gridsync-builder-qt$${_QT_VERSION}.digest)


# https://developer.apple.com/library/archive/technotes/tn2206/_index.html
codesign-app:
	python3 scripts/codesign.py app

codesign-dmg:
	python3 scripts/codesign.py dmg

codesign-all:
	$(MAKE) codesign-app dmg codesign-dmg

notarize-app:
	python3 scripts/notarize.py app

notarize-dmg:
	python3 scripts/notarize.py dmg

dist-macos:
	$(MAKE) codesign-app notarize-app dmg codesign-dmg notarize-dmg

appimage:
	python3 scripts/make_appimage.py

all:
	@case `uname` in \
		Darwin)	arch -x86_64 $(MAKE) pyinstaller zip dmg ;; \
		*) $(MAKE) pyinstaller zip appimage ;; \
	esac
	python3 scripts/sha256sum.py dist/*.*

gpg-sign:
	python3 scripts/gpg.py --sign

gpg-verify:
	python3 scripts/gpg.py --verify

pypi-release:
	python setup.py sdist bdist_wheel
	twine upload --verbose dist/gridsync-*.*

uninstall:
	python3 -m pip uninstall -y gridsync
