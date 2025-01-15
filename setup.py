from setuptools import setup, find_packages

setup(
    name="dhybridrpy",
    version="1",
    author="Bricker Ostler, Miha Cernetic",
    author_email="bostler@uchicago.edu",
    description="A Python package to easily read input + output data from dHybridR.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/bwostler/dhybridrpy",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
    ],
    license="AGPL-3.0",
    install_requires=[
        "numpy",
        "h5py",
        "matplotlib",
        "dask",
        "f90nml"
    ]
)