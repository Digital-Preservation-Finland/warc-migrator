WARC Migrator
=============

The tool migrates ARC 1.0/1.1 and WARC 0.17/0.18 to WARC 1.0 and validates it.

This tool is currently a work-in-progress project and should be used for
testing purposes only.

Mainly, the tool uses the MIT licensed Warctools and the Apache 2.0 licensed
Warcio tool for the migration. See:
- Warctools: https://github.com/internetarchive/warctools
- Warcio: https://github.com/webrecorder/warcio

Installation:
-------------

This software is tested with Python 2.7 with CentOS 7.x / RHEL 7.x releases.

Install the required software to a virtual environment with commands::

    yum install python-virtualenv
    virtualenv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools
    pip install click
    pip install lxml
    pip install six
    pip install warcio
    pip install warctools
    pip install git+https://github.com/Digital-Preservation-Finland/xml-helpers.git#egg=xml_helpers

Usage:
------

Use the software with the following command::

    python warc_migrator.py sourcefile targetfile [--encode] [--meta fieldname value ...]

The `sourcefile` must be existing ARC 1.0/1.1 or WARC 0.17/0.18 file.
The `targetfile` must be a non-existing file.

Option `--encode` URL encodes HTTP headers.

Option `--meta` along with `fieldname` and `value` is optional and can be
given multiple times. The `fieldname` is the name of the warcinfo field and
`value` is the contained metadata string. These fields are added to warcinfo
record. The given field overwrites the existing field.

Copyright
---------
Copyright (C) 2021 CSC - IT Center for Science Ltd.

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU Lesser General Public License as published by the Free Software Foundation, either
version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with
this program. If not, see <https://www.gnu.org/licenses/>.
