"""Installation script for the `warc-migrator` package."""
from setuptools import setup, find_packages
from warc_migrator import __version__

setup(
    name='warc_migrator',
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    version=__version__,
    install_requires=[
        "click",
        "warcio",
        "warctools",
        "six",
        "lxml",
        "xml_helpers@git+https://gitlab.ci.csc.fi/dpres/xml-helpers.git"
        "@develop#egg=xml_helpers"
    ],
    entry_points={'console_scripts': [
        'warc-migrator=warc_migrator.migrator:warc_migrator_cli']},
    zip_safe=False,
    tests_require=['pytest'],
    test_suite='tests')
