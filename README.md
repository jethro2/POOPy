# POOPy

**P**oo discharge monitoring with **O**bject **O**riented **Py**thon

## Description

This is a Python package for interfacing with Event Duration Monitoring (EDM) devices maintained by English Water Companies. This package was ostensibly developed to provide the back-end for [SewageMap.co.uk](https://github.com/AlexLipp/thames-sewage) but may be generically useful.

## Installation

Install this package by running the following command (replacing `[LOCAL DIRECTORY]` with the directory you wish to install the package into).
Note that this requires `Cython` to be installed (for example, `conda install -c anaconda cython`).

```bash
git clone https://github.com/AlexLipp/POOPy.git [LOCAL DIRECTORY]
pip install .
```

## Usage 

Once installed, the package can be imported into Python scripts using the following command.

```python
import poopy
```

Some examples of use are given in the `examples` folder.
