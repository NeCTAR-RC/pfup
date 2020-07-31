#!/usr/bin/env python

import setuptools

from pbr.packaging import parse_requirements


readme = open('README.rst').read()


setuptools.setup(
    name='pfup',
    version='0.1.0',
    description=('Script to check for updates to puppet modules '
                 'in puppet forge and submit for review'),
    long_description=readme,
    author='Sam Morrison',
    author_email='sorrison@gmail.com',
    url='https://github.com/NeCTAR-RC/pfup',
    packages=[
        'pfup',
    ],
    entry_points={
        'console_scripts': [
            'pfup = pfup.cmd:main',
        ],
    },
    install_requires=parse_requirements(),
    license="GPLv3+",
    zip_safe=False,
    keywords='puppet forge gerrit',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        ('License :: OSI Approved :: '
         'GNU General Public License v3 or later (GPLv3+)'),
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
    ],
)
