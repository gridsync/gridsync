.DEFAULT_GOAL := all
SHELL := /bin/bash
.PHONY: tahoe

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
		Darwin)	python3 -m tox ;; \
		*) xvfb-run -a python3 -m tox ;; \
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

frozen-tahoe:
	mkdir -p dist
	mkdir -p build/tahoe-lafs
	git clone https://github.com/tahoe-lafs/tahoe-lafs.git build/tahoe-lafs
	python3 -m virtualenv --clear --python=python2 build/venv-tahoe
	source build/venv-tahoe/bin/activate && \
	pip install --upgrade setuptools && \
	pip install --upgrade pip && \
	pushd build/tahoe-lafs && \
	git checkout tahoe-lafs-1.14.0 && \
	cp ../../misc/storage_client.py.patch . && \
	git apply storage_client.py.patch && \
	python setup.py update_version && \
	python -m pip install -r ../../requirements/tahoe-lafs.txt && \
	python -m pip install git+https://github.com/LeastAuthority/python-challenge-bypass-ristretto@v2020.04.03 && \
	python -m pip install git+https://github.com/PrivateStorageio/ZKAPAuthorizer@5725278531ba88a5e17da0ab0324fa934ec447bf && \
	python -m pip install . && \
	python -m pip install -r ../../requirements/pyinstaller.txt && \
	python -m pip list && \
	cp ../../misc/tahoe.spec pyinstaller.spec && \
	export PYTHONHASHSEED=1 && \
	pyinstaller pyinstaller.spec && \
	rm -rf dist/Tahoe-LAFS/cryptography-*-py2.7.egg-info && \
	rm -rf dist/Tahoe-LAFS/include/python2.7 && \
	rm -rf dist/Tahoe-LAFS/lib/python2.7 && \
	mkdir -p dist/Tahoe-LAFS/challenge_bypass_ristretto && \
	cp -R ../venv-tahoe/lib/python2.7/site-packages/challenge_bypass_ristretto/*.so dist/Tahoe-LAFS/challenge_bypass_ristretto && \
	popd && \
	mv build/tahoe-lafs/dist/Tahoe-LAFS dist

install:
	python3 -m pip install --upgrade .

pyinstaller:
	if [ ! -d dist/Tahoe-LAFS ] ; then make frozen-tahoe ; fi
	case `uname` in \
		Darwin) \
			python3 -m virtualenv --clear --python=python3.7 .tox/pyinstaller && \
			source .tox/pyinstaller/bin/activate && \
			pip install -r requirements/gridsync.txt && \
			pip install -r requirements/pyinstaller.txt && \
			pip install -e . && \
			rm -rf build/pyinstaller ; \
			git clone https://github.com/pyinstaller/pyinstaller.git build/pyinstaller && \
			pushd build/pyinstaller && \
			git checkout 0222ae2ea070e304405ba84a1f455f93e68d86a4 && \
			pushd bootloader && \
			export MACOSX_DEPLOYMENT_TARGET=10.13 && \
			export CFLAGS=-mmacosx-version-min=10.13 && \
			export CPPFLAGS=-mmacosx-version-min=10.13 && \
			export LDFLAGS=-mmacosx-version-min=10.13 && \
			export LINKFLAGS=-mmacosx-version-min=10.13 && \
			python ./waf all && \
			popd && \
			pip install . && \
			popd && \
			pip list && \
			export PYTHONHASHSEED=1 && \
			pyinstaller -y misc/gridsync.spec \
		;; \
		*) \
			python3 -m tox -e pyinstaller \
		;; \
	esac

dmg:
	python3 -m virtualenv --clear build/venv-dmg
	source build/venv-dmg/bin/activate && \
	python3 -m pip install dmgbuild && \
	python3 scripts/call_dmgbuild.py


vagrant-desktop-linux:
	vagrant up --no-provision ubuntu-20.04
	vagrant provision --provision-with desktop ubuntu-20.04

vagrant-desktop-macos:
	vagrant up --no-provision macos-10.15

vagrant-desktop-windows:
	vagrant up --no-provision windows-10


vagrant-build-linux:
	vagrant up centos-7
	vagrant provision --provision-with test,build centos-7

vagrant-build-macos:
	vagrant up --provision-with test,build macos-10.14

vagrant-build-windows:
	vagrant up --provision-with test,build windows-10


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
	$(MAKE) pyinstaller
	@case `uname` in \
		Darwin)	$(MAKE) dmg ;; \
		*) $(MAKE) appimage ;; \
	esac
	python3 scripts/sha256sum.py dist/*.*

gpg-sign:
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-Linux.AppImage
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-macOS.dmg
	gpg2 -a --detach-sign --default-key 0xD38A20A62777E1A5 release/Gridsync-Windows-setup.exe

gpg-verify:
	gpg2 --verify release/Gridsync-Linux.AppImage{.asc,}
	gpg2 --verify release/Gridsync-macOS.dmg{.asc,}
	gpg2 --verify release/Gridsync-Windows-setup.exe{.asc,}

pypi-release:
	python setup.py sdist bdist_wheel
	twine upload --verbose dist/gridsync-*.*

uninstall:
	python3 -m pip uninstall -y gridsync
