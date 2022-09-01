#!/bin/bash

python -m black setup.py gridsync tests
python -m isort setup.py gridsync tests
