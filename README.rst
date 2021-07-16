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

This software is tested with Python 2.7 and 3.6 with CentOS 7.x release.

Install the required software to a virtual environment with commands::

    yum install python-virtualenv
    virtualenv venv
    source venv/bin/activate
    pip install --upgrade pip setuptools
    pip install -r requirements_github.txt
    pip install .

Usage:
------

Use the software with the following command::

    warc-migrator sourcefile targetfile [--meta fieldname value ...]

The `sourcefile` must be existing ARC 1.0/1.1 or WARC 0.17/0.18 file.
The `targetfile` must be a non-existing file.

Option `--meta` along with `fieldname` and `value` is optional and can be
given multiple times. The `fieldname` is the name of the warcinfo field and
`value` is the contained metadata string. These fields are added to warcinfo
record. The given field overwrites the possibly existing field.

Migration:
----------

**Migration of ARC 1.0/1.1 files to WARC 1.0**

The tool will create WARC records for the actual content. In the beginning of
the WARC file, a new warcinfo record and a new metadata record will be created.
The warcinfo record contains basic info about the warc file. If the original
ARC file has XML metadata, it is utilized for warcinfo creation. The metadata
record contains the header of the original ARC file as is, including the possible
XML metadata.

1. Warcinfo record will have the following header::

    WARC/1.0
    WARC-Type: warcinfo
    WARC-Record-ID: <new UUID>
    WARC-Date: <timestamp of now>
    WARC-Filename: <resulted WARC file name>
    Content-Type: application/warc-fields
    Content-Length: <length of warcinfo>
    WARC-Block-Digest: <new block sha1 sum in base32 encoded format>

2. ARC metadata record will have the following header::

    WARC/1.0
    WARC-Type: metadata
    WARC-Concurrent-To: <warcinfo's WARC-Record-ID>
    WARC-Record-ID: <new UUID>
    WARC-Target-URI: <original ARC filename stripped from ARC header>
    WARC-Date: <original timestamp stripped from ARC header>
    WARC-Warcinfo-ID: <warcinfo's WARC-Record-ID>
    Content-Type: application/x-internet-archive
    Content-Length: <length of metadata>
    WARC-Block-Digest: <new block sha1 sum in base32 encoded format>
    WARC-Payload-Digest: <new payload sha1 sum in base32 encoded format>

3. The records of the actual content will have the following header::

    WARC/1.0
    WARC-Record-ID: <new UUID>
    WARC-Target-URI: <target URI>
    WARC-Warcinfo-ID: <warcinfo's WARC-Record-ID>
    WARC-IP-Address: <original IP address stripped from ARC record>
    WARC-Date: <original date stripped from ARC record
    WARC-Type: <type of record>
    Content-Type: <original mimetype stripped from ARC record>
    Content-Length: <original length stripped from arc record>
    WARC-Block-Digest: <new block sha1 sum in base32 encoded format>
    WARC-Payload-Digest: <new payload sha1 sum in base32 encoded format>

4. The actual warcinfo payload will contain the following items:

    1. The possible XML elements from ARC header, but in warcinfo format.
       The migration collects ARC and Dublin Core (Dublin Core 1.1, DCTerms,
       DCMIType) from the ARC metadata and uses the element name as warcinfo
       field name (without namespace) and the elment's value as the
       corresponding value.
    2. The following fields, which will overwrite the possibly existing fields
       with the same key added in step 4.1::

           conformsTo: https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.0/
           format: WARC File Format 1.0

    3. User defined fields, which will overwrite the possibly existing fields 
       with the same key added in steps 4.1. and 4.2.

5. The actual ARC metadata payload is the ARC header including the possible XML metadata.

6. The actual payloads of the other records are direct copies of the payloads of
   the original records, but those HTTP header values are URL encoded, which can
   not be fitted to US-ASCII. This URL encoding rule applies also to the
   description in the statusline.


**Migration of WARC 0.17/0.18 files to WARC 1.0**

The migration is quite straightforward.

1. The protocol is changed in all records to::

    WARC/1.0

2. The following WARC header fields are added or modified in warcinfo record,
   other fields remain as is::

    WARC/1.0
    WARC-Date: <timestamp of now>
    WARC-Filename: <resulted WARC file name>
    WARC-Block-Digest: <new block sha1 sum in base32 encoded format>

3. The following header fields are added to all other records::

    WARC/1.0
    WARC-Block-Digest: <new block sha1 sum in base32 encoded format>
    WARC-Payload-Digest: <new payload sha1 sum in base32 encoded format>

4. The following warcinfo fields are added or modified in warcinfo record,
   other fields remain as is:

    1. The following fields, which will overwrite the possibly existing fields
       with the same key::

           conformsTo: https://iipc.github.io/warc-specifications/specifications/warc-format/warc-1.0/
           format: WARC File Format 1.0

    2. User defined fields, which will overwrite the possibly existing fields
       with the same key.

5. The actual payloads of the other records are direct copies of the payloads of
   the original records, but those HTTP header values are URL encoded, which can
   not be fitted to US-ASCII. This URL encoding rule applies also to the
   description in the statusline.

6. A separate metadata record is not created, as done in ARC migration above.

**Other notes**

1. The final file will be a compressed WARC file (.warc.gz)

2. Some ARC and WARC files are originally compressed with a single gzip compression,
   with having all the records in the same compression. This disallows seeking. The
   migration fixes these so that each record is gzipped one-by-one, which will
   eventually create a multi-member gzip file. The reason of this single gzipping
   comes from older files, probably from the time when WARC specification was still
   a work-in-progess.

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
