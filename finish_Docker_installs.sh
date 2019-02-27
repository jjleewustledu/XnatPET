#! /bin/bash

cd /work/pyxnat
python setup.py install
cd /work/interfile
python setup.py install
cd /work
python setup.py install # xnatpet
