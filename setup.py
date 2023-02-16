#!/usr/bin/env python3

import os

from setuptools import find_packages, setup

directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(directory, "requirements.txt"), encoding="utf-8") as f:
    REQUIREMENTS = f.read().splitlines()

setup(
    name="cda-dl",
    version="1.0.0",
    description="CLI downloader do filmów i folderów z cda.pl",
    author="Piotr Skowroński",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Topic :: Multimedia :: Video",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "console_scripts": [
            "cda-dl=cda_dl.main:main",
        ],
    },
    install_requires=REQUIREMENTS,
    python_requires=">=3.10",
    extras_require={
        "formatting": [
            "black",
        ],
        "linting": [
            "flake8",
            "mypy",
        ],
        "testing": [
            "pytest",
            "pytest-asyncio",
            "tox",
        ],
    },
)
