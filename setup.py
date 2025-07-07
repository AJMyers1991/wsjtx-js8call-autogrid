#!/usr/bin/env python3
"""
Setup script for WSJT-X/JS8-Call Auto Grid Square Updater
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "WSJT-X/JS8-Call Auto Grid Square Updater"

# Read requirements
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="wsjtx-js8call-autogrid",
    version="1.0.0",
    description="Automatically updates grid square location in WSJT-X and JS8-Call based on GPS data",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Auto-generated",
    author_email="",
    url="",
    packages=find_packages(),
    py_modules=["autogrid"],
    install_requires=read_requirements(),
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Ham Radio",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="amateur radio ham radio wsjt-x js8-call gps grid square maidenhead",
    entry_points={
        "console_scripts": [
            "autogrid=autogrid:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 