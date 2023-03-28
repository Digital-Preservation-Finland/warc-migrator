"""
Warctools handler.

This module includes slightly reformatted MIT licensed code from Warctools
software originally created by Hanzo Archives Ltd.

For more information about Warctools, see
https://github.com/internetarchive/warctools


Warctools MIT license:

Copyright (c) 2011-2012 Hanzo Archives Ltd

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from hanzo.arc2warc import ArcTransformer
from hanzo.warctools.mixed import MixedRecord
from hanzo.warctools.warc import WarcRecord


def is_arc(source_path):
    """
    Resolve with Warctools whether a file is an ARC file or WARC file

    :source_path: Archive file path.
    :returns: True for ARC file, False for WARC
    """
    arc_file = True
    handler = MixedRecord.open_archive(filename=source_path, gzip="auto")
    try:
        for record in handler:
            if isinstance(record, WarcRecord):
                arc_file = False
            break
    finally:
        handler.close()

    return arc_file


def convert(infile, out):
    """
    Convert ARC to WARC with using Warctools.

    :infile: ARC filename
    :out: WARC file handler
    """
    count = 0
    arc = ArcTransformer()
    file_handler = MixedRecord.open_archive(filename=infile, gzip="auto")
    try:
        for record in file_handler:
            warcs = arc.convert(record)
            for warcrecord in warcs:
                warcrecord.write_to(out, gzip=False)

            count += len(warcs)

    finally:
        file_handler.close()

    return count
