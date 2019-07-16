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
	cp misc/tahoe.spec build/tahoe-lafs/pyinstaller.spec
	python3 -m virtualenv --clear --python=python2 build/venv-tahoe
	source build/venv-tahoe/bin/activate && \
	pushd build/tahoe-lafs && \
	git checkout ede9fc7b312a4a1b510e0d17e783de6de699fe9c && \
	python setup.py update_version && \
	python -m pip install . && \
	case `uname` in \
		Darwin) python ../../scripts/maybe_rebuild_libsodium.py ;; \
	esac &&	\
	python -m pip install packaging && \
	python -m pip install dis3 && \
	python -m pip install --no-use-pep517 pyinstaller==3.5 && \
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
	if [ ! -d dist/Tahoe-LAFS ] ; then make frozen-tahoe ; fi
	python3 -m tox -e pyinstaller

dmg:
	python3 -m virtualenv --clear --python=python2 build/venv-dmg
	source build/venv-dmg/bin/activate && \
	python -m pip install dmgbuild && \
	python misc/call_dmgbuild.py

vagrant-linux:
	pushd vagrantfiles/linux && \
	vagrant up ; \
	popd

vagrant-macos:
	pushd vagrantfiles/macos && \
	vagrant up ; \
	popd

vagrant-windows:
	rm vagrantfiles/windows/GridsyncSource.zip ; \
	python3 scripts/make_source_zip.py . vagrantfiles/windows/GridsyncSource.zip && \
	pushd vagrantfiles/windows && \
	vagrant up ; \
	rm GridsyncSource.zip ; \
	popd

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
	$(MAKE) pyinstaller
	@case `uname` in \
		Darwin)	$(MAKE) dmg ;; \
		*) python3 scripts/make_archive.py ;; \
	esac
	python3 scripts/sha256sum.py dist/*.*

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
