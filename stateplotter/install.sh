#!/bin/bash         
sudo apt-get install python-qt4

git clone https://github.com/pyqtgraph/pyqtgraph.git
cd pyqtgraph
python setup.py install