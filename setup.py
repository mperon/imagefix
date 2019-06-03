# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import find_packages, setup

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='imagefix',
    version='0.1.0',
    description='Fix image taken dates',
    long_description=readme,
    author='Marcos Peron',
    author_email='mperon@outlook.com',
    url='https://github.com/mperon/imagefix',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
