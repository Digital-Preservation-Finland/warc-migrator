"""
Warctools handler.

This module includes slightly reformatted MIT licensed code from Warctools
software originally created by Hanzo Archives Ltd.

For more information about Warctools, see
https://github.com/internetarchive/warctools
"""
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
    arc = ArcTransformer()
    fh = MixedRecord.open_archive(filename=infile, gzip="auto")
    try:
        for record in fh:
            try:
                warcs = arc.convert(record)
            except ValueError as err:
                if "invalid literal for int() with base 10: ''" in err:
                    warcs = _process_empty_length_record(record, arc)
                    for warcrecord in warcs:
                        warcrecord.write_to(out, gzip=False)
                else:
                    raise ValueError(err)
            else:
                for warcrecord in warcs:
                    warcrecord.write_to(out, gzip=False)

            count += len(warcs)

    finally:
        fh.close()

    return count


def _process_empty_length_record(record, arc):
    """
    Convert record from ARC to WARC if record length is not given in ARC.
    The original Warctools can not handle the record, if length is empty.
    This is a copied and stripped code from Warctools.

    :record: Warctools' ARC record
    :arc: Warctools' ARC transformer
    :returns: Warctools' WARC record
    """
    warc_id = arc.make_warc_uuid(record.url+record.date)
    headers = [
        (WarcRecord.ID, warc_id),
        (WarcRecord.URL, record.url),
        (WarcRecord.WARCINFO_ID, arc.warcinfo_id),
    ]

    if record.date:
        try:
            date = datetime.datetime.strptime(record.date.decode(
                'ascii'), '%Y%m%d%H%M%S')
        except ValueError:
            date = datetime.datetime.strptime(record.date.decode(
                'ascii'), '%Y%m%d')
    else:
        date = datetime.datetime.now()

    ip = record.get_header(ArcRecord.IP)
    if ip and ip.strip() != b"0.0.0.0":
        headers.append((WarcRecord.IP_ADDRESS, ip.strip()))

    headers.append((WarcRecord.DATE, warc_datetime_str(date)))

    content_type, content = record.content

    if not content_type.strip():
        content_type = b'application/octet-stream'

    message = ResponseMessage(RequestMessage(),
                              ignore_headers=["Content-Length"])
    remainder = message.feed(content)
    message.close()

    if message.complete() and not remainder:
        content_type = b"application/http;msgtype=response"
        record_type = WarcRecord.RESPONSE
    else:
        record_type = WarcRecord.RESOURCE

    headers.append((WarcRecord.TYPE, record_type))

    return WarcRecord(headers=headers, content=(content_type, content),
                      version=arc.version),
