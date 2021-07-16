"""
Warctools handler.

This module includes slightly reformatted MIT licensed code from Warctools
software originally created by Hanzo Archives Ltd.

For more information about Warctools, see
https://github.com/internetarchive/warctools


Warctools MIT license:

Copyright (c) 2011-2012 Hanzo Archives Ltd

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included 
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION 
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import io
import datetime

from hanzo.arc2warc import ArcTransformer
from hanzo.warctools.mixed import MixedRecord
from hanzo.warctools.warc import WarcRecord, warc_datetime_str
from hanzo.warctools.arc import ArcRecord
from hanzo.httptools.messaging import RequestMessage, ResponseMessage


def is_arc(source_path):
    """
    Resolve with Warctools wheter a file is an ARC file or WARC file

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
    arc = Arc2WarcTransformer()
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


def is_http_response(content):
    """
    Check if the content is a HTTP response.

    The same function is in Warctools, but it raises a ValueError if the
    Content-Length field is empty in HTTP header. Here we first read the HTTTP
    haader, and if empty Content-Length is found, it will be ignored.

    :content: Record cotent
    :returns: True if the content is HTTP response, False otherwise
    """
    empty_length = False
    content_buffer = io.BytesIO(content)
    for line in content_buffer:
        if line.strip() == b"Content-Length:":
            empty_length = True
            break
        if len(line.strip()) == 0:
            break
    if empty_length:
        message = ResponseMessage(RequestMessage(),
                                  ignore_headers=["Content-Length"])
    else:
        message = ResponseMessage(RequestMessage())

    remainder = message.feed(content)
    message.close()
    return message.complete() and not remainder


# pylint: disable=no-member, too-many-branches, trailing-comma-tuple
# WarcRecord has constants in a decorator, which is not supoorted in pylint.
class Arc2WarcTransformer(ArcTransformer):
    """
    Override Warctools class ArcTransformer.
    """

    def convert_record(self, record):
        """
        Convert ARC record to WARC.

        This method overrides ArcTransformer.convert_record() found in
        Warctools. This method is no different from the method it
        overrides (except some style fixes), but here it uses the
        is_http_response() function defined in this module.

        :record: ARC record
        :returns: Converted WARC record(s)
        """
        warc_id = self.make_warc_uuid(record.url+record.date)
        headers = [
            (WarcRecord.ID, warc_id),
            (WarcRecord.URL,record.url),
            (WarcRecord.WARCINFO_ID, self.warcinfo_id),
        ]

        if record.date:
            try:
                date = datetime.datetime.strptime(
                    record.date.decode('ascii'),'%Y%m%d%H%M%S')
            except ValueError:
                date = datetime.datetime.strptime(
                    record.date.decode('ascii'),'%Y%m%d')
        else:
            date = datetime.datetime.now()

        host = record.get_header(ArcRecord.IP)
        if host:
            host = host.strip()
            if host != b"0.0.0.0":
                headers.append((WarcRecord.IP_ADDRESS, host))

        headers.append((WarcRecord.DATE, warc_datetime_str(date)))

        content_type, content = record.content

        if not content_type.strip():
            content_type = b'application/octet-stream'

        url = record.url.lower()

        if any(url.startswith(p) for p in self.resources):
            record_type = WarcRecord.RESOURCE
        elif any(url.startswith(p) for p in self.responses):
            record_type = WarcRecord.RESPONSE
        elif url.startswith(b'http'):
            if is_http_response(content):
                content_type=b"application/http;msgtype=response"
                record_type = WarcRecord.RESPONSE
            else:
                record_type = WarcRecord.RESOURCE
        elif url.startswith(b'dns'):
            if content_type.startswith(b'text/dns') and \
                    str(content.decode('ascii', 'ignore')) == content:
                record_type = WarcRecord.RESOURCE
            else:
                record_type = WarcRecord.RESPONSE
        else:
            # unknown protocol
            record_type = WarcRecord.RESPONSE

        headers.append((WarcRecord.TYPE, record_type))

        warcrecord = WarcRecord(
            headers=headers, content=(content_type, content),
            version=self.version)

        return warcrecord,
