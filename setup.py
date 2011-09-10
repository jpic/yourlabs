#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='yourlabs',
    version='0.0.0',
    description='Part of our Django kit',
    author='James Pic',
    author_email='jpic@yourlabs.org',
    url='http://github.com/yourlabs/yourlabs/',
    license='New BSD License',
    classifiers=[
      'Framework :: Django',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: BSD License',
      'Programming Language :: Python',
    ],
    include_package_data=True,
    packages=find_packages(),
    zip_safe=False,
)
