#!/usr/bin/env python

import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand

setup_requires = []

if 'test' in sys.argv:
    setup_requires.append('pytest')

install_requires = [
    'requests>=2.0',
    'cookies',
    'six'
]

if sys.version_info < (3, 2):
    install_requires.append('mock')

tests_require = [
    'pytest',
    'coverage >= 3.7.1, < 5.0.0',
    'pytest-cov',
    'pytest-localserver',
    'flake8',
    'idna',
]

extras_require = {
    'tests': tests_require,
}


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = ['test_requests_testing.py']
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


setup(
    name='requests-testing',
    version='0.2.0',
    author='Pertsev Alexey',
    author_email='oeermanz@gmail.com',
    description='A utility library for mocking out the `requests` Python library.',
    url='https://github.com/a-pertsev/requests-testing',
    license='Apache 2.0',
    long_description=open('README.rst').read(),
    py_modules=['requests_testing', 'test_requests_testing'],
    zip_safe=False,
    install_requires=install_requires,
    extras_require=extras_require,
    tests_require=tests_require,
    setup_requires=setup_requires,
    cmdclass={'test': PyTest},
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development'
    ],
    keywords='requests mock testing',
)
