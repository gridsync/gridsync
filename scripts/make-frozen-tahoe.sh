#!/bin/bash
#
# Build frozen Tahoe-LAFS on OS X - virtualenv edition
#

pip install --upgrade virtualenv
virtualenv --clear --python=python2 build/venv
source build/venv/bin/activate

git clone https://github.com/tahoe-lafs/tahoe-lafs.git build/tahoe-lafs

make -C build/tahoe-lafs make-version
pip install --upgrade build/tahoe-lafs

pip install --upgrade pyinstaller
sed -i '' 's/"setuptools >= 0.6c6",/#"setuptools >= 0.6c6",/' \
	build/venv/lib/python2.7/site-packages/allmydata/_auto_deps.py
export PYTHONHASHSEED=1
pyinstaller --noconfirm tahoe.spec
python -m zipfile -c dist/Tahoe-LAFS.zip dist/Tahoe-LAFS
export PYTHONHASHSEED=

deactivate

echo Done!
